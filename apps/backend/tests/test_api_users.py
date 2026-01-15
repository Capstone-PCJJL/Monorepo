"""
User API endpoint tests.

Tests for user-specific endpoints: users, watchlist, ratings, imports.
These endpoints use raw SQL, so we mock the database engine.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_engine():
    """Create a mock SQLAlchemy engine with connection context."""
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_conn.execute.return_value = mock_result
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn

    return mock_engine, mock_conn, mock_result


@pytest.fixture
def user_api_client(mock_engine):
    """Provide FastAPI test client with mocked database engine."""
    mock_engine_obj, mock_conn, mock_result = mock_engine

    from api.main import app
    from api import dependencies

    # Clear cached dependencies
    dependencies.get_config.cache_clear()
    dependencies.get_db.cache_clear()
    dependencies.get_tmdb_client.cache_clear()

    # Create mock database manager with engine
    mock_db = MagicMock()
    mock_db.engine = mock_engine_obj

    def get_mock_db():
        return mock_db

    def get_mock_config():
        config = MagicMock()
        config.allowed_origins = []
        return config

    app.dependency_overrides[dependencies.get_db] = get_mock_db
    app.dependency_overrides[dependencies.get_config] = get_mock_config

    with TestClient(app) as client:
        yield client, mock_conn, mock_result

    app.dependency_overrides.clear()


class TestUsersEndpoints:
    """Test user management endpoints."""

    def test_get_or_create_user_existing(self, user_api_client):
        """Test getting existing user by Firebase ID."""
        client, mock_conn, mock_result = user_api_client

        # Mock: user exists
        mock_result.fetchone.return_value = (1,)

        response = client.post(
            "/api/v1/users/firebase",
            json={"firebase_id": "test-firebase-id"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert data["user_id"] == 1

    def test_get_or_create_user_new(self, user_api_client):
        """Test creating new user."""
        client, mock_conn, mock_result = user_api_client

        # Mock: user doesn't exist, then create
        mock_result.fetchone.side_effect = [None, (2,)]

        response = client.post(
            "/api/v1/users/firebase",
            json={"firebase_id": "new-firebase-id"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data

    def test_get_user_consent(self, user_api_client):
        """Test getting user consent status."""
        client, mock_conn, mock_result = user_api_client

        # Mock: user consented
        mock_result.fetchone.return_value = (True,)

        response = client.get("/api/v1/users/1/consent")

        assert response.status_code == 200
        data = response.json()
        assert "consented" in data

    def test_get_user_consent_not_found(self, user_api_client):
        """Test consent check for nonexistent user."""
        client, mock_conn, mock_result = user_api_client

        mock_result.fetchone.return_value = None

        response = client.get("/api/v1/users/999/consent")

        assert response.status_code == 404

    def test_set_user_consent(self, user_api_client):
        """Test setting user consent."""
        client, mock_conn, mock_result = user_api_client

        mock_result.rowcount = 1

        response = client.put("/api/v1/users/1/consent")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_import_status(self, user_api_client):
        """Test getting user import status."""
        client, mock_conn, mock_result = user_api_client

        mock_result.fetchone.return_value = (False,)

        response = client.get("/api/v1/users/1/import-status")

        assert response.status_code == 200
        data = response.json()
        assert "imported" in data


class TestWatchlistEndpoints:
    """Test watchlist endpoints."""

    def test_get_watchlist(self, user_api_client):
        """Test getting user watchlist."""
        client, mock_conn, mock_result = user_api_client

        # Mock empty watchlist
        mock_result.fetchall.return_value = []

        response = client.get("/api/v1/users/1/watchlist")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data

    def test_add_to_watchlist(self, user_api_client):
        """Test adding movie to watchlist."""
        client, mock_conn, mock_result = user_api_client

        response = client.post(
            "/api/v1/users/1/watchlist",
            json={"movie_id": 550}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    def test_remove_from_watchlist(self, user_api_client):
        """Test removing movie from watchlist."""
        client, mock_conn, mock_result = user_api_client

        mock_result.rowcount = 1

        response = client.delete("/api/v1/users/1/watchlist/550")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_remove_from_watchlist_not_found(self, user_api_client):
        """Test removing movie not in watchlist."""
        client, mock_conn, mock_result = user_api_client

        mock_result.rowcount = 0

        response = client.delete("/api/v1/users/1/watchlist/999")

        assert response.status_code == 404

    def test_mark_not_interested(self, user_api_client):
        """Test marking movie as not interested."""
        client, mock_conn, mock_result = user_api_client

        response = client.post(
            "/api/v1/users/1/not-interested",
            json={"movie_id": 550}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True


class TestRatingsEndpoints:
    """Test ratings and likes endpoints."""

    def test_add_rating(self, user_api_client):
        """Test adding a movie rating."""
        client, mock_conn, mock_result = user_api_client
        from datetime import date

        # Mock movie exists
        mock_result.fetchone.side_effect = [
            ("Fight Club", date(1999, 10, 15)),  # Movie details
            (1,),  # Insert ID
        ]

        response = client.post(
            "/api/v1/users/1/ratings",
            json={"movie_id": 550, "rating": 8.5}
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data

    def test_add_rating_movie_not_found(self, user_api_client):
        """Test adding rating for nonexistent movie."""
        client, mock_conn, mock_result = user_api_client

        mock_result.fetchone.return_value = None

        response = client.post(
            "/api/v1/users/1/ratings",
            json={"movie_id": 999, "rating": 8.0}
        )

        assert response.status_code == 404

    def test_like_movie(self, user_api_client):
        """Test liking a movie."""
        client, mock_conn, mock_result = user_api_client
        from datetime import date

        # Mock movie exists
        mock_result.fetchone.side_effect = [
            ("Fight Club", date(1999, 10, 15)),  # Movie details
            (1,),  # Insert ID
        ]

        response = client.post(
            "/api/v1/users/1/likes",
            json={"movie_id": 550}
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data


class TestImportEndpoints:
    """Test CSV import endpoints."""

    def test_import_ratings_csv(self, user_api_client):
        """Test importing ratings from CSV data."""
        client, mock_conn, mock_result = user_api_client

        # Mock fuzzy_match_ratings to return 0 matches
        with patch('api.routers.imports.fuzzy_match_ratings', return_value=0):
            response = client.post(
                "/api/v1/users/1/import",
                json={
                    "table": "ratings",
                    "data": [
                        {"Name": "Fight Club", "Year": 1999, "Rating": 8.0}
                    ]
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "inserted" in data

    def test_import_likes_csv(self, user_api_client):
        """Test importing likes from CSV data."""
        client, mock_conn, mock_result = user_api_client

        with patch('api.routers.imports.fuzzy_match_likes', return_value=0):
            response = client.post(
                "/api/v1/users/1/import",
                json={
                    "table": "likes",
                    "data": [
                        {"Name": "Inception", "Year": 2010}
                    ]
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_import_empty_data(self, user_api_client):
        """Test importing empty data returns error."""
        client, mock_conn, mock_result = user_api_client

        response = client.post(
            "/api/v1/users/1/import",
            json={
                "table": "ratings",
                "data": []
            }
        )

        assert response.status_code == 400


class TestRecommendedMoviesEndpoint:
    """Test recommended movies endpoint."""

    def test_get_recommended_movies(self, user_api_client):
        """Test getting recommended movies for user."""
        client, mock_conn, mock_result = user_api_client

        # Mock movie data
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": 550,
            "title": "Fight Club",
            "genres": "Action,Drama",
        }
        mock_result.fetchall.return_value = [mock_row]

        response = client.get("/api/v1/movies/recommended/1?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
