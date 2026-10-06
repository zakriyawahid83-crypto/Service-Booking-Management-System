from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db

from app.models.availability import Availability
from app.models.category import Category
from app.models.provider import Provider
from app.models.review import Review
from app.models.service import Service
from app.models.user import User

from app.schemas.service import (
    ServiceCreate,
    ServiceDetailResponse,
    ServiceResponse,
)
from app.utils.auth import require_role


router = APIRouter(
    prefix="/services",
    tags=["Services"],
)


def _get_current_provider(current_user: User, db: Session) -> Provider:
    provider = (
        db.query(Provider)
        .filter(Provider.user_id == current_user.id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider profile not found",
        )

    return provider


# =========================================================
# CREATE SERVICE
# =========================================================

@router.post(
    "/",
    response_model=ServiceResponse,
)
def create_service(
    service: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("provider")),
):
    provider = _get_current_provider(current_user, db)

    # Provider ID must belong to logged-in provider
    if service.provider_id != provider.id:
        raise HTTPException(
            status_code=403,
            detail="You can only create services for your provider profile",
        )

    # Get category
    category = (
        db.query(Category)
        .filter(Category.id == service.category_id)
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    # Category ownership
    if category.provider_id != provider.id:
        raise HTTPException(
            status_code=403,
            detail="This category does not belong to your shop",
        )

    # Create service
    new_service = Service(
        provider_id=provider.id,
        category_id=category.id,
        name=service.name,
        description=service.description,
        price=service.price,
        duration_minutes=service.duration_minutes,
        image_url=service.image_url,
        is_active=True,
    )

    db.add(new_service)
    db.commit()
    db.refresh(new_service)

    return new_service


# =========================================================
# GET ALL ACTIVE SERVICES
# =========================================================

@router.get(
    "/",
    response_model=list[ServiceResponse],
)
def get_services(
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Service,
            Provider.business_name,
            Provider.location,
        )
        .join(
            Provider,
            Provider.id == Service.provider_id,
        )
        .filter(
            Service.is_active == True
        )
        .order_by(Service.id)
        .all()
    )

    return [
        {
            "id": service.id,
            "provider_id": service.provider_id,
            "category_id": service.category_id,
            "name": service.name,
            "description": service.description,
            "price": service.price,
            "duration_minutes": service.duration_minutes,
            "image_url": service.image_url,
            "is_active": service.is_active,
            "provider_name": provider_name,
            "provider_location": provider_location,
        }
        for service, provider_name, provider_location in rows
    ]


# =========================================================
# GET PROVIDER SERVICES
# =========================================================

@router.get(
    "/provider/me",
    response_model=list[ServiceResponse],
)
def get_my_services(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("provider")),
):
    provider = _get_current_provider(current_user, db)

    return (
        db.query(Service)
        .filter(
            Service.provider_id == provider.id
        )
        .order_by(Service.id)
        .all()
    )


# =========================================================
# SEARCH SERVICES
# =========================================================

@router.get(
    "/search",
    response_model=list[ServiceResponse],
)
def search_services(
    q: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    provider_id: int | None = Query(default=None),
    location: str | None = Query(default=None),
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
    min_rating: float | None = Query(default=None),
    booking_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Service)
        .join(
            Provider,
            Service.provider_id == Provider.id,
        )
        .filter(
            Service.is_active == True
        )
    )

    # Search text
    if q:
        search_text = f"%{q}%"

        query = query.filter(
            (Service.name.ilike(search_text))
            | (Service.description.ilike(search_text))
        )

    # Category
    if category_id is not None:
        query = query.filter(
            Service.category_id == category_id
        )

    # Provider
    if provider_id is not None:
        query = query.filter(
            Service.provider_id == provider_id
        )

    # Location
    if location and hasattr(Provider, "location"):
        query = query.filter(
            Provider.location.ilike(
                f"%{location}%"
            )
        )

    # Minimum price
    if min_price is not None:
        query = query.filter(
            Service.price >= min_price
        )

    # Maximum price
    if max_price is not None:
        query = query.filter(
            Service.price <= max_price
        )

    # Minimum rating
    if min_rating is not None:
        query = (
            query
            .outerjoin(
                Review,
                Review.provider_id == Provider.id,
            )
            .group_by(Service.id)
            .having(
                func.coalesce(
                    func.avg(Review.rating),
                    0,
                ) >= min_rating
            )
        )

    # Booking date
    if booking_date is not None:
        weekday = booking_date.weekday()

        query = query.filter(
            db.query(Availability.id)
            .filter(
                Availability.provider_id
                == Service.provider_id,
                Availability.day_of_week
                == weekday,
                Availability.is_available == True,
            )
            .exists()
        )

    return query.all()


# =========================================================
# GET SERVICE DETAILS
# =========================================================

@router.get(
    "/{service_id}",
    response_model=ServiceDetailResponse,
)
def get_service(
    service_id: int,
    db: Session = Depends(get_db),
):
    result = (
        db.query(
            Service,
            Provider,
            func.coalesce(
                func.avg(Review.rating),
                0,
            ).label("average_rating"),
            func.count(
                Review.id
            ).label("total_reviews"),
        )
        .join(
            Provider,
            Service.provider_id == Provider.id,
        )
        .outerjoin(
            Review,
            Review.provider_id == Provider.id,
        )
        .filter(
            Service.id == service_id
        )
        .group_by(
            Service.id,
            Provider.id,
        )
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    service, provider, average_rating, total_reviews = result

    return {
        "id": service.id,
        "provider_id": service.provider_id,
        "category_id": service.category_id,
        "name": service.name,
        "description": service.description,
        "price": service.price,
        "duration_minutes": service.duration_minutes,
        "image_url": service.image_url,
        "is_active": service.is_active,
        "provider_name": getattr(
            provider,
            "business_name",
            None,
        ) or getattr(
            provider,
            "name",
            None,
        ),
        "provider_location": getattr(
            provider,
            "location",
            None,
        ),
        "provider_phone": getattr(
            provider,
            "phone",
            None,
        ),
        "average_rating": float(
            average_rating or 0
        ),
        "total_reviews": int(
            total_reviews or 0
        ),
    }


# =========================================================
# UPDATE SERVICE
# =========================================================

@router.put(
    "/{service_id}",
    response_model=ServiceResponse,
)
def update_service(
    service_id: int,
    service_data: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("provider")),
):
    provider = _get_current_provider(
        current_user,
        db,
    )

    service = (
        db.query(Service)
        .filter(
            Service.id == service_id
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    # Service ownership
    if service.provider_id != provider.id:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    # Provider ownership
    if service_data.provider_id != provider.id:
        raise HTTPException(
            status_code=403,
            detail="You can only assign services to your provider profile",
        )

    # Get category
    category = (
        db.query(Category)
        .filter(
            Category.id
            == service_data.category_id
        )
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    # Category ownership
    if category.provider_id != provider.id:
        raise HTTPException(
            status_code=403,
            detail="This category does not belong to your shop",
        )

    service.provider_id = provider.id
    service.category_id = category.id
    service.name = service_data.name
    service.description = service_data.description
    service.price = service_data.price
    service.duration_minutes = service_data.duration_minutes
    service.image_url = service_data.image_url

    db.commit()
    db.refresh(service)

    return service


# =========================================================
# DEACTIVATE SERVICE
# =========================================================

@router.patch(
    "/{service_id}/deactivate",
)
def deactivate_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("provider")),
):
    provider = _get_current_provider(
        current_user,
        db,
    )

    service = (
        db.query(Service)
        .filter(
            Service.id == service_id
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    if service.provider_id != provider.id:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    service.is_active = False

    db.commit()
    db.refresh(service)

    return {
        "message": "Service deactivated successfully",
        "service_id": service.id,
        "is_active": service.is_active,
    }


# =========================================================
# ACTIVATE SERVICE
# =========================================================

@router.patch(
    "/{service_id}/activate",
)
def activate_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("provider")),
):
    provider = _get_current_provider(
        current_user,
        db,
    )

    service = (
        db.query(Service)
        .filter(
            Service.id == service_id
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    if service.provider_id != provider.id:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    service.is_active = True

    db.commit()
    db.refresh(service)

    return {
        "message": "Service activated successfully",
        "service_id": service.id,
        "is_active": service.is_active,
    }


# =========================================================
# DELETE SERVICE
# =========================================================

@router.delete(
    "/{service_id}",
)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("provider")),
):
    provider = _get_current_provider(
        current_user,
        db,
    )

    service = (
        db.query(Service)
        .filter(
            Service.id == service_id
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    if service.provider_id != provider.id:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    db.delete(service)
    db.commit()

    return {
        "message": "Service deleted successfully"
    }