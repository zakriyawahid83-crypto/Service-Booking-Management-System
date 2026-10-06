from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.service import Service
from app.models.provider import Provider
from app.models.category import Category
from app.models.review import Review
from app.models.availability import Availability
from app.models.booking import Booking
from app.schemas.search import SearchServiceResponse


router = APIRouter(
    prefix="/search",
    tags=["Search"]
)


@router.get(
    "/services",
    response_model=list[SearchServiceResponse]
)
def search_services(
    q: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    location: str | None = Query(default=None),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    search_date: date | None = Query(default=None),
    db: Session = Depends(get_db)
):
    query = (
        db.query(
            Service.id.label("service_id"),
            Service.name.label("service_name"),
            Service.description,
            Service.price,
            Service.duration_minutes,

            Provider.id.label("provider_id"),
            Provider.business_name.label("provider_name"),
            Provider.location.label("provider_location"),

            Category.id.label("category_id"),
            Category.name.label("category_name"),

            func.coalesce(
                func.avg(Review.rating),
                0
            ).label("average_rating"),

            func.count(Review.id).label("total_reviews")
        )
        .join(
            Provider,
            Service.provider_id == Provider.id
        )
        .outerjoin(
            Category,
            Service.category_id == Category.id
        )
        .outerjoin(
            Review,
            Review.provider_id == Provider.id
        )
        .filter(
            Service.is_active == True
        )
    )

    if q:
        search_text = f"%{q}%"

        query = query.filter(
            Service.name.ilike(search_text)
            |
            Service.description.ilike(search_text)
            |
            Provider.business_name.ilike(search_text)
        )

    if category_id is not None:
        query = query.filter(
            Service.category_id == category_id
        )

    if location:
        query = query.filter(
            Provider.location.ilike(
                f"%{location}%"
            )
        )

    if min_price is not None:
        query = query.filter(
            Service.price >= min_price
        )

    if max_price is not None:
        query = query.filter(
            Service.price <= max_price
        )

    query = query.group_by(
        Service.id,
        Service.name,
        Service.description,
        Service.price,
        Service.duration_minutes,

        Provider.id,
        Provider.business_name,
        Provider.location,

        Category.id,
        Category.name
    )

    if min_rating is not None:
        query = query.having(
            func.coalesce(
                func.avg(Review.rating),
                0
            ) >= min_rating
        )

    results = query.all()

    response = []

    for item in results:

        available_slots = None

        if search_date:

            day_of_week = search_date.weekday()

            availability = db.query(
                Availability
            ).filter(
                Availability.provider_id == item.provider_id,
                Availability.day_of_week == day_of_week,
                Availability.is_available == True
            ).first()

            if not availability:
                continue

            bookings = db.query(
                Booking
            ).filter(
                Booking.provider_id == item.provider_id,
                Booking.booking_date == search_date,
                Booking.status.in_(
                    ["pending", "confirmed"]
                )
            ).all()

            available_slots = []

            current = datetime.combine(
                search_date,
                availability.start_time
            )

            working_end = datetime.combine(
                search_date,
                availability.end_time
            )

            break_start = None
            break_end = None

            if (
                availability.break_start
                and availability.break_end
            ):
                break_start = datetime.combine(
                    search_date,
                    availability.break_start
                )

                break_end = datetime.combine(
                    search_date,
                    availability.break_end
                )

            while (
                current
                + timedelta(
                    minutes=item.duration_minutes
                )
                <= working_end
            ):

                slot_end = current + timedelta(
                    minutes=item.duration_minutes
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
                            search_date,
                            booking.start_time
                        )

                        booking_end = datetime.combine(
                            search_date,
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
                        "start_time": current.strftime(
                            "%H:%M:%S"
                        ),
                        "end_time": slot_end.strftime(
                            "%H:%M:%S"
                        )
                    })

                current += timedelta(
                    minutes=availability.slot_duration
                )

            if not available_slots:
                continue

        response.append({
            "service_id": item.service_id,
            "service_name": item.service_name,
            "description": item.description,
            "price": float(item.price),
            "duration_minutes": item.duration_minutes,

            "provider_id": item.provider_id,
            "provider_name": item.provider_name,
            "provider_location": item.provider_location,

            "category_id": item.category_id,
            "category_name": item.category_name,

            "average_rating": round(
                float(item.average_rating),
                2
            ),

            "total_reviews": item.total_reviews,

            "available_slots": available_slots
        })

    return response
