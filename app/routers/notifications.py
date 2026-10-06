from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import Booking
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationReadUpdate
)
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)


@router.post(
    "/",
    response_model=NotificationResponse
)
def create_notification(
    notification: NotificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can create notifications"
        )

    user = db.query(User).filter(
        User.id == notification.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    new_notification = Notification(
        user_id=notification.user_id,
        title=notification.title,
        message=notification.message,
        notification_type=notification.notification_type,
        is_read=False
    )

    db.add(new_notification)
    db.commit()
    db.refresh(new_notification)

    return new_notification


@router.get(
    "/my",
    response_model=list[NotificationResponse]
)
def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).all()


@router.get(
    "/my/unread",
    response_model=list[NotificationResponse]
)
def get_my_unread_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False)
    ).order_by(
        Notification.created_at.desc()
    ).all()


@router.get(
    "/my/unread-count"
)
def get_my_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False)
    ).count()

    return {
        "unread_count": count
    }


@router.get(
    "/user/{user_id}",
    response_model=list[NotificationResponse]
)
def get_user_notifications(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only access your own notifications"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(
        Notification.created_at.desc()
    ).all()


@router.post(
    "/upcoming",
    response_model=list[NotificationResponse]
)
def create_upcoming_notifications(
    target_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can create upcoming notifications"
        )

    upcoming_bookings = db.query(Booking).filter(
        Booking.booking_date == target_date,
        Booking.status == "confirmed"
    ).all()

    created_notifications = []

    for booking in upcoming_bookings:
        existing_notification = db.query(Notification).filter(
            Notification.user_id == booking.customer_id,
            Notification.notification_type == "upcoming_appointment",
            Notification.message.like(
                f"%booking #{booking.id}%"
            )
        ).first()

        if existing_notification:
            continue

        notification = Notification(
            user_id=booking.customer_id,
            title="Upcoming Appointment",
            message=(
                f"Your booking #{booking.id} is scheduled "
                f"for {booking.booking_date} at "
                f"{booking.start_time}."
            ),
            notification_type="upcoming_appointment",
            is_read=False
        )

        db.add(notification)
        created_notifications.append(notification)

    db.commit()

    for notification in created_notifications:
        db.refresh(notification)

    return created_notifications


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse
)
def update_notification_read_status(
    notification_id: int,
    notification_status: NotificationReadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )

    if (
        notification.user_id != current_user.id
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only update your own notifications"
        )

    notification.is_read = notification_status.is_read

    db.commit()
    db.refresh(notification)

    return notification


@router.patch(
    "/read-all"
)
def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False)
    ).all()

    for notification in notifications:
        notification.is_read = True

    db.commit()

    return {
        "message": "All notifications marked as read",
        "updated_count": len(notifications)
    }


@router.delete(
    "/{notification_id}"
)
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )

    if (
        notification.user_id != current_user.id
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own notifications"
        )

    db.delete(notification)
    db.commit()

    return {
        "message": "Notification deleted successfully"
    }
