from pydantic import BaseModel


class CustomerProfileResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True


class CustomerProfileUpdate(BaseModel):
    name: str | None = None

class CustomerDashboardResponse(BaseModel):
    total_bookings: int
    pending_bookings: int
    confirmed_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    no_show_bookings: int
    total_spent: float
    total_reviews: int
    average_rating: float

