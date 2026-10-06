from datetime import datetime

from pydantic import BaseModel


class PaymentCreate(BaseModel):
    booking_id: int
    payment_method: str = "mock"


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    amount: float
    status: str
    payment_method: str
    transaction_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True