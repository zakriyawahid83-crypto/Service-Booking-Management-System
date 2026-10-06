from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import Category
from app.models.provider import Provider
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse
from app.utils.auth import require_role


router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)


# =========================================================
# CURRENT PROVIDER
# =========================================================

def _get_current_provider(
    current_user: User,
    db: Session,
) -> Provider:

    provider = (
        db.query(Provider)
        .filter(
            Provider.user_id == current_user.id
        )
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider profile not found",
        )

    return provider


# =========================================================
# CREATE CATEGORY
# =========================================================

@router.post(
    "/",
    response_model=CategoryResponse,
)
def create_category(
    category: CategoryCreate,
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db),
):

    # -----------------------------------------------------
    # Get logged-in provider
    # -----------------------------------------------------

    provider = _get_current_provider(
        current_user,
        db,
    )

    # -----------------------------------------------------
    # Check duplicate category inside same shop
    # -----------------------------------------------------

    existing_category = (
        db.query(Category)
        .filter(
            Category.name == category.name,
            Category.provider_id == provider.id,
        )
        .first()
    )

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This category already exists in your shop",
        )

    # -----------------------------------------------------
    # Create category
    # -----------------------------------------------------

    new_category = Category(
        name=category.name,
        description=category.description,
        provider_id=provider.id,
    )

    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    return new_category


# =========================================================
# GET ALL CATEGORIES
# =========================================================

@router.get(
    "/",
    response_model=list[CategoryResponse],
)
def get_categories(
    db: Session = Depends(get_db),
):

    return (
        db.query(Category)
        .order_by(Category.id)
        .all()
    )


# =========================================================
# GET MY CATEGORIES
# =========================================================

@router.get(
    "/my",
    response_model=list[CategoryResponse],
)
def get_my_categories(
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db),
):

    provider = _get_current_provider(
        current_user,
        db,
    )

    return (
        db.query(Category)
        .filter(
            Category.provider_id == provider.id
        )
        .order_by(Category.id)
        .all()
    )


# =========================================================
# GET CATEGORY BY ID
# =========================================================

@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
):

    category = (
        db.query(Category)
        .filter(
            Category.id == category_id
        )
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return category


# =========================================================
# UPDATE MY CATEGORY
# =========================================================

@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
)
def update_category(
    category_id: int,
    category_data: CategoryCreate,
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db),
):

    provider = _get_current_provider(
        current_user,
        db,
    )

    # -----------------------------------------------------
    # Find category belonging to current provider
    # -----------------------------------------------------

    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.provider_id == provider.id,
        )
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # -----------------------------------------------------
    # Check duplicate name in same shop
    # -----------------------------------------------------

    duplicate = (
        db.query(Category)
        .filter(
            Category.name == category_data.name,
            Category.provider_id == provider.id,
            Category.id != category_id,
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This category already exists in your shop",
        )

    # -----------------------------------------------------
    # Update
    # -----------------------------------------------------

    category.name = category_data.name
    category.description = category_data.description

    db.commit()
    db.refresh(category)

    return category


# =========================================================
# DELETE MY CATEGORY
# =========================================================

@router.delete(
    "/{category_id}",
)
def delete_category(
    category_id: int,
    current_user: User = Depends(
        require_role("provider")
    ),
    db: Session = Depends(get_db),
):

    provider = _get_current_provider(
        current_user,
        db,
    )

    # -----------------------------------------------------
    # Find category belonging to current provider
    # -----------------------------------------------------

    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.provider_id == provider.id,
        )
        .first()
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # -----------------------------------------------------
    # Check whether services use this category
    # -----------------------------------------------------

    if category.services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category because services are using it",
        )

    db.delete(category)
    db.commit()

    return {
        "message": "Category deleted successfully"
    }
