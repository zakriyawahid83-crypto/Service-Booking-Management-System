from datetime import date, datetime, time

from pydantic import BaseModel, Field, field_validator


class BookingCreate(BaseModel):
    service_id: int
    booking_date: date
    start_time: time
    customer_notes: str | None = None
    service_address: str = Field(min_length=5, max_length=500)

    # Retained for compatibility with older clients; the server ignores these.
    provider_id: int | None = None
    end_time: time | None = None
    price: float | None = Field(default=None, gt=0)

    @field_validator("service_address")
    @classmethod
    def validate_service_address(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Enter a complete service address")
        return value


class BookingReschedule(BaseModel):
    booking_date: date
    start_time: time
    end_time: time


class BookingResponse(BaseModel):
    id: int
    customer_id: int
    provider_id: int
    service_id: int
    booking_date: date
    start_time: time
    end_time: time
    price: float
    status: str
    customer_notes: str | None
    service_address: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProviderBookingResponse(BaseModel):
    id: int
    customer_id: int
    provider_id: int
    service_id: int

    customer_name: str
    service_name: str

    booking_date: date
    start_time: time
    end_time: time
    price: float
    status: str
    customer_notes: str | None
    service_address: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerBookingResponse(BaseModel):
    id: int
    customer_id: int
    provider_id: int
    service_id: int
    booking_date: date
    start_time: time
    end_time: time
    price: float
    status: str
    customer_notes: str | None
    created_at: datetime

    service_name: str
    business_name: str
    provider_location: str | None
    provider_phone: str | None
    service_address: str | None = None

    class Config:
        from_attributes = True