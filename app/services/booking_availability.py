from datetime import date, time

from sqlalchemy.orm import Session

from app.models.availability import (
    Availability,
    ProviderBlockedDate,
    ProviderBlockedTime,
)
from app.models.booking import Booking


def time_to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def minutes_to_time(minutes: int) -> time:
    hours = minutes // 60
    mins = minutes % 60
    return time(hour=hours, minute=mins)


def ranges_overlap(
    start1: int,
    end1: int,
    start2: int,
    end2: int,
) -> bool:
    return start1 < end2 and end1 > start2


def available_slots(
    db: Session,
    provider_id: int,
    duration_minutes: int,
    booking_date: date,
    exclude_booking_id: int | None = None,
):
    """
    Generate available booking slots.

    provider_id:
        Provider ID

    duration_minutes:
        Service duration

    booking_date:
        Selected booking date

    exclude_booking_id:
        Used when rescheduling an existing booking.
    """

    # =========================================================
    # BASIC VALIDATION
    # =========================================================

    if duration_minutes <= 0:
        return []

    # Python weekday:
    # Monday    = 0
    # Tuesday   = 1
    # Wednesday = 2
    # Thursday  = 3
    # Friday    = 4
    # Saturday  = 5
    # Sunday    = 6

    day_of_week = booking_date.weekday()

    # =========================================================
    # BLOCKED DATE
    # =========================================================

    blocked_date = (
        db.query(ProviderBlockedDate)
        .filter(
            ProviderBlockedDate.provider_id == provider_id,
            ProviderBlockedDate.blocked_date == booking_date,
        )
        .first()
    )

    if blocked_date:
        return []

    # =========================================================
    # PROVIDER AVAILABILITY
    # =========================================================

    availability = (
        db.query(Availability)
        .filter(
            Availability.provider_id == provider_id,
            Availability.day_of_week == day_of_week,
            Availability.is_available.is_(True),
        )
        .first()
    )

    if not availability:
        return []

    if not availability.start_time or not availability.end_time:
        return []

    work_start = time_to_minutes(availability.start_time)
    work_end = time_to_minutes(availability.end_time)

    if work_end <= work_start:
        return []

    # =========================================================
    # SLOT DURATION
    # =========================================================

    slot_duration = availability.slot_duration or 30

    if slot_duration <= 0:
        slot_duration = 30

    # =========================================================
    # BREAK
    # =========================================================

    break_start = None
    break_end = None

    if availability.break_start and availability.break_end:

        break_start = time_to_minutes(
            availability.break_start
        )

        break_end = time_to_minutes(
            availability.break_end
        )

        if break_end <= break_start:
            break_start = None
            break_end = None

    # =========================================================
    # EXISTING BOOKINGS
    # =========================================================

    booking_query = (
        db.query(Booking)
        .filter(
            Booking.provider_id == provider_id,
            Booking.booking_date == booking_date,
            Booking.status.in_(
                [
                    "pending",
                    "confirmed",
                ]
            ),
        )
    )

    if exclude_booking_id is not None:
        booking_query = booking_query.filter(
            Booking.id != exclude_booking_id
        )

    bookings = booking_query.all()

    booked_ranges = []

    for booking in bookings:

        if not booking.start_time or not booking.end_time:
            continue

        booked_start = time_to_minutes(
            booking.start_time
        )

        booked_end = time_to_minutes(
            booking.end_time
        )

        booked_ranges.append(
            (
                booked_start,
                booked_end,
            )
        )

    # =========================================================
    # BLOCKED TIMES
    # =========================================================

    blocked_times = (
        db.query(ProviderBlockedTime)
        .filter(
            ProviderBlockedTime.provider_id == provider_id,
            ProviderBlockedTime.blocked_date == booking_date,
        )
        .all()
    )

    blocked_ranges = []

    for blocked in blocked_times:

        blocked_start = time_to_minutes(
            blocked.start_time
        )

        blocked_end = time_to_minutes(
            blocked.end_time
        )

        blocked_ranges.append(
            (
                blocked_start,
                blocked_end,
            )
        )

    # =========================================================
    # GENERATE SLOTS
    # =========================================================

    slots = []

    current_start = work_start

    while current_start + duration_minutes <= work_end:

        current_end = current_start + duration_minutes

        # -----------------------------------------------------
        # BREAK CHECK
        # -----------------------------------------------------

        if (
            break_start is not None
            and break_end is not None
            and ranges_overlap(
                current_start,
                current_end,
                break_start,
                break_end,
            )
        ):
            current_start += slot_duration
            continue

        # -----------------------------------------------------
        # BLOCKED TIME CHECK
        # -----------------------------------------------------

        blocked = False

        for blocked_start, blocked_end in blocked_ranges:

            if ranges_overlap(
                current_start,
                current_end,
                blocked_start,
                blocked_end,
            ):
                blocked = True
                break

        if blocked:
            current_start += slot_duration
            continue

        # -----------------------------------------------------
        # BOOKING CHECK
        # -----------------------------------------------------

        booked = False

        for booked_start, booked_end in booked_ranges:

            if ranges_overlap(
                current_start,
                current_end,
                booked_start,
                booked_end,
            ):
                booked = True
                break

        if booked:
            current_start += slot_duration
            continue

        # -----------------------------------------------------
        # AVAILABLE
        # -----------------------------------------------------

        slots.append(
            (
                minutes_to_time(current_start),
                minutes_to_time(current_end),
            )
        )

        current_start += slot_duration

    return slots