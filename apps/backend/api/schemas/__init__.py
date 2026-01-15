"""Pydantic schemas for API request and response validation."""

from api.schemas.common import (
    CreditType,
    ErrorResponse,
    MovieSortBy,
    PaginatedResponse,
    PaginationMeta,
    PeopleSortBy,
    SearchIn,
    SortOrder,
    SpokenLanguage,
    SuccessResponse,
    TimeWindow,
)
from api.schemas.movie import (
    CastMember,
    Credits,
    CreditsWithTotals,
    CrewMember,
    MovieDetail,
    MovieListItem,
    MovieSummary,
    PersonDetail,
    PersonSummary,
    SimilarMovie,
    SimilarMoviesResponse,
)
from api.schemas.person import (
    Filmography,
    FilmographyItem,
    PersonListItem,
    PersonMoviesResponse,
    PersonStats,
)
from api.schemas.genre import Genre, GenreListResponse
from api.schemas.search import (
    MovieSearchResponse,
    MovieSearchResults,
    PeopleSearchResponse,
    PeopleSearchResults,
    UnifiedSearchResponse,
)
from api.schemas.discover import (
    ByDecadeResponse,
    DateRange,
    NewReleasesResponse,
    TopRatedResponse,
    TrendingResponse,
    UpcomingResponse,
    YearRange,
)

__all__ = [
    # Common
    "CreditType",
    "ErrorResponse",
    "MovieSortBy",
    "PaginatedResponse",
    "PaginationMeta",
    "PeopleSortBy",
    "SearchIn",
    "SortOrder",
    "SpokenLanguage",
    "SuccessResponse",
    "TimeWindow",
    # Movie
    "CastMember",
    "Credits",
    "CreditsWithTotals",
    "CrewMember",
    "MovieDetail",
    "MovieListItem",
    "MovieSummary",
    "PersonDetail",
    "PersonSummary",
    "SimilarMovie",
    "SimilarMoviesResponse",
    # Person
    "Filmography",
    "FilmographyItem",
    "PersonListItem",
    "PersonMoviesResponse",
    "PersonStats",
    # Genre
    "Genre",
    "GenreListResponse",
    # Search
    "MovieSearchResponse",
    "MovieSearchResults",
    "PeopleSearchResponse",
    "PeopleSearchResults",
    "UnifiedSearchResponse",
    # Discover
    "ByDecadeResponse",
    "DateRange",
    "NewReleasesResponse",
    "TopRatedResponse",
    "TrendingResponse",
    "UpcomingResponse",
    "YearRange",
]
