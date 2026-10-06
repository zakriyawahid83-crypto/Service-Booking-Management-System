from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.availability import Availability, ProviderBlockedDate, ProviderBlockedTime
from app.models.booking import Booking
from app.models.provider import Provider
from app.models.service import Service
from app.models.user import User
from app.services.booking_availability import available_slots
from app.schemas.availability import (
    BlockedDateCreate,
    BlockedDateResponse,
    AvailabilityCreate,
    AvailabilityResponse,
    AvailabilityUpdate,
    BlockedTimeCreate,
    BlockedTimeResponse,
)
from app.routers.auth import get_current_user


router = APIRouter(
    prefix="/availability",
    tags=["Availability"],
)


@router.get("/blocked-times", response_model=list[BlockedTimeResponse])
def get_my_blocked_times(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "provider":
        raise HTTPException(status_code=403, detail="Only providers can manage blocked times")
    provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    query = db.query(ProviderBlockedTime).filter(ProviderBlockedTime.provider_id == provider.id)
    if start_date is not None:
        query = query.filter(ProviderBlockedTime.blocked_date >= start_date)
    if end_date is not None:
        query = query.filter(ProviderBlockedTime.blocked_date <= end_date)
    return query.order_by(ProviderBlockedTime.blocked_date, ProviderBlockedTime.start_time).all()


@router.post("/blocked-times", response_model=BlockedTimeResponse)
def create_blocked_time(
    data: BlockedTimeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "provider":
        raise HTTPException(status_code=403, detail="Only providers can manage blocked times")
    provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    if data.blocked_date < date.today():
        raise HTTPException(status_code=400, detail="A past date cannot be blocked")
    conflict = db.query(Booking.id).filter(
        Booking.provider_id == provider.id,
        Booking.booking_date == data.blocked_date,
        Booking.status.in_(("pending", "confirmed")),
        Booking.start_time < data.end_time,
        Booking.end_time > data.start_time,
    ).first()
    if conflict:
        raise HTTPException(status_code=409, detail="This time overlaps an existing booking")
    row = ProviderBlockedTime(
        provider_id=provider.id,
        blocked_date=data.blocked_date,
        start_time=data.start_time,
        end_time=data.end_time,
        reason=data.reason,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/blocked-times/{blocked_time_id}")
def delete_blocked_time(
    blocked_time_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "provider":
        raise HTTPException(status_code=403, detail="Only providers can manage blocked times")
    provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    row = db.query(ProviderBlockedTime).filter(
        ProviderBlockedTime.id == blocked_time_id,
        ProviderBlockedTime.provider_id == provider.id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Blocked time not found")
    db.delete(row)
    db.commit()
    return {"message": "Blocked time removed"}


@router.get("/blocked-dates", response_model=list[BlockedDateResponse])
def get_my_blocked_dates(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "provider":
        raise HTTPException(status_code=403, detail="Only providers can manage blocked dates")
    provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    query = db.query(ProviderBlockedDate).filter(
        ProviderBlockedDate.provider_id == provider.id
    )
    if start_date is not None:
        query = query.filter(ProviderBlockedDate.blocked_date >= start_date)
    if end_date is not None:
        query = query.filter(ProviderBlockedDate.blocked_date <= end_date)
    return query.order_by(ProviderBlockedDate.blocked_date).all()


@router.post("/blocked-dates", response_model=BlockedDateResponse)
def create_blocked_date(
    data: BlockedDateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "provider":
        raise HTTPException(status_code=403, detail="Only providers can manage blocked dates")
    provider = (
        db.query(Provider)
        .filter(Provider.user_id == current_user.id)
        .with_for_update()
        .first()
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    if data.blocked_date < date.today():
        raise HTTPException(status_code=400, detail="A past date cannot be blocked")
    row = (
        db.query(ProviderBlockedDate)
        .filter(
            ProviderBlockedDate.provider_id == provider.id,
            ProviderBlockedDate.blocked_date == data.blocked_date,
        )
        .first()
    )
    if row:
        row.reason = data.reason
    else:
        row = ProviderBlockedDate(
            provider_id=provider.id,
            blocked_date=data.blocked_date,
            reason=data.reason,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/blocked-dates/{blocked_date}")
def delete_blocked_date(
    blocked_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "provider":
        raise HTTPException(status_code=403, detail="Only providers can manage blocked dates")
    provider = (
        db.query(Provider)
        .filter(Provider.user_id == current_user.id)
        .with_for_update()
        .first()
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    row = (
        db.query(ProviderBlockedDate)
        .filter(
            ProviderBlockedDate.provider_id == provider.id,
            ProviderBlockedDate.blocked_date == blocked_date,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Blocked date not found")
    db.delete(row)
    db.commit()
    return {"message": "Date restored to the provider's schedule"}


# =========================================================
# CREATE AVAILABILITY
# =========================================================

@router.post(
    "/",
    response_model=AvailabilityResponse,
)
def create_availability(
    data: AvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "provider":
        raise HTTPException(
            status_code=403,
            detail="Only providers can create availability",
        )

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

    availability = Availability(
        provider_id=provider.id,
        day_of_week=data.day_of_week,
        start_time=data.start_time,
        end_time=data.end_time,
        break_start=data.break_start,
        break_end=data.break_end,
        slot_duration=data.slot_duration,
        is_available=True,
    )

    db.add(availability)
    db.commit()
    db.refresh(availability)

    return availability


# =========================================================
# GET MY AVAILABILITIES
# =========================================================

@router.get(
    "/my",
    response_model=list[AvailabilityResponse],
)
def get_my_availabilities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "provider":
        raise HTTPException(
            status_code=403,
            detail="Only providers can access availability",
        )

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

    return (
        db.query(Availability)
        .filter(
            Availability.provider_id == provider.id
        )
        .order_by(
            Availability.day_of_week,
            Availability.start_time,
        )
        .all()
    )


# =========================================================
# GET PROVIDER AVAILABILITIES
# =========================================================

@router.get(
    "/provider/{provider_id}",
    response_model=list[AvailabilityResponse],
)
def get_provider_availabilities(
    provider_id: int,
    db: Session = Depends(get_db),
):
    provider = (
        db.query(Provider)
        .filter(Provider.id == provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    return (
        db.query(Availability)
        .filter(
            Availability.provider_id == provider_id
        )
        .order_by(
            Availability.day_of_week,
            Availability.start_time,
        )
        .all()
    )


# =========================================================
# UPDATE AVAILABILITY
# =========================================================

@router.put(
    "/{availability_id}",
    response_model=AvailabilityResponse,
)
def update_availability(
    availability_id: int,
    data: AvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "provider":
        raise HTTPException(
            status_code=403,
            detail="Only providers can update availability",
        )

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

    availability = (
        db.query(Availability)
        .filter(
            Availability.id == availability_id,
            Availability.provider_id == provider.id,
        )
        .first()
    )

    if not availability:
        raise HTTPException(
            status_code=404,
            detail="Availability not found",
        )

    if data.start_time is not None:
        availability.start_time = data.start_time

    if data.end_time is not None:
        availability.end_time = data.end_time

    if "break_start" in data.model_fields_set:
        availability.break_start = data.break_start

    if "break_end" in data.model_fields_set:
        availability.break_end = data.break_end

    if data.slot_duration is not None:
        availability.slot_duration = data.slot_duration

    if data.is_available is not None:
        availability.is_available = data.is_available

    # Validate working hours
    if availability.end_time <= availability.start_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time",
        )

    # Validate break
    if (availability.break_start is None) != (availability.break_end is None):
        raise HTTPException(
            status_code=400,
            detail="Both break start and break end are required",
        )

    if availability.break_start is not None and availability.break_end is not None:
        if availability.break_end <= availability.break_start:
            raise HTTPException(
                status_code=400,
                detail="Break end time must be after break start",
            )

        if availability.break_start < availability.start_time:
            raise HTTPException(
                status_code=400,
                detail="Break must be inside working hours",
            )

        if availability.break_end > availability.end_time:
            raise HTTPException(
                status_code=400,
                detail="Break must be inside working hours",
            )

    db.commit()
    db.refresh(availability)

    return availability


# =========================================================
# DELETE AVAILABILITY
# =========================================================

@router.delete("/{availability_id}")
def delete_availability(
    availability_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "provider":
        raise HTTPException(
            status_code=403,
            detail="Only providers can delete availability",
        )

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

    availability = (
        db.query(Availability)
        .filter(
            Availability.id == availability_id,
            Availability.provider_id == provider.id,
        )
        .first()
    )

    if not availability:
        raise HTTPException(
            status_code=404,
            detail="Availability not found",
        )

    db.delete(availability)
    db.commit()

    return {
        "message": "Availability deleted successfully"
    }


@router.get("/calendar")
def get_provider_calendar(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "provider":
        raise HTTPException(
            status_code=403,
            detail="Only providers can access their calendar",
        )

    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="End date must be on or after start date",
        )

    if (end_date - start_date).days > 30:
        raise HTTPException(
            status_code=400,
            detail="Calendar range cannot exceed 31 days",
        )

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

    availability_rows = (
        db.query(Availability)
        .filter(
            Availability.provider_id == provider.id,
            Availability.is_available == True,
        )
        .order_by(Availability.day_of_week, Availability.start_time)
        .all()
    )
    availability_by_day = {}
    for row in availability_rows:
        availability_by_day.setdefault(row.day_of_week, row)

    blocked_dates = {
        row.blocked_date: row.reason
        for row in db.query(ProviderBlockedDate)
        .filter(
            ProviderBlockedDate.provider_id == provider.id,
            ProviderBlockedDate.blocked_date >= start_date,
            ProviderBlockedDate.blocked_date <= end_date,
        )
        .all()
    }
    blocked_time_rows = db.query(ProviderBlockedTime).filter(
        ProviderBlockedTime.provider_id == provider.id,
        ProviderBlockedTime.blocked_date >= start_date,
        ProviderBlockedTime.blocked_date <= end_date,
    ).order_by(ProviderBlockedTime.blocked_date, ProviderBlockedTime.start_time).all()
    blocked_times_by_date = {}
    for row in blocked_time_rows:
        blocked_times_by_date.setdefault(row.blocked_date, []).append({
            "id": row.id,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "reason": row.reason,
        })

    booking_rows = (
        db.query(
            Booking,
            Service.name.label("service_name"),
            Service.duration_minutes.label("service_duration"),
            User.name.label("customer_name"),
            User.email.label("customer_email"),
        )
        .join(Service, Service.id == Booking.service_id)
        .join(User, User.id == Booking.customer_id)
        .filter(
            Booking.provider_id == provider.id,
            Booking.booking_date >= start_date,
            Booking.booking_date <= end_date,
        )
        .order_by(Booking.booking_date, Booking.start_time)
        .all()
    )
    bookings_by_date = {}
    for booking, service_name, service_duration, customer_name, customer_email in booking_rows:
        bookings_by_date.setdefault(booking.booking_date, []).append({
            "booking_id": booking.id,
            "service_id": booking.service_id,
            "service_name": service_name,
            "service_duration": service_duration,
            "customer_id": booking.customer_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            "price": booking.price,
            "status": booking.status,
            "customer_notes": booking.customer_notes,
        })

    calendar = []
    current_date = start_date
    while current_date <= end_date:
        availability = availability_by_day.get(current_date.weekday())
        is_blocked = current_date in blocked_dates
        calendar.append({
            "date": current_date,
            "day_of_week": current_date.weekday(),
            "is_available": availability is not None and not is_blocked,
            "is_blocked": is_blocked,
            "blocked_reason": blocked_dates.get(current_date),
            "blocked_times": blocked_times_by_date.get(current_date, []),
            "start_time": availability.start_time if availability else None,
            "end_time": availability.end_time if availability else None,
            "break_start": availability.break_start if availability else None,
            "break_end": availability.break_end if availability else None,
            "slot_duration": availability.slot_duration if availability else None,
            "bookings": bookings_by_date.get(current_date, []),
        })
        current_date += timedelta(days=1)

    return {
        "provider_id": provider.id,
        "start_date": start_date,
        "end_date": end_date,
        "calendar": calendar,
    }


# =========================================================
# AVAILABLE SLOTS
# =========================================================

@router.get("/slots/{provider_id}")
def get_available_slots(
    provider_id: int,
    date: date = Query(...),
    service_id: int = Query(...),
    db: Session = Depends(get_db),
):
    # -----------------------------------------------------
    # Check provider
    # -----------------------------------------------------

    provider = (
        db.query(Provider)
        .filter(Provider.id == provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    # -----------------------------------------------------
    # Check service
    # -----------------------------------------------------

    service = (
        db.query(Service)
        .filter(
            Service.id == service_id,
            Service.provider_id == provider_id,
            Service.is_active == True,
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found for this provider",
        )

    service_duration = service.duration_minutes
    slots = available_slots(
        db,
        provider_id,
        service_duration,
        date,
    )

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "provider_id": provider_id,
        "service_id": service_id,
        "date": date.isoformat(),
        "service_duration": service_duration,
            "available_slots": [
                {
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                }
                for start, end in slots
            ],
    }
