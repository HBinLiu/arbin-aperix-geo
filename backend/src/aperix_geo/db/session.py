"""Database session factory."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from aperix_geo.config import get_settings
from aperix_geo.db.delete import SoftDeleteSession

_settings = get_settings()
engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    echo=False,
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=SoftDeleteSession,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
