from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import Booking
from app.models.review import Review
from app.models.provider import Provider
from app.models.service import Service
from app.models.user import User
from app.schemas.review import (
    ReviewCreate,
    ReviewDisplayResponse,
    ReviewUpdate,
    ReviewResponse
)
from app.utils.auth import get_current_user
from app.utils.notifications import create_notification


router = APIRouter(
    prefix="/reviews",
    tags=["Reviews"]
)


def _get_review_display_rows(
    db: Session,
    customer_id: int | None = None,
    provider_id: int | None = None,
):
    query = (
        db.query(
            Review,
            User.name,
            Service.name,
            Provider.business_name,
            Booking.status,
            Booking.booking_date,
            Booking.start_time,
            Booking.end_time,
            Booking.price,
            Booking.customer_id,
            Booking.provider_id,
        )
        .join(Booking, Booking.id == Review.booking_id)
        .join(User, User.id == Review.customer_id)
        .join(
            Service,
            (Service.id == Booking.service_id)
            & (Service.provider_id == Booking.provider_id),
        )
        .join(Provider, Provider.id == Booking.provider_id)
    )

    if customer_id is not None:
        query = query.filter(
            Review.customer_id == customer_id,
            Booking.customer_id == customer_id,
        )
    if provider_id is not None:
        query = query.filter(
            Review.provider_id == provider_id,
            Booking.provider_id == provider_id,
        )

    rows = query.order_by(Review.created_at.desc()).all()

    return [
        {
            "id": review.id,
            "booking_id": review.booking_id,
            "customer_id": review.customer_id,
            "provider_id": review.provider_id,
            "rating": review.rating,
            "title": review.title,
            "comment": review.comment,
            "created_at": review.created_at,
            "updated_at": review.updated_at,
            "customer_name": customer_name,
            "service_name": service_name,
            "provider_name": provider_name,
            "booking_date": booking_date,
            "booking_start_time": booking_start_time,
            "booking_end_time": booking_end_time,
            "booking_price": float(booking_price),
            "booking_status": booking_status,
            "verified_booking": (
                booking_status == "completed"
                and review.customer_id == booking_customer_id
                and review.provider_id == booking_provider_id
            ),
        }
        for (
            review,
            customer_name,
            service_name,
            provider_name,
            booking_status,
            booking_date,
            booking_start_time,
            booking_end_time,
            booking_price,
            booking_customer_id,
            booking_provider_id,
        ) in rows
    ]


@router.get("/provider/me", response_model=list[ReviewDisplayResponse])
def get_my_provider_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "provider":
        raise HTTPException(
            status_code=403,
            detail="Only providers can access provider reviews",
        )

    provider = db.query(Provider).filter(
        Provider.user_id == current_user.id
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")

    return _get_review_display_rows(db, provider_id=provider.id)


@router.post("/", response_model=ReviewResponse)
def create_review(
    data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=403,
            detail="Only customers can create reviews"
        )

    booking = db.query(Booking).filter(
        Booking.id == data.booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if booking.customer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only review your own booking"
        )

    if booking.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="You can only review a completed booking"
        )

    clean_comment = data.comment.strip()
    if not clean_comment:
        raise HTTPException(
            status_code=400,
            detail="Review text cannot be blank",
        )

    existing_review = db.query(Review).filter(
        Review.booking_id == booking.id
    ).first()

    if existing_review:
        raise HTTPException(
            status_code=409,
            detail="This booking has already been reviewed"
        )

    review = Review(
        booking_id=booking.id,
        customer_id=current_user.id,
        provider_id=booking.provider_id,
        rating=data.rating,
        title=data.title.strip() or None if data.title else None,
        comment=clean_comment,
    )

    db.add(review)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This booking has already been reviewed",
        )
    db.refresh(review)

    provider = db.query(Provider).filter(
        Provider.id == booking.provider_id
    ).first()

    if provider:
        create_notification(
            db=db,
            user_id=provider.user_id,
            title="New Review",
            message=f"You received a {data.rating}-star review for booking #{booking.id}.",
            notification_type="new_review"
        )
        db.commit()

    return review


@router.get("/my", response_model=list[ReviewDisplayResponse])
def get_my_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=403,
            detail="Only customers can access their reviews"
        )

    return _get_review_display_rows(
        db,
        customer_id=current_user.id,
    )


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(
    review_id: int,
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

    return review


@router.get(
    "/provider/{provider_id}",
    response_model=list[ReviewDisplayResponse]
)
def get_provider_reviews(
    provider_id: int,
    db: Session = Depends(get_db)
):
    return _get_review_display_rows(
        db,
        provider_id=provider_id,
    )


@router.get("/provider/{provider_id}/rating")
def get_provider_rating(
    provider_id: int,
    db: Session = Depends(get_db)
):
    rating_counts = db.query(
        Review.rating,
        func.count(Review.id),
    ).join(
        Booking,
        Booking.id == Review.booking_id,
    ).join(
        Service,
        (Service.id == Booking.service_id)
        & (Service.provider_id == Booking.provider_id),
    ).filter(
        Review.provider_id == provider_id,
        Review.customer_id == Booking.customer_id,
        Review.provider_id == Booking.provider_id,
        Booking.status == "completed",
    ).group_by(
        Review.rating
    ).all()

    distribution = {
        rating: 0
        for rating in range(5, 0, -1)
    }
    for rating, count in rating_counts:
        distribution[rating] = count

    total_reviews = sum(distribution.values())
    average_rating = (
        sum(rating * count for rating, count in distribution.items())
        / total_reviews
        if total_reviews
        else 0
    )

    return {
        "provider_id": provider_id,
        "average_rating": round(
            float(average_rating),
            2
        ),
        "total_reviews": total_reviews,
        "rating_distribution": [
            {"rating": rating, "count": count}
            for rating, count in distribution.items()
        ],
    }


@router.put("/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: int,
    data: ReviewUpdate,
    current_user: User = Depends(get_current_user),
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

    if current_user.role != "customer":
        raise HTTPException(
            status_code=403,
            detail="Only customers can update reviews"
        )

    if review.customer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own review"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for field in ("title", "comment"):
        if field in update_data and update_data[field] is not None:
            update_data[field] = update_data[field].strip() or None

    if "comment" in update_data and update_data["comment"] is None:
        raise HTTPException(
            status_code=400,
            detail="Review text cannot be blank",
        )

    for field, value in update_data.items():
        setattr(review, field, value)

    db.commit()
    db.refresh(review)

    return review


@router.delete("/{review_id}")
def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
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

    if current_user.role != "admin" and (
        current_user.role != "customer"
        or review.customer_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own review"
        )

    db.delete(review)
    db.commit()

    return {
        "message": "Review deleted successfully"
    }
