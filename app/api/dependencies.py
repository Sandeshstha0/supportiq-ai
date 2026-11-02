import os
import secrets

from dotenv import load_dotenv
from fastapi import Header, HTTPException, status
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.staff import StaffUserDB
from app.services.auth_service import decode_access_token

load_dotenv()


def verify_admin_api_key(
    x_admin_api_key: str | None = Header(default=None),
) -> None:
    expected_key = os.getenv("SUPPORTIQ_ADMIN_API_KEY")

    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication is not configured.",
        )

    if not x_admin_api_key or not secrets.compare_digest(
        x_admin_api_key,
        expected_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> StaffUserDB:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user_id = int(user_id)

    except Exception:
        raise credentials_exception

    user = db.get(StaffUserDB, user_id)

    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_admin(
    current_user: StaffUserDB = Depends(get_current_user),
) -> StaffUserDB:

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )

    return current_user