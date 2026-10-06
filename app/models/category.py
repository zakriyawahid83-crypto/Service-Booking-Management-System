from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(100),
        unique=True,
        nullable=False
    )

    description = Column(
        String(255),
        nullable=True
    )

    provider_id = Column(
        Integer,
        ForeignKey("providers.id"),
        nullable=True
    )

    # =====================================================
    # PROVIDER
    # =====================================================

    provider = relationship(
        "Provider",
        back_populates="categories"
    )

    # =====================================================
    # SERVICES
    # =====================================================

    services = relationship(
        "Service",
        back_populates="category"
    )
