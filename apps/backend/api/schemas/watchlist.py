"""
Watchlist-related Pydantic schemas.
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WatchlistAdd(BaseModel):
    """Request to add movie to watchlist."""

    movie_id: int = Field(..., description="Movie ID to add")


class WatchlistMovie(BaseModel):
    """Movie in watchlist with details."""

    id: int
    title: str
    poster_path: Optional[str] = None
    vote_average: Optional[float] = None
    release_date: Optional[date] = None
    overview: Optional[str] = None
    added_at: Optional[datetime] = None


class WatchlistResponse(BaseModel):
    """Response containing user's watchlist."""

    data: List[WatchlistMovie] = []
    total: int = 0


class NotInterestedAdd(BaseModel):
    """Request to mark movie as not interested."""

    movie_id: int = Field(..., description="Movie ID to mark")
