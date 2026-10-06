from pydantic import BaseModel


# =========================================================
# CREATE / UPDATE CATEGORY
# =========================================================

class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


# =========================================================
# CATEGORY RESPONSE
# =========================================================

class CategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None
    provider_id: int | None

    class Config:
        from_attributes = True
