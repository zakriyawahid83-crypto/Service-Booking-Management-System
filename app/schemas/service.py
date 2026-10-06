from pydantic import BaseModel, Field


class ServiceCreate(BaseModel):
    provider_id: int
    category_id: int
    name: str
    description: str | None = None
    price: float = Field(gt=0)
    duration_minutes: int = Field(gt=0)
    image_url: str | None = None


class ServiceResponse(BaseModel):
    id: int
    provider_id: int
    category_id: int
    name: str
    description: str | None
    price: float
    duration_minutes: int
    image_url: str | None = None
    is_active: bool
    provider_name: str | None = None
    provider_location: str | None = None

    class Config:
        from_attributes = True


class ServiceDetailResponse(BaseModel):
    id: int
    provider_id: int
    category_id: int
    name: str
    description: str | None
    price: float
    duration_minutes: int
    image_url: str | None = None
    is_active: bool

    business_name: str
    provider_description: str | None
    location: str | None
    phone: str | None
    is_verified: bool

    average_rating: float
    total_reviews: int