from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Provider(Base):
    __tablename__ = "providers"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    business_name = Column(
        String(150),
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    location = Column(
        String(255),
        nullable=True
    )

    phone = Column(
        String(30),
        nullable=True
    )

    is_verified = Column(
        Boolean,
        default=False,
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="provider"
    )

    availabilities = relationship(
        "Availability",
        back_populates="provider",
        cascade="all, delete-orphan"
    )

    categories = relationship(
        "Category",
        back_populates="provider"
    )