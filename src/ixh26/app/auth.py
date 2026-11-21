"""Pseudonymous accounts (username + password, no personal data) with JWT sessions (D-003/5)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status

from ixh26 import config
from ixh26.store.repo import Store

COOKIE = "guardian_session"
USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
# shortcut: base58 shape only, no checksum; the worker rejects unknown accounts via the ledger
ADDRESS_RE = re.compile(r"^r[1-9A-HJ-NP-Za-km-z]{24,34}$")
TX_HASH_RE = re.compile(r"^[0-9A-Fa-f]{64}$")

_hasher = PasswordHasher()


@dataclass(frozen=True)
class CurrentUser:
    id: int
    username: str
    role: str

    @property
    def is_analyst(self) -> bool:
        return self.role == "analyst"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def validate_credentials(username: str, password: str) -> None:
    if not USERNAME_RE.fullmatch(username):
        raise HTTPException(422, "username: 3-32 letters, digits, '_' or '-'")
    if not 8 <= len(password) <= 128:
        raise HTTPException(422, "password: 8-128 characters")


def authenticate(store: Store, username: str, password: str) -> CurrentUser:
    user = store.user_by_name(username)
    try:
        if user is None:
            raise VerifyMismatchError
        _hasher.verify(user.password_hash, password)
    except VerifyMismatchError:
        raise HTTPException(401, "invalid username or password") from None
    return CurrentUser(user.id, user.username, user.role)


def issue_token(user: CurrentUser, settings: config.Settings) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user.id),
        "role": user.role,
        "network": settings.network.name,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_ttl_minutes),
    }
    return jwt.encode(claims, config.jwt_secret(), algorithm="HS256")


def get_store(request: Request) -> Store:
    return request.app.state.store


def get_settings(request: Request) -> config.Settings:
    return request.app.state.settings


def optional_user(
    request: Request, store: Annotated[Store, Depends(get_store)]
) -> CurrentUser | None:
    token = request.cookies.get(COOKIE)
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        token = header[7:]
    if not token:
        return None
    try:
        claims = jwt.decode(token, config.jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    # Pre-switch tokens were issued for the default Testnet deployment.
    if claims.get("network", "testnet") != get_settings(request).network.name:
        return None
    user = store.user(int(claims["sub"]))
    return CurrentUser(user.id, user.username, user.role) if user else None


def current_user(user: Annotated[CurrentUser | None, Depends(optional_user)]) -> CurrentUser:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "login required")
    return user


def analyst(user: Annotated[CurrentUser, Depends(current_user)]) -> CurrentUser:
    if not user.is_analyst:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "analyst role required")
    return user


StoreDep = Annotated[Store, Depends(get_store)]
SettingsDep = Annotated[config.Settings, Depends(get_settings)]
UserDep = Annotated[CurrentUser, Depends(current_user)]
AnalystDep = Annotated[CurrentUser, Depends(analyst)]
