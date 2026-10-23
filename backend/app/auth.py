from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User

passwords = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def create_token(user: User):
    settings = get_settings()
    return jwt.encode(
        {
            "sub": user.id,
            "exp": datetime.now(UTC) + timedelta(minutes=settings.token_minutes),
            "iss": "insightai",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    denied = HTTPException(401, "Please sign in", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise denied
    try:
        payload = jwt.decode(
            credentials.credentials,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            issuer="insightai",
            options={"require": ["sub", "exp", "iss"]},
        )
        user = db.get(User, payload["sub"])
    except (jwt.PyJWTError, KeyError):
        raise denied from None
    if user is None:
        raise denied
    return user
