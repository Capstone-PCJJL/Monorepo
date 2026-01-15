"""
Search-related Pydantic schemas.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel

from api.schemas.movie import MovieListItem
from api.schemas.person import PersonListItem


class MovieSearchResults(BaseModel):
    """Movie search results section."""

    data: List[MovieListItem]
    total: int
    returned: int


class PeopleSearchResults(BaseModel):
    """People search results section."""

    data: List[PersonListItem]
    total: int
    returned: int


class UnifiedSearchResponse(BaseModel):
    """Response for unified search endpoint."""

    query: str
    movies: MovieSearchResults
    people: PeopleSearchResults


class MovieSearchResponse(BaseModel):
    """Response for movie search endpoint."""

    query: str
    filters: Optional[Dict] = None
    data: List[MovieListItem]
    pagination: Dict


class PeopleSearchResponse(BaseModel):
    """Response for people search endpoint."""

    query: str
    data: List[PersonListItem]
    pagination: Dict
