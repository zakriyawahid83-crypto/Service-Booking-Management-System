from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id"),
        nullable=False
    )

    amount = Column(
        Numeric(10, 2),
        nullable=False
    )

    status = Column(
        String(20),
        nullable=False,
        default="pending"
    )

    payment_method = Column(
        String(50),
        nullable=False,
        default="mock"
    )

    transaction_id = Column(
        String(100),
        nullable=True,
        unique=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )