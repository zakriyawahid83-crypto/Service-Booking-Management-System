from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import Booking
from app.models.category import Category
from app.models.complaint import Complaint
from app.models.provider import Provider
from app.models.review import Review
from app.models.service import Service
from app.models.user import User
from app.schemas.admin import (
    AdminBookingResponse,
    AdminBookingStatusUpdate,
    AdminComplaintResponse,
    AdminComplaintUpdate,
    AdminProviderResponse,
    AdminProviderUpdate,
    AdminReviewResponse,
    AdminReviewUpdate,
    AdminRoleUpdate,
    AdminServiceResponse,
    AdminServiceUpdate,
    AdminStatisticsResponse,
    AdminUserResponse,
)
from app.utils.auth import require_role


router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.get(
    "/users",
    response_model=list[AdminUserResponse]
)
def get_all_users(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    return db.query(User).order_by(
        User.id
    ).all()


@router.get(
    "/users/{user_id}",
    response_model=AdminUserResponse
)
def get_user(
    user_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user


@router.patch(
    "/users/{user_id}/role",
    response_model=AdminUserResponse
)
def update_user_role(
    user_id: int,
    data: AdminRoleUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if data.role not in [
        "customer",
        "provider",
        "admin"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid role"
        )

    user.role = data.role

    db.commit()
    db.refresh(user)

    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Admin cannot delete their own account"
        )

    db.delete(user)
    db.commit()

    return {
        "message": "User deleted successfully"
    }


@router.get(
    "/providers",
    response_model=list[AdminProviderResponse]
)
def get_all_providers(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    providers = db.query(Provider).order_by(
        Provider.id
    ).all()

    return [
        {
            "id": provider.id,
            "user_id": provider.user_id,
            "business_name": provider.business_name,
            "description": provider.description,
            "location": provider.location,
            "phone": provider.phone,
            "is_verified": provider.is_verified,
            "user_name": provider.user.name,
            "user_email": provider.user.email,
        }
        for provider in providers
    ]


@router.get(
    "/providers/{provider_id}",
    response_model=AdminProviderResponse
)
def get_provider(
    provider_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    provider = db.query(Provider).filter(
        Provider.id == provider_id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found"
        )

    return {
        "id": provider.id,
        "user_id": provider.user_id,
        "business_name": provider.business_name,
        "description": provider.description,
        "location": provider.location,
        "phone": provider.phone,
        "is_verified": provider.is_verified,
        "user_name": provider.user.name,
        "user_email": provider.user.email,
    }


@router.patch(
    "/providers/{provider_id}",
    response_model=AdminProviderResponse
)
def update_provider(
    provider_id: int,
    data: AdminProviderUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    provider = db.query(Provider).filter(
        Provider.id == provider_id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found"
        )

    updates = data.model_dump(
        exclude_unset=True
    )

    for field, value in updates.items():
        setattr(provider, field, value)

    db.commit()
    db.refresh(provider)

    return {
        "id": provider.id,
        "user_id": provider.user_id,
        "business_name": provider.business_name,
        "description": provider.description,
        "location": provider.location,
        "phone": provider.phone,
        "is_verified": provider.is_verified,
        "user_name": provider.user.name,
        "user_email": provider.user.email,
    }


@router.delete("/providers/{provider_id}")
def delete_provider(
    provider_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    provider = db.query(Provider).filter(
        Provider.id == provider_id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found"
        )

    db.delete(provider)
    db.commit()

    return {
        "message": "Provider deleted successfully"
    }


@router.get(
    "/services",
    response_model=list[AdminServiceResponse]
)
def get_all_services(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    services = db.query(Service).order_by(
        Service.id
    ).all()

    return [
        {
            "id": service.id,
            "provider_id": service.provider_id,
            "category_id": service.category_id,
            "name": service.name,
            "description": service.description,
            "price": float(service.price),
            "duration_minutes": service.duration_minutes,
            "is_active": service.is_active,
            "provider_name": service.provider.business_name,
            "category_name": service.category.name,
        }
        for service in services
    ]


@router.get(
    "/services/{service_id}",
    response_model=AdminServiceResponse
)
def get_service(
    service_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    service = db.query(Service).filter(
        Service.id == service_id
    ).first()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    return {
        "id": service.id,
        "provider_id": service.provider_id,
        "category_id": service.category_id,
        "name": service.name,
        "description": service.description,
        "price": float(service.price),
        "duration_minutes": service.duration_minutes,
        "is_active": service.is_active,
        "provider_name": service.provider.business_name,
        "category_name": service.category.name,
    }


@router.patch(
    "/services/{service_id}",
    response_model=AdminServiceResponse
)
def update_service(
    service_id: int,
    data: AdminServiceUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    service = db.query(Service).filter(
        Service.id == service_id
    ).first()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    if data.price is not None and data.price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Price must be greater than 0"
        )

    if (
        data.duration_minutes is not None
        and data.duration_minutes <= 0
    ):
        raise HTTPException(
            status_code=400,
            detail="Duration must be greater than 0"
        )

    if data.category_id is not None:
        category = db.query(Category).filter(
            Category.id == data.category_id
        ).first()

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

    updates = data.model_dump(
        exclude_unset=True
    )

    for field, value in updates.items():
        setattr(service, field, value)

    db.commit()
    db.refresh(service)

    return {
        "id": service.id,
        "provider_id": service.provider_id,
        "category_id": service.category_id,
        "name": service.name,
        "description": service.description,
        "price": float(service.price),
        "duration_minutes": service.duration_minutes,
        "is_active": service.is_active,
        "provider_name": service.provider.business_name,
        "category_name": service.category.name,
    }


@router.delete("/services/{service_id}")
def delete_service(
    service_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    service = db.query(Service).filter(
        Service.id == service_id
    ).first()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    db.delete(service)
    db.commit()

    return {
        "message": "Service deleted successfully"
    }


@router.get(
    "/bookings",
    response_model=list[AdminBookingResponse]
)
def get_all_bookings(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    bookings = db.query(Booking).order_by(
        Booking.id
    ).all()

    response = []

    for booking in bookings:
        customer = db.query(User).filter(
            User.id == booking.customer_id
        ).first()

        provider = db.query(Provider).filter(
            Provider.id == booking.provider_id
        ).first()

        service = db.query(Service).filter(
            Service.id == booking.service_id
        ).first()

        response.append({
            "id": booking.id,
            "customer_id": booking.customer_id,
            "provider_id": booking.provider_id,
            "service_id": booking.service_id,
            "booking_date": booking.booking_date,
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            "price": float(booking.price),
            "status": booking.status,
            "customer_notes": booking.customer_notes,
            "created_at": booking.created_at,
            "customer_name": customer.name,
            "customer_email": customer.email,
            "provider_name": provider.business_name,
            "service_name": service.name,
        })

    return response


@router.get(
    "/bookings/{booking_id}",
    response_model=AdminBookingResponse
)
def get_admin_booking(
    booking_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    customer = db.query(User).filter(
        User.id == booking.customer_id
    ).first()

    provider = db.query(Provider).filter(
        Provider.id == booking.provider_id
    ).first()

    service = db.query(Service).filter(
        Service.id == booking.service_id
    ).first()

    return {
        "id": booking.id,
        "customer_id": booking.customer_id,
        "provider_id": booking.provider_id,
        "service_id": booking.service_id,
        "booking_date": booking.booking_date,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "price": float(booking.price),
        "status": booking.status,
        "customer_notes": booking.customer_notes,
        "created_at": booking.created_at,
        "customer_name": customer.name,
        "customer_email": customer.email,
        "provider_name": provider.business_name,
        "service_name": service.name,
    }


@router.patch(
    "/bookings/{booking_id}/status",
    response_model=AdminBookingResponse
)
def update_admin_booking_status(
    booking_id: int,
    data: AdminBookingStatusUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    allowed_statuses = [
        "pending",
        "confirmed",
        "completed",
        "cancelled",
        "no_show"
    ]

    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid booking status"
        )

    booking.status = data.status

    db.commit()
    db.refresh(booking)

    customer = db.query(User).filter(
        User.id == booking.customer_id
    ).first()

    provider = db.query(Provider).filter(
        Provider.id == booking.provider_id
    ).first()

    service = db.query(Service).filter(
        Service.id == booking.service_id
    ).first()

    return {
        "id": booking.id,
        "customer_id": booking.customer_id,
        "provider_id": booking.provider_id,
        "service_id": booking.service_id,
        "booking_date": booking.booking_date,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "price": float(booking.price),
        "status": booking.status,
        "customer_notes": booking.customer_notes,
        "created_at": booking.created_at,
        "customer_name": customer.name,
        "customer_email": customer.email,
        "provider_name": provider.business_name,
        "service_name": service.name,
    }


@router.delete("/bookings/{booking_id}")
def delete_admin_booking(
    booking_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    db.delete(booking)
    db.commit()

    return {
        "message": "Booking deleted successfully"
    }


@router.get(
    "/reviews",
    response_model=list[AdminReviewResponse]
)
def get_all_reviews(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    reviews = db.query(Review).order_by(
        Review.id
    ).all()

    response = []

    for review in reviews:
        customer = db.query(User).filter(
            User.id == review.customer_id
        ).first()

        provider = db.query(Provider).filter(
            Provider.id == review.provider_id
        ).first()

        response.append({
            "id": review.id,
            "booking_id": review.booking_id,
            "customer_id": review.customer_id,
            "provider_id": review.provider_id,
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at,
            "updated_at": review.updated_at,
            "customer_name": customer.name,
            "customer_email": customer.email,
            "provider_name": provider.business_name,
        })

    return response


@router.get(
    "/reviews/{review_id}",
    response_model=AdminReviewResponse
)
def get_review(
    review_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(
        Review.id == review_id
    ).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found"
        )

    customer = db.query(User).filter(
        User.id == review.customer_id
    ).first()

    provider = db.query(Provider).filter(
        Provider.id == review.provider_id
    ).first()

    return {
        "id": review.id,
        "booking_id": review.booking_id,
        "customer_id": review.customer_id,
        "provider_id": review.provider_id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "customer_name": customer.name,
        "customer_email": customer.email,
        "provider_name": provider.business_name,
    }


@router.patch(
    "/reviews/{review_id}",
    response_model=AdminReviewResponse
)
def update_review(
    review_id: int,
    data: AdminReviewUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(
        Review.id == review_id
    ).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found"
        )

    if data.rating is not None:
        if data.rating < 1 or data.rating > 5:
            raise HTTPException(
                status_code=400,
                detail="Rating must be between 1 and 5"
            )

        review.rating = data.rating

    if data.comment is not None:
        review.comment = data.comment

    db.commit()
    db.refresh(review)

    customer = db.query(User).filter(
        User.id == review.customer_id
    ).first()

    provider = db.query(Provider).filter(
        Provider.id == review.provider_id
    ).first()

    return {
        "id": review.id,
        "booking_id": review.booking_id,
        "customer_id": review.customer_id,
        "provider_id": review.provider_id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "customer_name": customer.name,
        "customer_email": customer.email,
        "provider_name": provider.business_name,
    }


@router.delete(
    "/reviews/{review_id}"
)
def delete_review(
    review_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(
        Review.id == review_id
    ).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found"
        )

    db.delete(review)
    db.commit()

    return {
        "message": "Review deleted successfully"
    }


@router.get(
    "/complaints",
    response_model=list[AdminComplaintResponse]
)
def get_all_complaints(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    complaints = db.query(Complaint).order_by(
        Complaint.id.desc()
    ).all()

    response = []

    for complaint in complaints:
        customer = db.query(User).filter(
            User.id == complaint.customer_id
        ).first()

        provider = None

        if complaint.provider_id is not None:
            provider = db.query(Provider).filter(
                Provider.id == complaint.provider_id
            ).first()

        response.append({
            "id": complaint.id,
            "customer_id": complaint.customer_id,
            "provider_id": complaint.provider_id,
            "booking_id": complaint.booking_id,
            "subject": complaint.subject,
            "description": complaint.description,
            "status": complaint.status,
            "admin_response": complaint.admin_response,
            "created_at": complaint.created_at,
            "updated_at": complaint.updated_at,
            "customer_name": customer.name,
            "customer_email": customer.email,
            "provider_name": (
                provider.business_name
                if provider else None
            ),
        })

    return response


@router.get(
    "/complaints/{complaint_id}",
    response_model=AdminComplaintResponse
)
def get_admin_complaint(
    complaint_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    complaint = db.query(Complaint).filter(
        Complaint.id == complaint_id
    ).first()

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found"
        )

    customer = db.query(User).filter(
        User.id == complaint.customer_id
    ).first()

    provider = None

    if complaint.provider_id is not None:
        provider = db.query(Provider).filter(
            Provider.id == complaint.provider_id
        ).first()

    return {
        "id": complaint.id,
        "customer_id": complaint.customer_id,
        "provider_id": complaint.provider_id,
        "booking_id": complaint.booking_id,
        "subject": complaint.subject,
        "description": complaint.description,
        "status": complaint.status,
        "admin_response": complaint.admin_response,
        "created_at": complaint.created_at,
        "updated_at": complaint.updated_at,
        "customer_name": customer.name,
        "customer_email": customer.email,
        "provider_name": (
            provider.business_name
            if provider else None
        ),
    }


@router.patch(
    "/complaints/{complaint_id}",
    response_model=AdminComplaintResponse
)
def update_admin_complaint(
    complaint_id: int,
    data: AdminComplaintUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    complaint = db.query(Complaint).filter(
        Complaint.id == complaint_id
    ).first()

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found"
        )

    allowed_statuses = [
        "open",
        "in_progress",
        "resolved",
        "closed"
    ]

    if (
        data.status is not None
        and data.status not in allowed_statuses
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid complaint status"
        )

    updates = data.model_dump(
        exclude_unset=True
    )

    for field, value in updates.items():
        setattr(complaint, field, value)

    db.commit()
    db.refresh(complaint)

    customer = db.query(User).filter(
        User.id == complaint.customer_id
    ).first()

    provider = None

    if complaint.provider_id is not None:
        provider = db.query(Provider).filter(
            Provider.id == complaint.provider_id
        ).first()

    return {
        "id": complaint.id,
        "customer_id": complaint.customer_id,
        "provider_id": complaint.provider_id,
        "booking_id": complaint.booking_id,
        "subject": complaint.subject,
        "description": complaint.description,
        "status": complaint.status,
        "admin_response": complaint.admin_response,
        "created_at": complaint.created_at,
        "updated_at": complaint.updated_at,
        "customer_name": customer.name,
        "customer_email": customer.email,
        "provider_name": (
            provider.business_name
            if provider else None
        ),
    }


@router.delete("/complaints/{complaint_id}")
def delete_admin_complaint(
    complaint_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    complaint = db.query(Complaint).filter(
        Complaint.id == complaint_id
    ).first()

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found"
        )

    db.delete(complaint)
    db.commit()

    return {
        "message": "Complaint deleted successfully"
    }


@router.get(
    "/statistics",
    response_model=AdminStatisticsResponse
)
def get_admin_statistics(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    total_users = db.query(User).count()

    total_customers = db.query(User).filter(
        User.role == "customer"
    ).count()

    total_providers = db.query(User).filter(
        User.role == "provider"
    ).count()

    total_services = db.query(Service).count()

    total_bookings = db.query(Booking).count()

    pending_bookings = db.query(Booking).filter(
        Booking.status == "pending"
    ).count()

    confirmed_bookings = db.query(Booking).filter(
        Booking.status == "confirmed"
    ).count()

    completed_bookings = db.query(Booking).filter(
        Booking.status == "completed"
    ).count()

    cancelled_bookings = db.query(Booking).filter(
        Booking.status == "cancelled"
    ).count()

    no_show_bookings = db.query(Booking).filter(
        Booking.status == "no_show"
    ).count()

    total_reviews = db.query(Review).count()

    average_rating = db.query(
        func.avg(Review.rating)
    ).scalar()

    total_complaints = db.query(
        Complaint
    ).count()

    open_complaints = db.query(
        Complaint
    ).filter(
        Complaint.status == "open"
    ).count()

    in_progress_complaints = db.query(
        Complaint
    ).filter(
        Complaint.status == "in_progress"
    ).count()

    resolved_complaints = db.query(
        Complaint
    ).filter(
        Complaint.status == "resolved"
    ).count()

    closed_complaints = db.query(
        Complaint
    ).filter(
        Complaint.status == "closed"
    ).count()

    total_revenue = db.query(
        func.sum(Booking.price)
    ).filter(
        Booking.status == "completed"
    ).scalar()

    return {
        "total_users": total_users,
        "total_customers": total_customers,
        "total_providers": total_providers,
        "total_services": total_services,
        "total_bookings": total_bookings,
        "pending_bookings": pending_bookings,
        "confirmed_bookings": confirmed_bookings,
        "completed_bookings": completed_bookings,
        "cancelled_bookings": cancelled_bookings,
        "no_show_bookings": no_show_bookings,
        "total_reviews": total_reviews,
        "average_rating": round(
            float(average_rating or 0),
            2
        ),
        "total_complaints": total_complaints,
        "open_complaints": open_complaints,
        "in_progress_complaints": in_progress_complaints,
        "resolved_complaints": resolved_complaints,
        "closed_complaints": closed_complaints,
        "total_revenue": float(
            total_revenue or 0
        ),
    }
