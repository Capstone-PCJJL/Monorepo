"""
Dependency injection for the API.

Provides dependencies for database access and configuration.
"""

from functools import lru_cache
from typing import Dict, List, TypeVar

from fastapi import HTTPException, status

from tmdb_pipeline.client import TMDBClient
from tmdb_pipeline.config import Config
from tmdb_pipeline.database import DatabaseManager

T = TypeVar("T")


@lru_cache()
def get_config() -> Config:
    """Get cached configuration instance."""
    return Config.from_env()


@lru_cache()
def get_db() -> DatabaseManager:
    """Get cached DatabaseManager instance."""
    config = get_config()
    return DatabaseManager(config)


@lru_cache()
def get_tmdb_client() -> TMDBClient:
    """Get cached TMDBClient instance."""
    config = get_config()
    return TMDBClient(config)


def paginate(
    items: List[T],
    total: int,
    page: int,
    per_page: int,
) -> Dict:
    """
    Create a paginated response structure.

    Args:
        items: List of items for current page
        total: Total number of items across all pages
        page: Current page number
        per_page: Items per page

    Returns:
        Dictionary with data and pagination metadata
    """
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return {
        "data": items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


def validate_pagination(page: int, per_page: int, max_per_page: int = 100) -> None:
    """
    Validate pagination parameters.

    Args:
        page: Page number (must be >= 1)
        per_page: Items per page (must be >= 1 and <= max_per_page)
        max_per_page: Maximum allowed items per page

    Raises:
        HTTPException: If parameters are invalid
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be >= 1",
        )
    if per_page < 1 or per_page > max_per_page:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"per_page must be between 1 and {max_per_page}",
        )
