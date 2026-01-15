"""
Shared fixtures for TMDB backend tests.

Provides mock database, mock TMDB client, and sample data.
"""

import pytest
from datetime import date
from typing import Dict, List, Optional, Set, Tuple
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tmdb_pipeline.models import MovieData, CreditData, PersonData


# =============================================================================
# SAMPLE DATA
# =============================================================================

def create_sample_movie(
    movie_id: int,
    title: str,
    release_date: Optional[date] = None,
    genres: Optional[List[str]] = None,
    popularity: float = 50.0,
    vote_average: float = 7.5,
) -> MovieData:
    """Create a sample MovieData for testing."""
    return MovieData(
        id=movie_id,
        title=title,
        original_title=title,
        overview=f"This is the overview for {title}.",
        release_date=release_date or date(2023, 1, 15),
        runtime=120,
        status="Released",
        tagline=f"The tagline for {title}",
        vote_average=vote_average,
        vote_count=1000,
        popularity=popularity,
        poster_path=f"/poster_{movie_id}.jpg",
        backdrop_path=f"/backdrop_{movie_id}.jpg",
        budget=50000000,
        revenue=150000000,
        imdb_id=f"tt{movie_id:07d}",
        original_language="en",
        genres=genres or ["Action", "Drama"],
        credits=[
            CreditData(
                person_id=100 + movie_id,
                person_name=f"Actor {movie_id}",
                credit_type="cast",
                character_name="Main Character",
                credit_order=0,
            ),
            CreditData(
                person_id=200 + movie_id,
                person_name=f"Director {movie_id}",
                credit_type="crew",
                job="Director",
                department="Directing",
            ),
        ],
    )


SAMPLE_MOVIES = [
    create_sample_movie(550, "Fight Club", date(1999, 10, 15), ["Drama", "Thriller"], 80.0, 8.4),
    create_sample_movie(27205, "Inception", date(2010, 7, 16), ["Action", "Sci-Fi", "Thriller"], 90.0, 8.8),
    create_sample_movie(155, "The Dark Knight", date(2008, 7, 18), ["Action", "Crime", "Drama"], 95.0, 9.0),
    create_sample_movie(680, "Pulp Fiction", date(1994, 10, 14), ["Crime", "Thriller"], 70.0, 8.9),
    create_sample_movie(157336, "Interstellar", date(2014, 11, 7), ["Adventure", "Drama", "Sci-Fi"], 85.0, 8.6),
]


# =============================================================================
# MOCK DATABASE
# =============================================================================

class MockDatabaseManager:
    """In-memory mock database for testing."""

    def __init__(self):
        self.production_movies: Dict[int, MovieData] = {}
        self.pending_movies: Dict[int, MovieData] = {}
        self.production_people: Dict[int, PersonData] = {}
        self.pending_people: Dict[int, PersonData] = {}
        self.tables_created = False

    def reset(self):
        """Reset all data."""
        self.production_movies.clear()
        self.pending_movies.clear()
        self.production_people.clear()
        self.pending_people.clear()
        self.tables_created = False

    # Setup & Status
    def check_and_create_tables(self) -> dict:
        self.tables_created = True
        return {"created": ["movies", "credits", "genres", "people"], "existing": []}

    def table_exists(self, table_name: str) -> bool:
        return self.tables_created

    def get_status(self) -> dict:
        return {
            "production_movies": len(self.production_movies),
            "pending_movies": len(self.pending_movies),
            "production_people": len(self.production_people),
            "pending_people": len(self.pending_people),
        }

    # Production operations
    def movie_exists(self, movie_id: int) -> bool:
        return movie_id in self.production_movies

    def insert_movie(self, movie: MovieData) -> bool:
        if movie.id in self.production_movies:
            return False
        self.production_movies[movie.id] = movie
        for credit in movie.credits:
            person = credit.to_person_data()
            self.production_people[person.id] = person
        return True

    def get_production_count(self) -> int:
        return len(self.production_movies)

    def get_all_movie_ids(self) -> Set[int]:
        return set(self.production_movies.keys())

    def get_latest_movie_date(self) -> Optional[date]:
        if not self.production_movies:
            return None
        dates = [m.release_date for m in self.production_movies.values() if m.release_date]
        return max(dates) if dates else None

    # Pending operations (used by CLI pipeline)
    def insert_pending_movie(self, movie: MovieData) -> bool:
        if movie.id in self.pending_movies or movie.id in self.production_movies:
            return False
        self.pending_movies[movie.id] = movie
        for credit in movie.credits:
            person = credit.to_person_data()
            self.pending_people[person.id] = person
        return True

    def get_pending_movie(self, movie_id: int) -> Optional[MovieData]:
        return self.pending_movies.get(movie_id)

    def get_pending_movie_ids(self) -> Set[int]:
        return set(self.pending_movies.keys())

    def get_pending_count(self) -> int:
        return len(self.pending_movies)

    def delete_pending_movie(self, movie_id: int) -> bool:
        if movie_id in self.pending_movies:
            del self.pending_movies[movie_id]
            return True
        return False

    def approve_movie(self, movie_id: int) -> bool:
        movie = self.pending_movies.get(movie_id)
        if not movie:
            return False
        if movie_id in self.production_movies:
            return False
        del self.pending_movies[movie_id]
        self.production_movies[movie_id] = movie
        return True

    def get_pending_movies_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        movie_id: Optional[int] = None,
        **kwargs,
    ) -> Tuple[List[dict], int]:
        movies = list(self.pending_movies.values())
        if movie_id:
            movies = [m for m in movies if m.id == movie_id]
        elif search:
            movies = [m for m in movies if search.lower() in m.title.lower()]
        total = len(movies)
        start = (page - 1) * per_page
        end = start + per_page
        result = []
        for m in movies[start:end]:
            item = self._movie_to_list_item(m)
            item["created_at"] = "2024-01-01T00:00:00"
            result.append(item)
        return result, total

    def approve_movies_bulk(self, movie_ids: List[int]) -> dict:
        approved = []
        failed = []
        for mid in movie_ids:
            if self.approve_movie(mid):
                approved.append(mid)
            else:
                failed.append({"movie_id": mid, "error": "not_found_or_exists"})
        return {"approved": approved, "failed": failed}

    def delete_pending_movies_bulk(self, movie_ids: List[int]) -> List[int]:
        deleted = []
        for mid in movie_ids:
            if self.delete_pending_movie(mid):
                deleted.append(mid)
        return deleted

    def approve_all_pending(self) -> dict:
        return self.approve_movies_bulk(list(self.pending_movies.keys()))

    def delete_all_pending(self) -> int:
        count = len(self.pending_movies)
        self.pending_movies.clear()
        return count

    # Paginated queries (for public API)
    def get_movies_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        genre: Optional[str] = None,
        **kwargs,
    ) -> Tuple[List[dict], int]:
        movies = list(self.production_movies.values())
        if genre:
            movies = [m for m in movies if genre in m.genres]
        total = len(movies)
        start = (page - 1) * per_page
        end = start + per_page
        result = [self._movie_to_list_item(m) for m in movies[start:end]]
        return result, total

    def get_movie_detail(self, movie_id: int) -> Optional[dict]:
        movie = self.production_movies.get(movie_id)
        if not movie:
            return None
        return self._movie_to_detail(movie)

    def get_movie_credits(self, movie_id: int, cast_limit: int = 20, crew_limit: int = 10) -> Optional[dict]:
        movie = self.production_movies.get(movie_id)
        if not movie:
            return None
        cast = [c for c in movie.credits if c.credit_type == "cast"][:cast_limit]
        crew = [c for c in movie.credits if c.credit_type == "crew"][:crew_limit]
        return {
            "movie_id": movie_id,
            "cast": [self._credit_to_dict(c) for c in cast],
            "crew": [self._credit_to_dict(c) for c in crew],
        }

    def get_similar_movies(self, movie_id: int, limit: int = 10) -> List[dict]:
        movie = self.production_movies.get(movie_id)
        if not movie:
            return []
        similar = []
        for m in self.production_movies.values():
            if m.id != movie_id:
                shared = set(m.genres) & set(movie.genres)
                if shared:
                    similar.append((len(shared), m))
        similar.sort(key=lambda x: x[0], reverse=True)
        return [self._movie_to_list_item(m) for _, m in similar[:limit]]

    def get_trending_movies(self, limit: int = 20, time_window: str = "week") -> List[dict]:
        movies = sorted(self.production_movies.values(), key=lambda m: m.popularity or 0, reverse=True)
        return [self._movie_to_list_item(m) for m in movies[:limit]]

    def get_top_rated_movies(self, limit: int = 20, min_votes: int = 1000, genre: Optional[str] = None) -> List[dict]:
        movies = [m for m in self.production_movies.values() if (m.vote_count or 0) >= min_votes]
        if genre:
            movies = [m for m in movies if genre in m.genres]
        movies.sort(key=lambda m: m.vote_average or 0, reverse=True)
        return [self._movie_to_list_item(m) for m in movies[:limit]]

    def get_new_releases(self, limit: int = 20, days: int = 30, min_rating: Optional[float] = None):
        from datetime import timedelta
        today = date.today()
        cutoff = today - timedelta(days=days)
        movies = [m for m in self.production_movies.values() if m.release_date and m.release_date >= cutoff]
        if min_rating:
            movies = [m for m in movies if (m.vote_average or 0) >= min_rating]
        movies.sort(key=lambda m: m.release_date, reverse=True)
        return [self._movie_to_list_item(m) for m in movies[:limit]], cutoff, today

    def get_upcoming_movies(self, limit: int = 20, days: int = 60):
        from datetime import timedelta
        today = date.today()
        future = today + timedelta(days=days)
        movies = [m for m in self.production_movies.values() if m.release_date and m.release_date > today]
        movies.sort(key=lambda m: m.release_date)
        return [self._movie_to_list_item(m) for m in movies[:limit]], today, future

    def get_movies_by_decade(self, decade: str, page: int = 1, per_page: int = 20, sort_by: str = "vote_average"):
        start_year = int(decade[:4])
        end_year = start_year + 9
        movies = [
            m for m in self.production_movies.values()
            if m.release_date and start_year <= m.release_date.year <= end_year
        ]
        total = len(movies)
        start = (page - 1) * per_page
        end = start + per_page
        return [self._movie_to_list_item(m) for m in movies[start:end]], total, start_year, end_year

    def search_movies_fulltext(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        **kwargs,
    ) -> Tuple[List[dict], int]:
        query_lower = query.lower()
        movies = [m for m in self.production_movies.values() if query_lower in m.title.lower()]
        total = len(movies)
        start = (page - 1) * per_page
        end = start + per_page
        return [self._movie_to_list_item(m) for m in movies[start:end]], total

    def get_all_genres_with_counts(self) -> List[dict]:
        genre_counts: Dict[str, int] = {}
        for movie in self.production_movies.values():
            for genre in movie.genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        return [{"name": g, "movie_count": c} for g, c in sorted(genre_counts.items())]

    def get_movies_by_genre(
        self,
        genre_name: str,
        page: int = 1,
        per_page: int = 20,
        **kwargs,
    ) -> Tuple[List[dict], int]:
        movies = [m for m in self.production_movies.values() if genre_name in m.genres]
        total = len(movies)
        start = (page - 1) * per_page
        end = start + per_page
        return [self._movie_to_list_item(m) for m in movies[start:end]], total

    def get_people_paginated(self, page: int = 1, per_page: int = 20, **kwargs) -> Tuple[List[dict], int]:
        people = list(self.production_people.values())
        total = len(people)
        start = (page - 1) * per_page
        end = start + per_page
        return [p.to_dict() for p in people[start:end]], total

    def get_person_detail(self, person_id: int) -> Optional[dict]:
        person = self.production_people.get(person_id)
        if not person:
            return None
        return person.to_dict()

    def get_person_movies_paginated(
        self,
        person_id: int,
        page: int = 1,
        per_page: int = 20,
        **kwargs,
    ) -> Tuple[List[dict], int, Optional[str]]:
        person = self.production_people.get(person_id)
        if not person:
            return [], 0, None
        movies = [
            m for m in self.production_movies.values()
            if any(c.person_id == person_id for c in m.credits)
        ]
        total = len(movies)
        start = (page - 1) * per_page
        end = start + per_page
        return [self._movie_to_list_item(m) for m in movies[start:end]], total, person.name

    def search_people(self, query: str, page: int = 1, per_page: int = 20, **kwargs) -> Tuple[List[dict], int]:
        query_lower = query.lower()
        people = [p for p in self.production_people.values() if query_lower in p.name.lower()]
        total = len(people)
        start = (page - 1) * per_page
        end = start + per_page
        return [p.to_dict() for p in people[start:end]], total

    def get_people_count(self) -> int:
        return len(self.production_people)

    def get_credits_count(self) -> int:
        return sum(len(m.credits) for m in self.production_movies.values())

    # Helper methods
    def _movie_to_list_item(self, movie: MovieData) -> dict:
        return {
            "id": movie.id,
            "title": movie.title,
            "release_date": str(movie.release_date) if movie.release_date else None,
            "vote_average": movie.vote_average,
            "vote_count": movie.vote_count,
            "popularity": movie.popularity,
            "poster_path": movie.poster_path,
            "genres": movie.genres,
        }

    def _movie_to_detail(self, movie: MovieData) -> dict:
        item = self._movie_to_list_item(movie)
        item.update({
            "overview": movie.overview,
            "runtime": movie.runtime,
            "tagline": movie.tagline,
            "budget": movie.budget,
            "revenue": movie.revenue,
            "imdb_id": movie.imdb_id,
            "backdrop_path": movie.backdrop_path,
        })
        return item

    def _credit_to_dict(self, credit: CreditData) -> dict:
        return {
            "person_id": credit.person_id,
            "name": credit.person_name,
            "credit_type": credit.credit_type,
            "character": credit.character_name,
            "job": credit.job,
            "department": credit.department,
        }


# =============================================================================
# MOCK TMDB CLIENT
# =============================================================================

class MockTMDBClient:
    """Mock TMDB client that returns sample data."""

    def __init__(self, sample_movies: List[MovieData] = None):
        self.sample_movies = {m.id: m for m in (sample_movies or SAMPLE_MOVIES)}
        self.connection_ok = True

    def test_connection(self) -> bool:
        return self.connection_ok

    def get_movie_with_credits(self, movie_id: int) -> Optional[MovieData]:
        return self.sample_movies.get(movie_id)

    def search_movies(self, query: str, page: int = 1) -> List:
        from tmdb_pipeline.models import MovieSearchResult
        query_lower = query.lower()
        results = []
        for movie in self.sample_movies.values():
            if query_lower in movie.title.lower():
                results.append(MovieSearchResult.from_movie_data(movie))
        return results

    def discover_movies_since_date(self, since_date: date, page: int = 1) -> List[MovieData]:
        return [
            m for m in self.sample_movies.values()
            if m.release_date and m.release_date >= since_date
        ]


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_db():
    """Provide a fresh mock database for each test."""
    return MockDatabaseManager()


@pytest.fixture
def mock_db_with_data(mock_db):
    """Mock database pre-populated with sample movies."""
    mock_db.tables_created = True
    for movie in SAMPLE_MOVIES:
        mock_db.insert_movie(movie)
    return mock_db


@pytest.fixture
def mock_tmdb_client():
    """Provide mock TMDB client."""
    return MockTMDBClient()


@pytest.fixture
def api_client(mock_db_with_data):
    """Provide FastAPI test client with mocked dependencies."""
    from api.main import app
    from api import dependencies

    # Clear any cached config/db from previous runs
    dependencies.get_config.cache_clear()
    dependencies.get_db.cache_clear()
    dependencies.get_tmdb_client.cache_clear()

    # Override dependencies
    def get_mock_db():
        return mock_db_with_data

    def get_mock_config():
        config = MagicMock()
        config.allowed_origins = []
        return config

    app.dependency_overrides[dependencies.get_db] = get_mock_db
    app.dependency_overrides[dependencies.get_config] = get_mock_config

    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()
