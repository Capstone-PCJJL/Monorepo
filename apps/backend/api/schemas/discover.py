"""
Discovery-related Pydantic schemas.
"""

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel

from .movie import MovieListItem


class TrendingResponse(BaseModel):
    """Response for trending movies endpoint."""

    time_window: str
    data: List[MovieListItem]


class TopRatedResponse(BaseModel):
    """Response for top-rated movies endpoint."""

    min_votes: int
    data: List[MovieListItem]


class DateRange(BaseModel):
    """Date range for releases."""

    from_date: date
    to_date: date


class NewReleasesResponse(BaseModel):
    """Response for new releases endpoint."""

    date_range: DateRange
    data: List[MovieListItem]


class UpcomingResponse(BaseModel):
    """Response for upcoming movies endpoint."""

    date_range: DateRange
    data: List[MovieListItem]


class YearRange(BaseModel):
    """Year range for decade."""

    from_year: int
    to_year: int


class ByDecadeResponse(BaseModel):
    """Response for by-decade endpoint."""

    decade: str
    year_range: YearRange
    data: List[MovieListItem]
    pagination: Dict
