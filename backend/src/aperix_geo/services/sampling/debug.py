"""Dev-only debug guard for manual sampling triggers."""

from fastapi import HTTPException, status

from aperix_geo.config import get_settings


def assert_sampling_debug_access(header: str | None) -> None:
    """Raise HTTPException when debug route is disabled or secret mismatches."""
    settings = get_settings()
    if not settings.sampling_debug_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not settings.sampling_debug_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sampling debug enabled but SAMPLING_DEBUG_SECRET is not set",
        )
    if header != settings.sampling_debug_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
