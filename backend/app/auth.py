from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from fastapi import Cookie, HTTPException, Response, status

from . import config

_serializer = URLSafeTimedSerializer(config.SESSION_SECRET, salt="admin-session")


def create_session_cookie(response: Response) -> None:
    token = _serializer.dumps({"role": "admin"})

    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="none" if config.COOKIE_SECURE else "lax",
        max_age=config.SESSION_MAX_AGE_SECONDS,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(config.SESSION_COOKIE_NAME, path="/")


def require_admin(
    session: str | None = Cookie(default=None, alias=config.SESSION_COOKIE_NAME)
) -> None:
    if session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")

    try:
        _serializer.loads(session, max_age=config.SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
