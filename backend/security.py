from __future__ import annotations

import base64
import contextlib
import datetime as dt
import hashlib
import hmac
import json
import secrets
from collections.abc import Sequence
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.sql_app import models, schemas
from backend.sql_app.database import get_db
from contextlib import suppress

# In-memory user cache used when the app is running with IN_MEMORY_DB for local/dev
_in_memory_users: dict[str, models.User] = {}


def add_in_memory_user(user: models.User) -> None:
    # Dev-only in-memory cache. Ignore weird collisions/tests.
    with suppress(Exception):
        _in_memory_users[user.email] = user


def find_in_memory_user_by_email(email: str) -> models.User | None:
    return _in_memory_users.get(email)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class JWTError(Exception):
    """Minimal JWT error wrapper to keep compatibility with jose.JWTError."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _jwt_encode(payload: dict[str, Any], secret: str) -> str:
    header = {"alg": ALGORITHM, "typ": "JWT"}
    header_segment = _b64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    payload_segment = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_segment = _b64url_encode(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def _jwt_decode(token: str, secret: str) -> dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:  # pragma: no cover - malformed token path
        raise JWTError("Invalid token format") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()

    try:
        actual = _b64url_decode(signature_segment)
    except Exception as exc:  # pragma: no cover - malformed base64
        raise JWTError("Invalid signature encoding") from exc

    if not hmac.compare_digest(expected, actual):
        raise JWTError("Invalid signature")

    try:
        payload_json = _b64url_decode(payload_segment)
        payload: dict[str, Any] = json.loads(payload_json)
    except Exception as exc:  # pragma: no cover - invalid payload
        raise JWTError("Invalid payload") from exc

    exp = payload.get("exp")
    if exp is not None:
        exp_dt = dt.datetime.fromtimestamp(float(exp), tz=dt.UTC)
        if dt.datetime.now(dt.UTC) >= exp_dt:
            raise JWTError("Token has expired")
    return payload


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt_b64, hash_b64 = hashed_password.split(":")
    except ValueError:
        return False
    salt = _b64url_decode(salt_b64)
    stored_hash = _b64url_decode(hash_b64)
    new_hash = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode("utf-8"), salt, 200_000
    )
    return hmac.compare_digest(stored_hash, new_hash)


def get_password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"{_b64url_encode(salt)}:{_b64url_encode(hashed)}"


def create_access_token(
    data: dict[str, Any], expires_delta: dt.timedelta | None = None
) -> str:
    to_encode = data.copy()
    expire = dt.datetime.now(dt.UTC) + (
        expires_delta
        if expires_delta is not None
        else dt.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire.timestamp()})
    return _jwt_encode(to_encode, settings.app_secret_key)


async def get_user_by_email(db: AsyncSession, email: str) -> models.User | None:
    stmt = select(models.User).where(models.User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    # If running in IN_MEMORY_DB mode, allow fallback to the in-memory user cache
    in_memory_enabled = False
    with contextlib.suppress(Exception):
        in_memory_enabled = bool(getattr(settings, "IN_MEMORY_DB", False))
    if user is None and in_memory_enabled:
        return find_in_memory_user_by_email(email)
    return user


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> models.User | None:
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = _jwt_decode(token, settings.app_secret_key)
        user_id: str | None = payload.get("sub")
        email: str | None = payload.get("email")
        if user_id is None:
            raise credentials_exception
        token_data = schemas.TokenData(user_id=user_id, email=email)
    except JWTError:
        raise credentials_exception from None

    stmt = select(models.User).where(models.User.id == token_data.user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if user is None:
        # If running in in-memory mode allow fallback to the in-memory cache by email
        in_memory_enabled = False
        with contextlib.suppress(Exception):
            in_memory_enabled = bool(getattr(settings, "IN_MEMORY_DB", False))
        if in_memory_enabled and token_data.email:
            user = find_in_memory_user_by_email(token_data.email)
        if user is None:
            raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[models.User, Depends(get_current_user)],
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


def require_roles(allowed_roles: Sequence[str]):
    allowed = {getattr(role, "value", role) for role in allowed_roles}

    async def _checker(
        current_user: Annotated[models.User, Depends(get_current_active_user)],
    ) -> models.User:
        role_value = getattr(current_user.role, "value", current_user.role)
        if role_value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role"
            )
        return current_user

    return _checker


coach_or_org_required = Depends(require_roles(["coach_pro", "org_pro"]))
analyst_or_org_required = Depends(require_roles(["analyst_pro", "org_pro"]))
org_only_required = Depends(require_roles(["org_pro"]))
