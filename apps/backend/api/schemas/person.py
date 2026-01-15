"""
Person-related Pydantic schemas.
"""

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PersonSummary(BaseModel):
    """Minimal person information."""

    id: int
    name: str
    profile_path: Optional[str] = None


class PersonListItem(PersonSummary):
    """Person item for browse lists."""

    gender: Optional[int] = None
    known_for_department: Optional[str] = None
    movie_count: Optional[int] = None


class FilmographyItem(BaseModel):
    """Single item in a person's filmography."""

    movie_id: int
    title: str
    release_date: Optional[date] = None
    poster_path: Optional[str] = None
    vote_average: Optional[float] = None
    character: Optional[str] = None  # For cast
    job: Optional[str] = None  # For crew
    department: Optional[str] = None  # For crew
    credit_type: str = Field(..., description="'cast' or 'crew'")


class PersonStats(BaseModel):
    """Statistics about a person's filmography."""

    total_movies: int
    as_cast: int
    as_crew: int
    average_movie_rating: Optional[float] = None


class Filmography(BaseModel):
    """Grouped filmography."""

    cast: List[FilmographyItem] = []
    crew: List[FilmographyItem] = []


class PersonDetail(PersonListItem):
    """Complete person details with filmography."""

    filmography: Filmography
    stats: PersonStats


class PersonMoviesResponse(BaseModel):
    """Response for paginated person movies endpoint."""

    person_id: int
    person_name: str
    data: List[FilmographyItem]
    pagination: Dict
