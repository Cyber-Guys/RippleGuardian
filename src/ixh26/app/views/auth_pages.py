"""Sign in, register, sign out."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from ixh26.app import auth
from ixh26.app.auth import CurrentUser, SettingsDep, StoreDep
from ixh26.app.views.common import redirect, render

router = APIRouter(include_in_schema=False)


@router.get("/login")
def login_page(request: Request) -> HTMLResponse:
    return render(request, "login.html", None)


@router.post("/login")
def login_submit(
    request: Request,
    store: StoreDep,
    settings: SettingsDep,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> Response:
    try:
        user = auth.authenticate(store, username.strip(), password)
    except HTTPException as exc:
        return render(request, "login.html", None, 401, error=exc.detail, username=username)
    response = redirect("/")
    response.set_cookie(
        auth.COOKIE, auth.issue_token(user, settings), httponly=True, samesite="lax"
    )
    return response


@router.get("/register")
def register_page(request: Request) -> HTMLResponse:
    return render(request, "register.html", None)


@router.post("/register")
def register_submit(
    request: Request,
    store: StoreDep,
    settings: SettingsDep,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> Response:
    username = username.strip()
    try:
        auth.validate_credentials(username, password)
        if store.user_by_name(username):
            raise HTTPException(409, "That username is taken. Pick another one.")
    except HTTPException as exc:
        return render(request, "register.html", None, 422, error=exc.detail, username=username)
    row = store.create_user(username, auth.hash_password(password))
    response = redirect("/")
    user = CurrentUser(row.id, row.username, row.role)
    response.set_cookie(
        auth.COOKIE, auth.issue_token(user, settings), httponly=True, samesite="lax"
    )
    return response


@router.post("/logout")
def logout() -> Response:
    response = redirect("/login")
    response.delete_cookie(auth.COOKIE)
    return response
