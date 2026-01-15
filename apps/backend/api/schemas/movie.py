"""
Movie-related Pydantic schemas.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class PersonSummary(BaseModel):
    """Minimal person information."""

    id: int
    name: str
    profile_path: Optional[str] = None


class PersonDetail(PersonSummary):
    """Person with additional details."""

    gender: Optional[int] = None
    known_for_department: Optional[str] = None


class CastMember(PersonDetail):
    """Cast member with character information."""

    character: Optional[str] = None
    order: int = 0


class CrewMember(PersonDetail):
    """Crew member with job information."""

    job: str
    department: str


class Credits(BaseModel):
    """Movie credits with cast and crew."""

    cast: List[CastMember] = []
    crew: List[CrewMember] = []


class CreditsWithTotals(BaseModel):
    """Credits response with total counts."""

    movie_id: int
    cast: List[CastMember] = []
    cast_total: int = Field(..., description="Total cast members available")
    crew: List[CrewMember] = []
    crew_total: int = Field(..., description="Total crew members available")
    director: Optional[PersonSummary] = None


class MovieSummary(BaseModel):
    """Minimal movie information for lists."""

    id: int
    title: str
    poster_path: Optional[str] = None
    vote_average: Optional[float] = None
    release_date: Optional[date] = None
    genres: List[str] = []


class MovieListItem(MovieSummary):
    """Movie item for browse/search lists."""

    original_title: Optional[str] = None
    overview: Optional[str] = None
    vote_count: Optional[int] = None
    popularity: Optional[float] = None
    backdrop_path: Optional[str] = None
    runtime: Optional[int] = None


class MovieDetail(MovieListItem):
    """Complete movie details."""

    tagline: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[int] = None
    revenue: Optional[int] = None
    imdb_id: Optional[str] = None
    original_language: Optional[str] = None
    origin_country: List[str] = []
    spoken_languages: List[dict] = []  # [{"code": "en", "name": "English"}]
    credits: Credits


class SimilarMovie(MovieSummary):
    """Similar movie with relevance score."""

    similarity_score: Optional[float] = None


class SimilarMoviesResponse(BaseModel):
    """Response for similar movies endpoint."""

    movie_id: int
    similar: List[SimilarMovie]
