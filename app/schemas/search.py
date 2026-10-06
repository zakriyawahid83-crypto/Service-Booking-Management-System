from datetime import date

from pydantic import BaseModel


class SearchServiceResponse(BaseModel):
    service_id: int
    service_name: str
    description: str | None
    price: float
    duration_minutes: int

    provider_id: int
    provider_name: str
    provider_location: str | None

    category_id: int | None
    category_name: str | None

    average_rating: float
    total_reviews: int

    available_slots: list[dict[str, str]] | None = None
