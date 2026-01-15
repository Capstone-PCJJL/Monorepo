"""
Genre-related Pydantic schemas.
"""

from typing import List

from pydantic import BaseModel


class Genre(BaseModel):
    """Genre with movie count."""

    name: str
    movie_count: int


class GenreListResponse(BaseModel):
    """Response for genres list endpoint."""

    data: List[Genre]
