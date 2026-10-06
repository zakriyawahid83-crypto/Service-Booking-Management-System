from datetime import date, datetime, time

from pydantic import BaseModel


class ProviderDashboardResponse(BaseModel):
    total_services: int
    active_services: int
    total_bookings: int
    pending_bookings: int
    confirmed_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    no_show_bookings: int
    total_customers: int
    total_reviews: int
    average_rating: float
    total_earnings: float


class ProviderServiceCreate(BaseModel):
    category_id: int
    name: str
    description: str | None = None
    price: float
    duration_minutes: int
    image_url: str | None = None
    is_active: bool = True


class ProviderServiceUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = None
    description: str | None = None
    price: float | None = None
    duration_minutes: int | None = None
    image_url: str | None = None
    is_active: bool | None = None


class ProviderServiceResponse(BaseModel):
    id: int
    provider_id: int
    category_id: int
    name: str
    description: str | None
    price: float
    duration_minutes: int
    image_url: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class ProviderBookingResponse(BaseModel):
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
    customer_name: str
    customer_email: str
    service_name: str

    class Config:
        from_attributes = True


class ProviderBookingStatusUpdate(BaseModel):
    status: str


class ProviderCustomerResponse(BaseModel):
    customer_id: int
    customer_name: str
    customer_email: str
    total_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    total_spent: float


class ProviderEarningItemResponse(BaseModel):
    booking_id: int
    customer_id: int
    customer_name: str
    service_id: int
    service_name: str
    duration_minutes: int
    booking_date: date
    start_time: time
    end_time: time
    booking_status: str
    price: float
    payment_id: int | None = None
    payment_amount: float | None = None
    payment_status: str | None = None
    transaction_id: str | None = None


class ProviderEarningsResponse(BaseModel):
    total_earnings: float
    completed_bookings: int
    average_booking_value: float
    booking_count: int = 0
    completed_revenue: float = 0
    pending_revenue: float = 0
    refunded_revenue: float = 0
    earnings: list[ProviderEarningItemResponse]


class ProviderProfileResponse(BaseModel):
    id: int
    user_id: int
    business_name: str
    description: str | None
    location: str | None
    phone: str | None
    is_verified: bool

    class Config:
        from_attributes = True


class ProviderProfileUpdate(BaseModel):
    business_name: str | None = None
    description: str | None = None
    location: str | None = None
    phone: str | None = None
