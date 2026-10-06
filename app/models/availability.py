from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Availability(Base):
    __tablename__ = "availabilities"

    id = Column(Integer, primary_key=True, index=True)

    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=False
    )

    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    break_start = Column(Time, nullable=True)
    break_end = Column(Time, nullable=True)

    slot_duration = Column(Integer, nullable=False, default=30)

    is_available = Column(Boolean, nullable=False, default=True)

    provider = relationship(
        "Provider",
        back_populates="availabilities"
    )


class ProviderBlockedDate(Base):
    __tablename__ = "provider_blocked_dates"
    __table_args__ = (
        UniqueConstraint("provider_id", "blocked_date", name="uq_provider_blocked_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    blocked_date = Column(Date, nullable=False)
    reason = Column(String(255), nullable=True)


class ProviderBlockedTime(Base):
    __tablename__ = "provider_blocked_times"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False, index=True)
    blocked_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    reason = Column(String(255), nullable=True)