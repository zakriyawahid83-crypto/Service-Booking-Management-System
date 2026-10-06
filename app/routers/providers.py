from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import Booking
from app.models.category import Category
from app.models.payment import Payment
from app.models.provider import Provider
from app.models.review import Review
from app.models.service import Service
from app.models.user import User
from app.schemas.provider import (
    ProviderBookingResponse,
    ProviderBookingStatusUpdate,
    ProviderCustomerResponse,
    ProviderDashboardResponse,
    ProviderEarningItemResponse,
    ProviderEarningsResponse,
    ProviderProfileResponse,
    ProviderProfileUpdate,
    ProviderServiceCreate,
    ProviderServiceResponse,
    ProviderServiceUpdate,
)
from app.utils.auth import require_role


router = APIRouter(
    prefix="/provider",
    tags=["Provider"]
)


# =========================================================
# GET CURRENT PROVIDER
# =========================================================

def get_provider(
    current_user: User,
    db: Session
):
    provider = (
        db.query(Provider)
        .filter(
            Provider.user_id == current_user.id
        )
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider profile not found"
        )

    return provider


# =========================================================
# GET PROVIDER DASHBOARD
# =========================================================

@router.get(
    "/dashboard",
    response_model=ProviderDashboardResponse
)
def provider_dashboard(
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    total_services = (
        db.query(Service)
        .filter(
            Service.provider_id == provider.id
        )
        .count()
    )

    active_services = (
        db.query(Service)
        .filter(
            Service.provider_id == provider.id,
            Service.is_active == True
        )
        .count()
    )

    bookings = (
        db.query(Booking)
        .filter(
            Booking.provider_id == provider.id
        )
        .all()
    )

    total_bookings = len(bookings)

    pending_bookings = sum(
        1
        for booking in bookings
        if booking.status == "pending"
    )

    confirmed_bookings = sum(
        1
        for booking in bookings
        if booking.status == "confirmed"
    )

    completed_bookings = sum(
        1
        for booking in bookings
        if booking.status == "completed"
    )

    cancelled_bookings = sum(
        1
        for booking in bookings
        if booking.status == "cancelled"
    )

    no_show_bookings = sum(
        1
        for booking in bookings
        if booking.status == "no-show"
    )

    customer_ids = {
        booking.customer_id
        for booking in bookings
    }

    total_customers = len(customer_ids)

    reviews = (
        db.query(Review)
        .filter(
            Review.provider_id == provider.id
        )
        .all()
    )

    total_reviews = len(reviews)

    average_rating = (
        sum(review.rating for review in reviews)
        / total_reviews
        if total_reviews
        else 0
    )

    total_earnings = sum(
        float(booking.price)
        for booking in bookings
        if booking.status == "completed"
    )

    return ProviderDashboardResponse(
        total_services=total_services,
        active_services=active_services,
        total_bookings=total_bookings,
        pending_bookings=pending_bookings,
        confirmed_bookings=confirmed_bookings,
        completed_bookings=completed_bookings,
        cancelled_bookings=cancelled_bookings,
        no_show_bookings=no_show_bookings,
        total_customers=total_customers,
        total_reviews=total_reviews,
        average_rating=average_rating,
        total_earnings=total_earnings
    )


# =========================================================
# CREATE PROVIDER SERVICE
# =========================================================

@router.post(
    "/services",
    response_model=ProviderServiceResponse
)
def create_provider_service(
    data: ProviderServiceCreate,
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    # -----------------------------------------------------
    # CATEGORY MUST BELONG TO CURRENT PROVIDER
    # -----------------------------------------------------

    category = (
        db.query(Category)
        .filter(
            Category.id == data.category_id,
            Category.provider_id == provider.id
        )
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This category does not belong to your shop"
        )

    service = Service(
        provider_id=provider.id,
        category_id=category.id,
        name=data.name,
        description=data.description,
        price=data.price,
        duration_minutes=data.duration_minutes,
        image_url=data.image_url,
        is_active=data.is_active
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    return service


# =========================================================
# GET MY SERVICES
# =========================================================

@router.get(
    "/services",
    response_model=list[ProviderServiceResponse]
)
def get_provider_services(
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    return (
        db.query(Service)
        .filter(
            Service.provider_id == provider.id
        )
        .order_by(Service.id)
        .all()
    )


# =========================================================
# GET SINGLE SERVICE
# =========================================================

@router.get(
    "/services/{service_id}",
    response_model=ProviderServiceResponse
)
def get_provider_service(
    service_id: int,
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    service = (
        db.query(Service)
        .filter(
            Service.id == service_id,
            Service.provider_id == provider.id
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    return service


# =========================================================
# UPDATE PROVIDER SERVICE
# =========================================================

@router.patch(
    "/services/{service_id}",
    response_model=ProviderServiceResponse
)
def update_provider_service(
    service_id: int,
    data: ProviderServiceUpdate,
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    service = (
        db.query(Service)
        .filter(
            Service.id == service_id,
            Service.provider_id == provider.id
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    # -----------------------------------------------------
    # CATEGORY OWNERSHIP CHECK
    # -----------------------------------------------------

    if data.category_id is not None:

        category = (
            db.query(Category)
            .filter(
                Category.id == data.category_id,
                Category.provider_id == provider.id
            )
            .first()
        )

        if not category:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This category does not belong to your shop"
            )

        service.category_id = category.id

    # -----------------------------------------------------
    # UPDATE SERVICE FIELDS
    # -----------------------------------------------------

    if data.name is not None:
        service.name = data.name

    if "description" in data.model_fields_set:
        service.description = data.description

    if data.price is not None:
        service.price = data.price

    if data.duration_minutes is not None:
        service.duration_minutes = data.duration_minutes

    if "image_url" in data.model_fields_set:
        service.image_url = data.image_url

    if data.is_active is not None:
        service.is_active = data.is_active

    db.commit()
    db.refresh(service)

    return service


# =========================================================
# DELETE PROVIDER SERVICE
# =========================================================

@router.delete(
    "/services/{service_id}"
)
def delete_provider_service(
    service_id: int,
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    service = (
        db.query(Service)
        .filter(
            Service.id == service_id,
            Service.provider_id == provider.id
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    has_bookings = db.query(Booking.id).filter(
        Booking.service_id == service.id
    ).first()
    if has_bookings:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This service has existing bookings and cannot be deleted. Deactivate it instead to preserve booking history.",
        )

    db.delete(service)
    db.commit()

    return {
        "message": "Service deleted successfully"
    }


# =========================================================
# GET PROVIDER BOOKINGS
# =========================================================

@router.get(
    "/bookings",
    response_model=list[ProviderBookingResponse]
)
def get_provider_bookings(
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    results = (
        db.query(
            Booking,
            User.name.label("customer_name"),
            User.email.label("customer_email"),
            Service.name.label("service_name")
        )
        .join(
            User,
            Booking.customer_id == User.id
        )
        .join(
            Service,
            Booking.service_id == Service.id
        )
        .filter(
            Booking.provider_id == provider.id
        )
        .order_by(
            Booking.booking_date.desc(),
            Booking.start_time.desc()
        )
        .all()
    )

    return [
        ProviderBookingResponse(
            id=booking.id,
            customer_id=booking.customer_id,
            provider_id=booking.provider_id,
            service_id=booking.service_id,
            booking_date=booking.booking_date,
            start_time=booking.start_time,
            end_time=booking.end_time,
            price=float(booking.price),
            status=booking.status,
            customer_notes=booking.customer_notes,
            created_at=booking.created_at,
            customer_name=customer_name,
            customer_email=customer_email,
            service_name=service_name
        )
        for (
            booking,
            customer_name,
            customer_email,
            service_name
        ) in results
    ]


# =========================================================
# GET SINGLE PROVIDER BOOKING
# =========================================================

@router.get(
    "/bookings/{booking_id}",
    response_model=ProviderBookingResponse
)
def get_provider_booking(
    booking_id: int,
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    result = (
        db.query(
            Booking,
            User.name.label("customer_name"),
            User.email.label("customer_email"),
            Service.name.label("service_name")
        )
        .join(
            User,
            Booking.customer_id == User.id
        )
        .join(
            Service,
            Booking.service_id == Service.id
        )
        .filter(
            Booking.id == booking_id,
            Booking.provider_id == provider.id
        )
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    (
        booking,
        customer_name,
        customer_email,
        service_name
    ) = result

    return ProviderBookingResponse(
        id=booking.id,
        customer_id=booking.customer_id,
        provider_id=booking.provider_id,
        service_id=booking.service_id,
        booking_date=booking.booking_date,
        start_time=booking.start_time,
        end_time=booking.end_time,
        price=float(booking.price),
        status=booking.status,
        customer_notes=booking.customer_notes,
        created_at=booking.created_at,
        customer_name=customer_name,
        customer_email=customer_email,
        service_name=service_name
    )


# =========================================================
# UPDATE BOOKING STATUS
# =========================================================

@router.patch(
    "/bookings/{booking_id}/status"
)
def update_provider_booking_status(
    booking_id: int,
    data: ProviderBookingStatusUpdate,
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.provider_id == provider.id
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    allowed_statuses = {
        "pending",
        "confirmed",
        "completed",
        "cancelled",
        "no-show"
    }

    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid booking status"
        )

    booking.status = data.status

    db.commit()
    db.refresh(booking)

    return {
        "message": "Booking status updated successfully",
        "booking_id": booking.id,
        "status": booking.status
    }


# =========================================================
# GET PROVIDER CUSTOMERS
# =========================================================

@router.get(
    "/customers",
    response_model=list[ProviderCustomerResponse]
)
def get_provider_customers(
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    results = (
        db.query(
            User.id.label("customer_id"),
            User.name.label("customer_name"),
            User.email.label("customer_email"),
            func.count(Booking.id).label("total_bookings"),
            func.sum(
                case(
                    (
                        Booking.status == "completed",
                        1
                    ),
                    else_=0
                )
            ).label("completed_bookings"),
            func.sum(
                case(
                    (
                        Booking.status == "cancelled",
                        1
                    ),
                    else_=0
                )
            ).label("cancelled_bookings"),
            func.sum(
                case(
                    (
                        Booking.status == "completed",
                        Booking.price
                    ),
                    else_=0
                )
            ).label("total_spent")
        )
        .join(
            Booking,
            Booking.customer_id == User.id
        )
        .filter(
            Booking.provider_id == provider.id
        )
        .group_by(
            User.id,
            User.name,
            User.email
        )
        .all()
    )

    return [
        ProviderCustomerResponse(
            customer_id=customer_id,
            customer_name=customer_name,
            customer_email=customer_email,
            total_bookings=total_bookings,
            completed_bookings=completed_bookings or 0,
            cancelled_bookings=cancelled_bookings or 0,
            total_spent=float(total_spent or 0)
        )
        for (
            customer_id,
            customer_name,
            customer_email,
            total_bookings,
            completed_bookings,
            cancelled_bookings,
            total_spent
        ) in results
    ]


# =========================================================
# GET SINGLE PROVIDER CUSTOMER
# =========================================================

@router.get(
    "/customers/{customer_id}",
    response_model=ProviderCustomerResponse
)
def get_provider_customer(
    customer_id: int,
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    result = (
        db.query(
            User.id.label("customer_id"),
            User.name.label("customer_name"),
            User.email.label("customer_email"),
            func.count(Booking.id).label("total_bookings"),
            func.sum(
                case(
                    (
                        Booking.status == "completed",
                        1
                    ),
                    else_=0
                )
            ).label("completed_bookings"),
            func.sum(
                case(
                    (
                        Booking.status == "cancelled",
                        1
                    ),
                    else_=0
                )
            ).label("cancelled_bookings"),
            func.sum(
                case(
                    (
                        Booking.status == "completed",
                        Booking.price
                    ),
                    else_=0
                )
            ).label("total_spent")
        )
        .join(
            Booking,
            Booking.customer_id == User.id
        )
        .filter(
            User.id == customer_id,
            Booking.provider_id == provider.id
        )
        .group_by(
            User.id,
            User.name,
            User.email
        )
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    (
        customer_id,
        customer_name,
        customer_email,
        total_bookings,
        completed_bookings,
        cancelled_bookings,
        total_spent
    ) = result

    return ProviderCustomerResponse(
        customer_id=customer_id,
        customer_name=customer_name,
        customer_email=customer_email,
        total_bookings=total_bookings,
        completed_bookings=completed_bookings or 0,
        cancelled_bookings=cancelled_bookings or 0,
        total_spent=float(total_spent or 0)
    )


# =========================================================
# PROVIDER EARNINGS
# =========================================================

@router.get(
    "/earnings",
    response_model=ProviderEarningsResponse
)
def get_provider_earnings(
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    if start_date and end_date and end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be on or after start date",
        )

    query = (
        db.query(
            Booking.id.label("booking_id"),
            Booking.customer_id,
            User.name.label("customer_name"),
            Booking.service_id,
            Service.name.label("service_name"),
            Service.duration_minutes,
            Booking.booking_date,
            Booking.start_time,
            Booking.end_time,
            Booking.status.label("booking_status"),
            Booking.price,
            Payment.id.label("payment_id"),
            Payment.amount.label("payment_amount"),
            Payment.status.label("payment_status"),
            Payment.transaction_id,
        )
        .join(
            User,
            Booking.customer_id == User.id
        )
        .join(
            Service,
            Booking.service_id == Service.id
        )
        .outerjoin(
            Payment,
            Payment.booking_id == Booking.id,
        )
        .filter(
            Booking.provider_id == provider.id
        )
    )
    if start_date is not None:
        query = query.filter(Booking.booking_date >= start_date)
    if end_date is not None:
        query = query.filter(Booking.booking_date <= end_date)

    results = query.order_by(
        Booking.booking_date.desc(),
        Booking.start_time.desc(),
    ).all()

    earnings = [
        ProviderEarningItemResponse(
            booking_id=booking_id,
            customer_id=customer_id,
            customer_name=customer_name,
            service_id=service_id,
            service_name=service_name,
            duration_minutes=duration_minutes,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            booking_status=booking_status,
            price=float(price),
            payment_id=payment_id,
            payment_amount=float(payment_amount) if payment_amount is not None else None,
            payment_status=payment_status,
            transaction_id=transaction_id,
        )
        for (
            booking_id,
            customer_id,
            customer_name,
            service_id,
            service_name,
            duration_minutes,
            booking_date,
            start_time,
            end_time,
            booking_status,
            price,
            payment_id,
            payment_amount,
            payment_status,
            transaction_id,
        ) in results
    ]

    completed_revenue = sum(
        item.payment_amount or 0
        for item in earnings
        if item.payment_status == "paid" and item.booking_status == "completed"
    )
    pending_revenue = sum(
        item.payment_amount or 0
        for item in earnings
        if item.payment_status == "pending"
    )
    refunded_revenue = sum(
        item.payment_amount or 0
        for item in earnings
        if item.payment_status == "refunded"
    )
    paid_revenue = sum(
        item.payment_amount or 0
        for item in earnings
        if item.payment_status == "paid"
    )
    total_earnings = paid_revenue - refunded_revenue

    completed_bookings = sum(
        1 for item in earnings if item.booking_status == "completed"
    )
    paid_completed_bookings = sum(
        1
        for item in earnings
        if item.payment_status == "paid" and item.booking_status == "completed"
    )

    average_booking_value = (
        completed_revenue / paid_completed_bookings
        if paid_completed_bookings
        else 0
    )

    return ProviderEarningsResponse(
        total_earnings=total_earnings,
        completed_bookings=completed_bookings,
        average_booking_value=average_booking_value,
        booking_count=len(earnings),
        completed_revenue=completed_revenue,
        pending_revenue=pending_revenue,
        refunded_revenue=refunded_revenue,
        earnings=earnings
    )


# =========================================================
# GET PROVIDER PROFILE / SHOP
# =========================================================

@router.get(
    "/profile",
    response_model=ProviderProfileResponse
)
def get_provider_profile(
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    return provider


# =========================================================
# UPDATE PROVIDER PROFILE / SHOP
# =========================================================

@router.put(
    "/profile",
    response_model=ProviderProfileResponse
)
def update_provider_profile(
    data: ProviderProfileUpdate,
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db)
):
    provider = get_provider(
        current_user,
        db
    )

    if data.business_name is not None:
        provider.business_name = data.business_name

    if data.description is not None:
        provider.description = data.description

    if data.location is not None:
        provider.location = data.location

    if data.phone is not None:
        provider.phone = data.phone

    db.commit()
    db.refresh(provider)

    return provider