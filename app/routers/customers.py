from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.availability import Availability
from app.models.booking import Booking
from app.models.provider import Provider
from app.models.review import Review
from app.models.service import Service
from app.models.user import User
from app.schemas.customer import (
    CustomerDashboardResponse,
    CustomerProfileResponse,
    CustomerProfileUpdate
)
from app.utils.auth import require_role
from app.schemas.booking import CustomerBookingResponse

router = APIRouter(
    prefix="/customer",
    tags=["Customer"]
)


@router.get(
    "/profile",
    response_model=CustomerProfileResponse
)
def get_customer_profile(
    current_user: User = Depends(require_role("customer"))
):
    return current_user


@router.put(
    "/profile",
    response_model=CustomerProfileResponse
)
def update_customer_profile(
    data: CustomerProfileUpdate,
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db)
):
    if data.name is not None:
        if not data.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name cannot be empty"
            )

        current_user.name = data.name.strip()

    db.commit()
    db.refresh(current_user)

    return current_user


@router.get(
    "/dashboard",
    response_model=CustomerDashboardResponse
)
def get_customer_dashboard(
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db)
):
    bookings = db.query(Booking).filter(
        Booking.customer_id == current_user.id
    ).all()

    total_bookings = len(bookings)

    pending_bookings = sum(
        1 for booking in bookings
        if booking.status == "pending"
    )

    confirmed_bookings = sum(
        1 for booking in bookings
        if booking.status == "confirmed"
    )

    completed_bookings = sum(
        1 for booking in bookings
        if booking.status == "completed"
    )

    cancelled_bookings = sum(
        1 for booking in bookings
        if booking.status == "cancelled"
    )

    no_show_bookings = sum(
        1 for booking in bookings
        if booking.status == "no_show"
    )

    total_spent = sum(
        float(booking.price or 0)
        for booking in bookings
        if booking.status == "completed"
    )

    reviews = db.query(Review).filter(
        Review.customer_id == current_user.id
    ).all()

    total_reviews = len(reviews)

    average_rating = (
        sum(review.rating for review in reviews) / total_reviews
        if total_reviews
        else 0
    )

    return CustomerDashboardResponse(
        total_bookings=total_bookings,
        pending_bookings=pending_bookings,
        confirmed_bookings=confirmed_bookings,
        completed_bookings=completed_bookings,
        cancelled_bookings=cancelled_bookings,
        no_show_bookings=no_show_bookings,
        total_spent=total_spent,
        total_reviews=total_reviews,
        average_rating=round(average_rating, 2)
    )


@router.get(
    "/services/{service_id}/slots"
)
def get_customer_service_slots(
    service_id: int,
    booking_date: date = Query(...),
    db: Session = Depends(get_db)
):
    service = db.query(Service).filter(
        Service.id == service_id,
        Service.is_active.is_(True)
    ).first()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    provider = db.query(Provider).filter(
        Provider.id == service.provider_id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found"
        )

    availability = db.query(Availability).filter(
        Availability.provider_id == provider.id,
        Availability.day_of_week == booking_date.weekday(),
        Availability.is_available.is_(True)
    ).first()

    if not availability:
        return {
            "service_id": service.id,
            "service_name": service.name,
            "provider_id": provider.id,
            "business_name": provider.business_name,
            "date": booking_date,
            "service_duration": service.duration_minutes,
            "available_slots": []
        }

    bookings = db.query(Booking).filter(
        Booking.provider_id == provider.id,
        Booking.booking_date == booking_date,
        Booking.status.in_(
            ["pending", "confirmed"]
        )
    ).all()

    available_slots = []

    current = datetime.combine(
        booking_date,
        availability.start_time
    )

    working_end = datetime.combine(
        booking_date,
        availability.end_time
    )

    break_start = (
        datetime.combine(
            booking_date,
            availability.break_start
        )
        if availability.break_start
        else None
    )

    break_end = (
        datetime.combine(
            booking_date,
            availability.break_end
        )
        if availability.break_end
        else None
    )

    while current + timedelta(
        minutes=service.duration_minutes
    ) <= working_end:

        slot_end = current + timedelta(
            minutes=service.duration_minutes
        )

        conflict = False

        if break_start and break_end:
            if (
                current < break_end
                and slot_end > break_start
            ):
                conflict = True

        if not conflict:
            for booking in bookings:
                booking_start = datetime.combine(
                    booking_date,
                    booking.start_time
                )

                booking_end = datetime.combine(
                    booking_date,
                    booking.end_time
                )

                if (
                    current < booking_end
                    and slot_end > booking_start
                ):
                    conflict = True
                    break

        if not conflict:
            available_slots.append({
                "start_time": current.strftime("%H:%M:%S"),
                "end_time": slot_end.strftime("%H:%M:%S")
            })

        current += timedelta(
            minutes=availability.slot_duration
        )

    return {
        "service_id": service.id,
        "service_name": service.name,
        "provider_id": provider.id,
        "business_name": provider.business_name,
        "date": booking_date,
        "service_duration": service.duration_minutes,
        "available_slots": available_slots
    }

@router.get(
    "/bookings",
    response_model=list[CustomerBookingResponse]
)
def get_customer_booking_history(
    status: str | None = Query(default=None),
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db)
):
    query = (
        db.query(
            Booking,
            Service.name.label("service_name"),
            Provider.business_name.label("business_name"),
            Provider.location.label("provider_location"),
            Provider.phone.label("provider_phone")
        )
        .join(
            Service,
            Booking.service_id == Service.id
        )
        .join(
            Provider,
            Booking.provider_id == Provider.id
        )
        .filter(
            Booking.customer_id == current_user.id
        )
    )

    if status:
        allowed_statuses = [
            "pending",
            "confirmed",
            "completed",
            "cancelled",
            "no_show"
        ]

        if status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid booking status"
            )

        query = query.filter(
            Booking.status == status
        )

    results = query.order_by(
        Booking.booking_date.desc(),
        Booking.start_time.desc()
    ).all()

    response = []

    for booking, service_name, business_name, provider_location, provider_phone in results:
        response.append(
            CustomerBookingResponse(
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
                service_name=service_name,
                business_name=business_name,
                provider_location=provider_location,
                provider_phone=provider_phone
            )
        )

    return response
