from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    customer_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=True
    )

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id"),
        nullable=True
    )

    subject = Column(
        String(150),
        nullable=False
    )

    description = Column(
        Text,
        nullable=False
    )

    status = Column(
        String(20),
        nullable=False,
        default="open"
    )

    admin_response = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
