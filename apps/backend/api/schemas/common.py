"""
Common schemas shared across API endpoints.
"""

from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SortOrder(str, Enum):
    """Sort order enumeration."""

    asc = "asc"
    desc = "desc"


class MovieSortBy(str, Enum):
    """Movie sort field options."""

    popularity = "popularity"
    release_date = "release_date"
    vote_average = "vote_average"
    title = "title"
    revenue = "revenue"


class PeopleSortBy(str, Enum):
    """People sort field options."""

    name = "name"
    popularity = "popularity"


class CreditType(str, Enum):
    """Credit type enumeration."""

    cast = "cast"
    crew = "crew"


class TimeWindow(str, Enum):
    """Time window for trending."""

    day = "day"
    week = "week"
    month = "month"


class SearchIn(str, Enum):
    """Search location options."""

    title = "title"
    overview = "overview"
    both = "both"


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total items across all pages")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    data: List[T]
    pagination: PaginationMeta


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class SuccessResponse(BaseModel):
    """Standard success response."""

    success: bool = True
    message: str


class SpokenLanguage(BaseModel):
    """Spoken language information."""

    code: str
    name: str
