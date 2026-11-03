from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import User
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None:
        raise HTTPException(401, 'Authentication required.', headers={'WWW-Authenticate': 'Bearer'})
    try:
        user_id = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(401, 'Invalid or expired access token.', headers={'WWW-Authenticate': 'Bearer'}) from exc
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(401, 'User account is unavailable.')
        session.expunge(user)
        return user