from datetime import date, datetime, time

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    booking_id: int
    rating: int = Field(..., ge=1, le=5)
    title: str | None = Field(default=None, max_length=120)
    comment: str = Field(..., min_length=1, max_length=2000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    title: str | None = Field(default=None, max_length=120)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    id: int
    booking_id: int
    customer_id: int
    provider_id: int
    rating: int
    title: str | None = None
    comment: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewDisplayResponse(ReviewResponse):
    customer_name: str
    service_name: str
    provider_name: str
    verified_booking: bool = False
    booking_date: date | None = None
    booking_start_time: time | None = None
    booking_end_time: time | None = None
    booking_price: float | None = None
    booking_status: str | None = None