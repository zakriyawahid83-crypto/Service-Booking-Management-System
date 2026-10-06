from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


@router.post(
    "/",
    response_model=PaymentResponse
)
def create_payment(
    data: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(
        Booking.id == data.booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if current_user.role == "customer":
        if booking.customer_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only pay for your own booking"
            )

    elif current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    if booking.status == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="Cancelled booking cannot be paid"
        )

    existing_payment = db.query(Payment).filter(
        Payment.booking_id == booking.id
    ).first()

    if existing_payment:
        raise HTTPException(
            status_code=400,
            detail="Payment already exists for this booking"
        )

    payment = Payment(
        booking_id=booking.id,
        amount=booking.price,
        status="pending",
        payment_method=data.payment_method,
        transaction_id=f"MOCK-{uuid4().hex[:12].upper()}"
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment


@router.get(
    "/my",
    response_model=list[PaymentResponse]
)
def get_my_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=403,
            detail="Only customers can access their payments"
        )

    return (
        db.query(Payment)
        .join(
            Booking,
            Payment.booking_id == Booking.id
        )
        .filter(
            Booking.customer_id == current_user.id
        )
        .order_by(
            Payment.created_at.desc()
        )
        .all()
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse
)
def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    booking = db.query(Booking).filter(
        Booking.id == payment.booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if current_user.role == "customer":
        if booking.customer_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

    elif current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    return payment


@router.post(
    "/{payment_id}/pay",
    response_model=PaymentResponse
)
def pay_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    booking = db.query(Booking).filter(
        Booking.id == payment.booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if current_user.role == "customer":
        if booking.customer_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only pay for your own booking"
            )

    elif current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    if payment.status == "paid":
        raise HTTPException(
            status_code=400,
            detail="Payment is already paid"
        )

    if payment.status == "refunded":
        raise HTTPException(
            status_code=400,
            detail="Refunded payment cannot be paid again"
        )

    payment.status = "paid"

    if not payment.transaction_id:
        payment.transaction_id = (
            f"MOCK-{uuid4().hex[:12].upper()}"
        )

    db.commit()
    db.refresh(payment)

    return payment


@router.post(
    "/{payment_id}/refund",
    response_model=PaymentResponse
)
def refund_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    booking = db.query(Booking).filter(
        Booking.id == payment.booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if current_user.role == "customer":
        if booking.customer_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only refund your own payment"
            )

    elif current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    if payment.status != "paid":
        raise HTTPException(
            status_code=400,
            detail="Only paid payments can be refunded"
        )

    payment.status = "refunded"

    db.commit()
    db.refresh(payment)

    return payment
