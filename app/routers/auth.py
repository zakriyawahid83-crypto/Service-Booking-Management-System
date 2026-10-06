from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth_config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
)
from app.models.user import User
from app.models.provider import Provider
import os
import smtplib
from email.message import EmailMessage
from app.schemas.user import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


security = HTTPBearer(
    auto_error=False
)


# =========================================================
# REGISTER
# =========================================================

@router.post(
    "/register",
    response_model=UserResponse,
)
def register(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    # -----------------------------------------------------
    # CHECK EXISTING USER
    # -----------------------------------------------------

    existing_user = (
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # -----------------------------------------------------
    # HASH PASSWORD
    # -----------------------------------------------------

    hashed_password = bcrypt.hashpw(
        user.password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    # -----------------------------------------------------
    # CREATE USER
    # -----------------------------------------------------

    new_user = User(
        name=user.name,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role,
    )

    db.add(new_user)
    db.flush()

    # -----------------------------------------------------
    # CREATE PROVIDER PROFILE
    # -----------------------------------------------------
    # Every provider user must have a corresponding
    # Provider record because provider routes use:
    #
    # Provider.user_id == current_user.id
    #
    # business_name is required in the Provider model,
    # so initially we use the user's name.
    # The provider can update it later from the dashboard.

    if user.role == "provider":

        existing_provider = (
            db.query(Provider)
            .filter(
                Provider.user_id == new_user.id
            )
            .first()
        )

        if not existing_provider:

            provider = Provider(
                user_id=new_user.id,
                business_name=new_user.name,
                description=None,
                location=None,
                phone=None,
                is_verified=False,
            )

            db.add(provider)

    # -----------------------------------------------------
    # SAVE EVERYTHING
    # -----------------------------------------------------

    try:
        db.commit()
    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create account",
        )

    db.refresh(new_user)

    return new_user


# =========================================================
# LOGIN
# =========================================================

@router.post("/login")
def login(
    user: UserLogin,
    db: Session = Depends(get_db),
):
    db_user = (
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # -----------------------------------------------------
    # VERIFY PASSWORD
    # -----------------------------------------------------

    try:
        password_correct = bcrypt.checkpw(
            user.password.encode("utf-8"),
            db_user.hashed_password.encode("utf-8"),
        )
    except Exception:
        password_correct = False

    if not password_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # -----------------------------------------------------
    # CREATE JWT
    # -----------------------------------------------------

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    token_data = {
        "sub": str(db_user.id),
        "role": db_user.role,
        "exp": expire,
    }

    access_token = jwt.encode(
        token_data,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": db_user.id,
        "role": db_user.role,
    }


# =========================================================
# FORGOT PASSWORD
# =========================================================

@router.post("/forgot-password")
def forgot_password(
     email: str = Body(..., embed=True),
     db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == email.strip())
        .first()
    )

    # Do not reveal whether the email exists
    if not user:
        return {
            "message": "If this email exists, a password reset link has been sent."
        }

    # -----------------------------------------------------
    # CREATE RESET TOKEN
    # -----------------------------------------------------

    expire = (
        datetime.now(timezone.utc)
        + timedelta(minutes=30)
    )

    reset_token_data = {
        "sub": str(user.id),
        "purpose": "password_reset",
        "exp": expire,
    }

    reset_token = jwt.encode(
        reset_token_data,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    # -----------------------------------------------------
    # RESET URL
    # -----------------------------------------------------

    frontend_url = os.getenv(
        "FRONTEND_URL",
        "http://localhost:5173",
    ).rstrip("/")

    reset_url = (
        f"{frontend_url}/reset-password"
        f"?token={reset_token}"
    )

    # -----------------------------------------------------
    # EMAIL SETTINGS
    # -----------------------------------------------------

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(
        os.getenv("SMTP_PORT", "587")
    )
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all(
        [
            smtp_host,
            smtp_username,
            smtp_password,
        ]
    ):
        raise HTTPException(
            status_code=500,
            detail="Email service is not configured.",
        )

    # -----------------------------------------------------
    # SEND EMAIL
    # -----------------------------------------------------

    message = EmailMessage()

    message["Subject"] = "Service Booking - Password Reset"
    message["From"] = smtp_username
    message["To"] = user.email

    message.set_content(
        f"""
Hello {user.name},

We received a request to reset your Service Booking password.

Use this link to reset your password:

{reset_url}

This link will expire in 30 minutes.

If you did not request this, you can safely ignore this email.

Regards,
Service Booking Team
"""
    )

    try:
        with smtplib.SMTP(
            smtp_host,
            smtp_port,
            timeout=20,
        ) as server:

            server.ehlo()
            server.starttls()
            server.ehlo()

            server.login(
                smtp_username,
                smtp_password,
            )

            server.send_message(message)

    except Exception as exc:
        print(
            "Password reset email error:",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to send password reset email.",
        )

    return {
        "message": "If this email exists, a password reset link has been sent."
    }


# =========================================================
# RESET PASSWORD
# =========================================================

@router.post("/reset-password")
def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db),
):
    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters.",
        )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        if payload.get("purpose") != "password_reset":
            raise HTTPException(
                status_code=400,
                detail="Invalid password reset token.",
            )

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid password reset token.",
            )

    except JWTError:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired password reset token.",
        )

    user = (
        db.query(User)
        .filter(User.id == int(user_id))
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    user.hashed_password = bcrypt.hashpw(
        new_password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    db.commit()

    return {
        "message": "Password reset successfully."
    }


# =========================================================
# CURRENT USER
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        security
    ),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        if payload.get("exp") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: expiration missing",
                headers={
                    "WWW-Authenticate": "Bearer"
                },
            )

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: user ID missing",
                headers={
                    "WWW-Authenticate": "Bearer"
                },
            )

        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: invalid user ID",
                headers={
                    "WWW-Authenticate": "Bearer"
                },
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # -----------------------------------------------------
    # FIND USER
    # -----------------------------------------------------

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


# =========================================================
# CURRENT USER API
# =========================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: User = Depends(get_current_user),
):
    return current_user
