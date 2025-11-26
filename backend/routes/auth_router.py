from __future__ import annotations

from typing import Annotated
import logging
import uuid

from backend.config import settings

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.sql_app import models, schemas
from backend.sql_app.database import get_db

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

    # Verify password against stored hash
    password_ok = security.verify_password(
        form_data.password, user.hashed_password
    )  # nosec

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


@router.get("/me", response_model=schemas.UserRead)
async def read_users_me(
    current_user: Annotated[models.User, Depends(security.get_current_active_user)],
) -> schemas.UserRead:
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

    return schemas.UserRead(
        id=str(getattr(current_user, "id", "")),
        email=getattr(current_user, "email", ""),
        is_active=bool(getattr(current_user, "is_active", False)),
        is_superuser=bool(getattr(current_user, "is_superuser", False)),
        role=role_param,
    )
