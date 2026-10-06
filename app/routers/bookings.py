from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import Booking
from app.models.provider import Provider
from app.models.service import Service
from app.models.user import User
from app.services.booking_availability import available_slots
from app.routers.auth import get_current_user

from app.schemas.booking import (
    BookingCreate,
    BookingReschedule,
    BookingResponse,
    CustomerBookingResponse,
    ProviderBookingResponse,
)


router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"],
)

@router.get("/debug-slots/{provider_id}")
def debug_slots(
    provider_id: int,
    service_id: int,
    booking_date: date,
    db: Session = Depends(get_db),
):
    service = (
        db.query(Service)
        .filter(Service.id == service_id)
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    slots = available_slots(
        db,
        provider_id,
        service.duration_minutes,
        booking_date,
    )

    return {
        "provider_id": provider_id,
        "service_id": service_id,
        "service_duration": service.duration_minutes,
        "booking_date": booking_date,
        "slots": [
            {
                "start": start.strftime("%H:%M"),
                "end": end.strftime("%H:%M"),
            }
            for start, end in slots
        ],
    }


# =========================================================
# PROVIDER ROLE CHECK
# =========================================================

def require_provider(
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "provider":
        raise HTTPException(
            status_code=403,
            detail="Provider access required",
        )

    return current_user


# =========================================================
# PROVIDER BOOKINGS
# =========================================================

@router.get(
    "/provider/me",
    response_model=list[ProviderBookingResponse],
)
def get_my_provider_bookings(
    current_user: User = Depends(require_provider),
    db: Session = Depends(get_db),
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
            status_code=404,
            detail="Provider profile not found",
        )

    results = (
        db.query(
            Booking,
            User.name.label("customer_name"),
            Service.name.label("service_name"),
        )
        .join(
            User,
            Booking.customer_id == User.id,
        )
        .join(
            Service,
            Booking.service_id == Service.id,
        )
        .filter(
            Booking.provider_id == provider.id
        )
        .order_by(
            Booking.booking_date.desc(),
            Booking.start_time.desc(),
        )
        .all()
    )

    response = []

    for booking, customer_name, service_name in results:
        response.append(
            {
                "id": booking.id,
                "customer_id": booking.customer_id,
                "provider_id": booking.provider_id,
                "service_id": booking.service_id,
                "customer_name": customer_name,
                "service_name": service_name,
                "booking_date": booking.booking_date,
                "start_time": booking.start_time,
                "end_time": booking.end_time,
                "price": booking.price,
                "status": booking.status,
                "customer_notes": booking.customer_notes,
                "service_address": booking.service_address,
                "created_at": booking.created_at,
            }
        )

    return response


@router.get("/provider/me/stats")
def get_my_booking_stats(
    current_user: User = Depends(require_provider),
    db: Session = Depends(get_db),
):
    provider = (
        db.query(Provider)
        .filter(Provider.user_id == current_user.id)
        .first()
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")

    counts = dict(
        db.query(Booking.status, func.count(Booking.id))
        .filter(Booking.provider_id == provider.id)
        .group_by(Booking.status)
        .all()
    )
    return {
        "total": sum(counts.values()),
        "pending": counts.get("pending", 0),
        "confirmed": counts.get("confirmed", 0),
        "completed": counts.get("completed", 0),
        "rejected": counts.get("rejected", 0),
        "cancelled": counts.get("cancelled", 0),
    }


# =========================================================
# PROVIDER BOOKINGS BY PROVIDER ID
# =========================================================

@router.get(
    "/provider/{provider_id}",
    response_model=list[ProviderBookingResponse],
)
def get_provider_bookings(
    provider_id: int,
    current_user: User = Depends(require_provider),
    db: Session = Depends(get_db),
):
    provider = (
        db.query(Provider)
        .filter(
            Provider.id == provider_id
        )
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    if provider.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only access your own bookings",
        )

    results = (
        db.query(
            Booking,
            User.name.label("customer_name"),
            Service.name.label("service_name"),
        )
        .join(
            User,
            Booking.customer_id == User.id,
        )
        .join(
            Service,
            Booking.service_id == Service.id,
        )
        .filter(
            Booking.provider_id == provider_id
        )
        .order_by(
            Booking.booking_date.desc(),
            Booking.start_time.desc(),
        )
        .all()
    )

    response = []

    for booking, customer_name, service_name in results:
        response.append(
            {
                "id": booking.id,
                "customer_id": booking.customer_id,
                "provider_id": booking.provider_id,
                "service_id": booking.service_id,
                "customer_name": customer_name,
                "service_name": service_name,
                "booking_date": booking.booking_date,
                "start_time": booking.start_time,
                "end_time": booking.end_time,
                "price": booking.price,
                "status": booking.status,
                "customer_notes": booking.customer_notes,
                "service_address": booking.service_address,
                "created_at": booking.created_at,
            }
        )

    return response


# =========================================================
# UPDATE BOOKING STATUS
# =========================================================

@router.patch(
    "/{booking_id}/status",
    response_model=BookingResponse,
)
def update_booking_status(
    booking_id: int,
    status: str = Query(...),
    current_user: User = Depends(require_provider),
    db: Session = Depends(get_db),
):
    allowed_transitions = {
        "pending": {"confirmed", "rejected"},
        "confirmed": {"completed", "no_show", "cancelled"},
    }

    if status not in {"confirmed", "rejected", "completed", "no_show", "cancelled"}:
        raise HTTPException(
            status_code=400,
            detail="Providers can accept, reject, or complete bookings",
        )

    provider = (
        db.query(Provider)
        .filter(
            Provider.user_id == current_user.id
        )
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider profile not found",
        )

    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    if booking.provider_id != provider.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own bookings",
        )

    if status not in allowed_transitions.get(booking.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change a {booking.status} booking to {status}",
        )

    booking.status = status

    db.commit()
    db.refresh(booking)

    return booking


# =========================================================
# RESCHEDULE BOOKING
# =========================================================

@router.patch(
    "/{booking_id}/reschedule",
    response_model=BookingResponse,
)
def reschedule_booking(
    booking_id: int,
    booking_data: BookingReschedule,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    if current_user.role == "customer":

        if booking.customer_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only reschedule your own booking",
            )

    elif current_user.role == "provider":

        provider = (
            db.query(Provider)
            .filter(
                Provider.user_id == current_user.id
            )
            .first()
        )

        if not provider:
            raise HTTPException(
                status_code=404,
                detail="Provider profile not found",
            )

        if booking.provider_id != provider.id:
            raise HTTPException(
                status_code=403,
                detail="You can only reschedule your own bookings",
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    if booking.status not in {"pending", "confirmed"}:
        raise HTTPException(status_code=409, detail="This booking can no longer be rescheduled")

    provider = (
        db.query(Provider)
        .filter(Provider.id == booking.provider_id)
        .with_for_update()
        .first()
    )
    service = db.query(Service).filter(Service.id == booking.service_id).first()
    if not provider or not service or not service.is_active:
        raise HTTPException(status_code=409, detail="The service is no longer available")

    slots = available_slots(
        db,
        provider.id,
        service.duration_minutes,
        booking_data.booking_date,
        exclude_booking_id=booking.id,
    )
    matching_slot = next(
        (slot for slot in slots if slot[0] == booking_data.start_time),
        None,
    )
    if not matching_slot or matching_slot[1] != booking_data.end_time:
        raise HTTPException(status_code=409, detail="That time is no longer available")

    booking.booking_date = booking_data.booking_date
    booking.start_time, booking.end_time = matching_slot

    booking.status = "pending"

    db.commit()
    db.refresh(booking)

    return booking


# =========================================================
# CREATE BOOKING
# =========================================================

@router.post(
    "/",
    response_model=BookingResponse,
)
def create_booking(
    booking_data: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=403,
            detail="Only customers can create bookings",
        )

    service = (
        db.query(Service)
        .filter(
            Service.id == booking_data.service_id
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    provider = (
        db.query(Provider)
        .filter(
            Provider.id == service.provider_id
        )
        .with_for_update()
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    if not service.is_active:
        raise HTTPException(status_code=409, detail="This service is no longer available")

    if booking_data.provider_id is not None and service.provider_id != booking_data.provider_id:
        raise HTTPException(status_code=400, detail="Service does not belong to this provider")

    if booking_data.booking_date < date.today():
        raise HTTPException(status_code=400, detail="You cannot book a past date")

    slots = available_slots(
        db,
        provider.id,
        service.duration_minutes,
        booking_data.booking_date,
    )
    matching_slot = next(
        (slot for slot in slots if slot[0] == booking_data.start_time),
        None,
    )
    if not matching_slot:
        raise HTTPException(
            status_code=409,
            detail="That time slot is no longer available. Please choose another time.",
        )

    new_booking = Booking(
        customer_id=current_user.id,
        provider_id=provider.id,
        service_id=booking_data.service_id,
        booking_date=booking_data.booking_date,
        start_time=matching_slot[0],
        end_time=matching_slot[1],
        price=service.price,
        status="pending",
        customer_notes=booking_data.customer_notes,
        service_address=booking_data.service_address,
    )

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return new_booking


# =========================================================
# GET CUSTOMER BOOKINGS
# =========================================================

@router.get(
    "/customer/me",
    response_model=list[CustomerBookingResponse],
)
def get_my_customer_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=403,
            detail="Customer access required",
        )

    results = (
        db.query(
            Booking,
            Service.name.label("service_name"),
            Provider.business_name.label("business_name"),
            Provider.location.label("provider_location"),
            Provider.phone.label("provider_phone"),
        )
        .join(
            Service,
            Booking.service_id == Service.id,
        )
        .join(
            Provider,
            Booking.provider_id == Provider.id,
        )
        .filter(
            Booking.customer_id == current_user.id
        )
        .order_by(
            Booking.booking_date.desc(),
            Booking.start_time.desc(),
        )
        .all()
    )

    response = []

    for (
        booking,
        service_name,
        business_name,
        provider_location,
        provider_phone,
    ) in results:

        response.append(
            {
                "id": booking.id,
                "customer_id": booking.customer_id,
                "provider_id": booking.provider_id,
                "service_id": booking.service_id,
                "booking_date": booking.booking_date,
                "start_time": booking.start_time,
                "end_time": booking.end_time,
                "price": booking.price,
                "status": booking.status,
                "customer_notes": booking.customer_notes,
                "service_address": booking.service_address,
                "created_at": booking.created_at,
                "service_name": service_name,
                "business_name": business_name,
                "provider_location": provider_location,
                "provider_phone": provider_phone,
            }
        )

    return response


# =========================================================
# GET ALL BOOKINGS
# =========================================================

@router.get(
    "/",
    response_model=list[BookingResponse],
)
def get_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == "customer":

        return (
            db.query(Booking)
            .filter(
                Booking.customer_id
                == current_user.id
            )
            .all()
        )

    if current_user.role == "provider":

        provider = (
            db.query(Provider)
            .filter(
                Provider.user_id
                == current_user.id
            )
            .first()
        )

        if not provider:
            raise HTTPException(
                status_code=404,
                detail="Provider profile not found",
            )

        return (
            db.query(Booking)
            .filter(
                Booking.provider_id
                == provider.id
            )
            .all()
        )

    return (
        db.query(Booking)
        .all()
    )


# =========================================================
# GET SINGLE BOOKING
# =========================================================

@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
)
def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    if current_user.role == "customer":

        if booking.customer_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

    elif current_user.role == "provider":

        provider = (
            db.query(Provider)
            .filter(
                Provider.user_id
                == current_user.id
            )
            .first()
        )

        if not provider:
            raise HTTPException(
                status_code=404,
                detail="Provider profile not found",
            )

        if booking.provider_id != provider.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

    return booking


# =========================================================
# CANCEL BOOKING
# =========================================================

@router.patch(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
)
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    if current_user.role == "customer":

        if booking.customer_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only cancel your own booking",
            )

    elif current_user.role == "provider":

        provider = (
            db.query(Provider)
            .filter(
                Provider.user_id
                == current_user.id
            )
            .first()
        )

        if not provider:
            raise HTTPException(
                status_code=404,
                detail="Provider profile not found",
            )

        if booking.provider_id != provider.id:
            raise HTTPException(
                status_code=403,
                detail="You can only cancel your own bookings",
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    if booking.status not in {"pending", "confirmed"}:
        raise HTTPException(status_code=409, detail="This booking can no longer be cancelled")

    booking.status = "cancelled"

    db.commit()
    db.refresh(booking)

    return booking
