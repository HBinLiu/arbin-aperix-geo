"""FastAPI dependencies: DB session, current user, tenant scope."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject, User
from aperix_geo.db.session import get_db
from aperix_geo.security.jwt import decode_token, parse_user_tenant_ids
from aperix_geo.services.subject.loader import load_subject_with_competitors

security = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id, _tenant_id = parse_user_tenant_ids(payload)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from e
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_tenant_match(user: User, tenant_id: UUID) -> None:
    if user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")


def get_subject_for_user(
    db: Session,
    user: User,
    subject_id: UUID,
    *,
    with_competitors: bool = False,
) -> Subject:
    """Load subject scoped to the user's tenant; 404 if missing or wrong tenant."""
    if with_competitors:
        subject = load_subject_with_competitors(db, subject_id, tenant_id=user.tenant_id)
    else:
        subject = db.get(Subject, subject_id)
        if subject is not None and subject.tenant_id != user.tenant_id:
            subject = None
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject
