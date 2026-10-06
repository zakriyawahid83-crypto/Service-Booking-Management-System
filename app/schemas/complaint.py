from datetime import datetime

from pydantic import BaseModel


class ComplaintCreate(BaseModel):
    provider_id: int | None = None
    booking_id: int | None = None
    subject: str
    description: str


class ComplaintStatusUpdate(BaseModel):
    status: str
    admin_response: str | None = None


class ComplaintResponse(BaseModel):
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

    class Config:
        from_attributes = True
