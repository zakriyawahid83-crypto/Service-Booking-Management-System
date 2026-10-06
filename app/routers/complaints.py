from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import Booking
from app.models.complaint import Complaint
from app.models.provider import Provider
from app.models.user import User
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintResponse,
    ComplaintStatusUpdate
)
from app.utils.auth import get_current_user
from app.utils.notifications import create_notification


router = APIRouter(
    prefix="/complaints",
    tags=["Complaints"]
)


@router.post(
    "/",
    response_model=ComplaintResponse
)
def create_complaint(
    data: ComplaintCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=403,
            detail="Only customers can create complaints"
        )

    if data.provider_id is not None:
        provider = db.query(Provider).filter(
            Provider.id == data.provider_id
        ).first()

        if not provider:
            raise HTTPException(
                status_code=404,
                detail="Provider not found"
            )

    if data.booking_id is not None:
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
                detail="You can only complain about your own booking"
            )

        if data.provider_id is not None:
            if booking.provider_id != data.provider_id:
                raise HTTPException(
                    status_code=400,
                    detail="Provider does not match the booking"
                )

    complaint = Complaint(
        customer_id=current_user.id,
        provider_id=data.provider_id,
        booking_id=data.booking_id,
        subject=data.subject,
        description=data.description,
        status="open"
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    if complaint.provider_id:
        provider = db.query(Provider).filter(
            Provider.id == complaint.provider_id
        ).first()

        if provider:
            create_notification(
                db=db,
                user_id=provider.user_id,
                title="New Complaint",
                message=f"A new complaint #{complaint.id} has been submitted.",
                notification_type="new_complaint"
            )
            db.commit()

    return complaint


@router.get(
    "/my",
    response_model=list[ComplaintResponse]
)
def get_my_complaints(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=403,
            detail="Only customers can access their complaints"
        )

    return (
        db.query(Complaint)
        .filter(
            Complaint.customer_id == current_user.id
        )
        .order_by(
            Complaint.created_at.desc()
        )
        .all()
    )


@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse
)
def get_complaint(
    complaint_id: int,
    current_user: User = Depends(get_current_user),
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

    if current_user.role == "customer":
        if complaint.customer_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only access your own complaints"
            )

    elif current_user.role == "provider":
        provider = db.query(Provider).filter(
            Provider.user_id == current_user.id
        ).first()

        if not provider or complaint.provider_id != provider.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

    elif current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    return complaint


@router.get(
    "/",
    response_model=list[ComplaintResponse]
)
def get_all_complaints(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can access all complaints"
        )

    return (
        db.query(Complaint)
        .order_by(
            Complaint.created_at.desc()
        )
        .all()
    )


@router.patch(
    "/{complaint_id}/status",
    response_model=ComplaintResponse
)
def update_complaint_status(
    complaint_id: int,
    data: ComplaintStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can update complaints"
        )

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
        "closed",
        "rejected"
    ]

    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid complaint status"
        )

    complaint.status = data.status

    if data.admin_response is not None:
        complaint.admin_response = data.admin_response

    db.commit()
    db.refresh(complaint)

    create_notification(
        db=db,
        user_id=complaint.customer_id,
        title="Complaint Updated",
        message=f"Your complaint #{complaint.id} status is now {complaint.status}.",
        notification_type="complaint_updated"
    )

    db.commit()

    return complaint
