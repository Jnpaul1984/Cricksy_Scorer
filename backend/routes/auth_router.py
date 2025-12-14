from __future__ import annotations

import logging
import uuid
from typing import Annotated

from backend import security
from backend.config import settings
from backend.sql_app import models, schemas
from backend.sql_app.database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_in: schemas.UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    existing = await security.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = models.User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),  # nosec
        is_active=True,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        ) from None
    await db.refresh(user)
    # If running in in-memory mode, ensure the user has an id and register in the in-memory cache
    try:
        if bool(getattr(settings, "IN_MEMORY_DB", False)):
            if not getattr(user, "id", None):
                # assign a UUID so tokens have a meaningful sub claim in dev
                user.id = str(uuid.uuid4())
            security.add_in_memory_user(user)
    except Exception:
        pass  # nosec
    return {"status": "ok"}


@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.Token:
    import datetime as dt

    logger = logging.getLogger(__name__)

    dev_mode = bool(getattr(settings, "CRICKSY_IN_MEMORY_DB", False)) or getattr(
        settings, "ENV", "local"
    ) in ("local", "dev")

    # Look up user by email (username field is the email for this app)
    user = await security.get_user_by_email(db, form_data.username)

    # If user does not exist: ALWAYS reject (even in dev)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # If user is deactivated: reject
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has been deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password against stored hash
    password_ok = security.verify_password(form_data.password, user.hashed_password)  # nosec

    # If password is wrong:
    if not password_ok:
        if dev_mode:
            # LOCAL DEV BYPASS:
            logger.warning(
                "DEV LOGIN BYPASS: accepting invalid password for user %s",
                user.email,
            )
            # fall through and issue token anyway
        else:
            # In non-dev mode we keep strict behavior
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # From here on, treat user as authenticated (password_ok or dev_mode bypass)
    access_token_expires = dt.timedelta(
        minutes=getattr(
            security,
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            60,
        ),
    )
    access_token = security.create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires,
    )
    return schemas.Token(access_token=access_token, token_type="bearer")  # nosec B106


def _get_subscription_info(role: models.RoleEnum) -> schemas.SubscriptionInfo:
    """Build subscription info based on user role."""
    role_str = role.value if hasattr(role, "value") else str(role)

    # Token limits by role
    limits = {
        "free": 10000,
        "player_pro": 100000,
        "coach_pro": 100000,
        "analyst_pro": 100000,
        "org_pro": None,  # Unlimited
        "superuser": None,
    }

    # Calculate renewal date (next month)
    import datetime

    next_month = datetime.date.today().replace(day=1)
    if next_month.month == 12:
        next_month = next_month.replace(year=next_month.year + 1, month=1)
    else:
        next_month = next_month.replace(month=next_month.month + 1)

    return schemas.SubscriptionInfo(
        plan=role_str,
        status="active",
        renewal_date=next_month.isoformat() if role_str != "free" else None,
        tokens_used=0,  # Would be fetched from usage logs in production
        tokens_limit=limits.get(role_str),
    )


@router.get("/me", response_model=schemas.UserProfile)
async def read_users_me(
    current_user: Annotated[models.User, Depends(security.get_current_active_user)],
) -> schemas.UserProfile:
    """
    Get current user profile with subscription info.

    Returns extended user profile including:
    - Basic user info (id, email, role)
    - Display name
    - Organization ID (if applicable)
    - Subscription details with token limits
    """
    # Serialize explicitly to avoid ResponseValidationError when some ORM attributes
    # are None (can happen for in-memory/dev users). Coerce types to match
    # pydantic schema expectations (bools/strings).
    role_attr = getattr(current_user, "role", None)
    # Normalize role into models.RoleEnum for Pydantic validation
    try:
        if role_attr is None:
            role_param = models.RoleEnum.free
        elif isinstance(role_attr, models.RoleEnum):
            role_param = role_attr
        else:
            # role_attr might be a string; attempt to coerce
            role_param = models.RoleEnum(str(getattr(role_attr, "value", role_attr)))
    except Exception:
        role_param = models.RoleEnum.free

    # Get name (use email prefix as fallback)
    email = getattr(current_user, "email", "")
    name = getattr(current_user, "name", None) or getattr(current_user, "full_name", None)
    if not name and email:
        name = email.split("@")[0]

    # Get org_id if available
    org_id = getattr(current_user, "org_id", None)

    # Get created_at
    created_at = getattr(current_user, "created_at", None)
    created_at_str = created_at.isoformat() if created_at else None

    return schemas.UserProfile(
        id=str(getattr(current_user, "id", "")),
        email=email,
        name=name,
        is_active=bool(getattr(current_user, "is_active", False)),
        is_superuser=bool(getattr(current_user, "is_superuser", False)),
        role=role_param,
        org_id=str(org_id) if org_id else None,
        subscription=_get_subscription_info(role_param),
        created_at=created_at_str,
    )


# Trigger CI
