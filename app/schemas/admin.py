from datetime import date, datetime, time

from pydantic import BaseModel


class AdminUserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class AdminRoleUpdate(BaseModel):
    role: str


class AdminProviderResponse(BaseModel):
    id: int
    user_id: int
    business_name: str
    description: str | None
    location: str | None
    phone: str | None
    is_verified: bool
    user_name: str
    user_email: str

    class Config:
        from_attributes = True


class AdminProviderUpdate(BaseModel):
    business_name: str | None = None
    description: str | None = None
    location: str | None = None
    phone: str | None = None
    is_verified: bool | None = None


class AdminServiceResponse(BaseModel):
    id: int
    provider_id: int
    category_id: int
    name: str
    description: str | None
    price: float
    duration_minutes: int
    is_active: bool
    provider_name: str
    category_name: str

    class Config:
        from_attributes = True


class AdminServiceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    duration_minutes: int | None = None
    category_id: int | None = None
    is_active: bool | None = None


class AdminBookingResponse(BaseModel):
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
    provider_name: str
    service_name: str

    class Config:
        from_attributes = True


class AdminBookingStatusUpdate(BaseModel):
    status: str


class AdminReviewResponse(BaseModel):
    id: int
    booking_id: int
    customer_id: int
    provider_id: int
    rating: int
    comment: str | None
    created_at: datetime
    updated_at: datetime
    customer_name: str
    customer_email: str
    provider_name: str

    class Config:
        from_attributes = True


class AdminReviewUpdate(BaseModel):
    rating: int | None = None
    comment: str | None = None


class AdminComplaintResponse(BaseModel):
    id: int
    customer_id: int
    provider_id: int | None
    booking_id: int | None
    subject: str
    description: str
    status: str
    admin_response: str | None
    created_at: datetime
    updated_at: datetime
    customer_name: str
    customer_email: str
    provider_name: str | None

    class Config:
        from_attributes = True


class AdminComplaintUpdate(BaseModel):
    status: str | None = None
    admin_response: str | None = None


class AdminStatisticsResponse(BaseModel):
    total_users: int
    total_customers: int
    total_providers: int
    total_services: int
    total_bookings: int
    pending_bookings: int
    confirmed_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    no_show_bookings: int
    total_reviews: int
    average_rating: float
    total_complaints: int
    open_complaints: int
    in_progress_complaints: int
    resolved_complaints: int
    closed_complaints: int
    total_revenue: float
