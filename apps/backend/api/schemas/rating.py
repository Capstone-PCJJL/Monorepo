"""
Rating-related Pydantic schemas.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class RatingAdd(BaseModel):
    """Request to add a movie rating."""

    movie_id: int = Field(..., description="Movie ID to rate")
    rating: float = Field(..., ge=0, le=10, description="Rating value (0-10)")


class LikeAdd(BaseModel):
    """Request to like a movie."""

    movie_id: int = Field(..., description="Movie ID to like")


class RatingResponse(BaseModel):
    """Response for a rating."""

    id: int
    user_id: int
    movie_id: Optional[int] = None
    name: Optional[str] = None
    year: Optional[int] = None
    rating: float
    watched_date: Optional[date] = None


class LikeResponse(BaseModel):
    """Response for a like."""

    id: int
    user_id: int
    movie_id: Optional[int] = None
    name: Optional[str] = None
    year: Optional[int] = None
    date: Optional[date] = None


class RatingCreatedResponse(BaseModel):
    """Response after creating a rating."""

    success: bool = True
    id: int = Field(..., description="ID of the created rating")


class LikeCreatedResponse(BaseModel):
    """Response after creating a like."""

    success: bool = True
    id: int = Field(..., description="ID of the created like")
