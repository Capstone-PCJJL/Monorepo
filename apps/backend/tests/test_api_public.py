"""
Public API user flow tests.

Tests mimic what a frontend would call.
"""

import pytest


class TestBrowseAndDiscoverFlow:
    """Flow 1: Browse and discover - landing page experience"""

    def test_get_genres_list(self, api_client):
        """Frontend loads available genres."""
        response = api_client.get("/api/v1/genres")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0
        # Each genre has name and count
        assert "name" in data["data"][0]
        assert "movie_count" in data["data"][0]

    def test_get_trending_movies(self, api_client):
        """Frontend shows trending section."""
        response = api_client.get("/api/v1/discover/trending")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "time_window" in data

    def test_get_top_rated_movies(self, api_client):
        """Frontend shows top rated section."""
        response = api_client.get("/api/v1/discover/top-rated")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_browse_movies_with_filters(self, api_client):
        """Frontend browses movies with genre filter."""
        response = api_client.get("/api/v1/movies?genre=Action&page=1&per_page=10")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 10

    def test_pagination_works(self, api_client):
        """Frontend navigates through pages."""
        # Get page 1
        response1 = api_client.get("/api/v1/movies?page=1&per_page=2")
        assert response1.status_code == 200
        data1 = response1.json()

        # Pagination metadata is present
        assert "pagination" in data1
        assert "total_items" in data1["pagination"]
        assert "total_pages" in data1["pagination"]
        assert "has_next" in data1["pagination"]
        assert "has_prev" in data1["pagination"]


class TestMovieDetailFlow:
    """Flow 2: View movie details - user clicks on a movie"""

    def test_get_movie_details(self, api_client):
        """User views movie details."""
        # Fight Club is in sample data with ID 550
        response = api_client.get("/api/v1/movies/550")

        assert response.status_code == 200
        movie = response.json()
        assert movie["id"] == 550
        assert movie["title"] == "Fight Club"
        assert "overview" in movie
        assert "genres" in movie

    def test_get_movie_credits(self, api_client):
        """User views cast and crew."""
        response = api_client.get("/api/v1/movies/550/credits?cast_limit=5&crew_limit=3")

        assert response.status_code == 200
        credits = response.json()
        assert "cast" in credits
        assert "crew" in credits
        assert credits["movie_id"] == 550

    def test_get_similar_movies(self, api_client):
        """User views recommendations."""
        response = api_client.get("/api/v1/movies/550/similar?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert "similar" in data
        assert data["movie_id"] == 550

    def test_full_movie_detail_flow(self, api_client):
        """Complete flow: details → credits → similar"""
        # Get details
        r1 = api_client.get("/api/v1/movies/27205")
        assert r1.status_code == 200
        assert r1.json()["title"] == "Inception"

        # Get credits
        r2 = api_client.get("/api/v1/movies/27205/credits")
        assert r2.status_code == 200

        # Get similar
        r3 = api_client.get("/api/v1/movies/27205/similar")
        assert r3.status_code == 200


class TestSearchFlow:
    """Flow 3: Search - user searches for movies/people"""

    def test_unified_search(self, api_client):
        """User does quick search from header."""
        response = api_client.get("/api/v1/search?q=Fight")

        assert response.status_code == 200
        data = response.json()
        assert "movies" in data
        assert "people" in data
        assert data["query"] == "Fight"

    def test_movie_search_with_pagination(self, api_client):
        """User does detailed movie search."""
        response = api_client.get("/api/v1/search/movies?q=Club&page=1&per_page=10")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert data["query"] == "Club"

    def test_people_search(self, api_client):
        """User searches for actors/directors."""
        response = api_client.get("/api/v1/search/people?q=Actor")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    def test_search_requires_query(self, api_client):
        """Search without query returns error."""
        response = api_client.get("/api/v1/search")
        assert response.status_code == 422  # Validation error


class TestPersonFlow:
    """Flow 4: Person details - user views actor/director"""

    def test_browse_people(self, api_client):
        """User browses people list."""
        response = api_client.get("/api/v1/people?page=1&per_page=10")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    def test_get_person_details(self, api_client, mock_db_with_data):
        """User views person profile."""
        # Get a person ID from the sample data
        people_ids = list(mock_db_with_data.production_people.keys())
        if people_ids:
            person_id = people_ids[0]
            response = api_client.get(f"/api/v1/people/{person_id}")

            assert response.status_code == 200
            person = response.json()
            assert "id" in person
            assert "name" in person

    def test_get_person_filmography(self, api_client, mock_db_with_data):
        """User views person's movies."""
        people_ids = list(mock_db_with_data.production_people.keys())
        if people_ids:
            person_id = people_ids[0]
            response = api_client.get(f"/api/v1/people/{person_id}/movies")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "pagination" in data


class TestDiscoverEndpoints:
    """Test all discovery endpoints."""

    def test_discover_new_releases(self, api_client):
        """Get recently released movies."""
        response = api_client.get("/api/v1/discover/new-releases?limit=10&days=30")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "date_range" in data

    def test_discover_upcoming(self, api_client):
        """Get upcoming movies."""
        response = api_client.get("/api/v1/discover/upcoming?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "date_range" in data

    def test_discover_by_decade(self, api_client):
        """Get movies by decade."""
        response = api_client.get("/api/v1/discover/by-decade?decade=1990s")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["decade"] == "1990s"


class TestErrorHandling:
    """Flow 5: Error handling - proper error responses"""

    def test_movie_not_found(self, api_client):
        """Request for nonexistent movie returns 404."""
        response = api_client.get("/api/v1/movies/999999")

        assert response.status_code == 404
        data = response.json()
        # API uses structured errors with "error" and "message" keys
        assert "error" in data or "detail" in data

    def test_person_not_found(self, api_client):
        """Request for nonexistent person returns 404."""
        response = api_client.get("/api/v1/people/999999")

        assert response.status_code == 404

    def test_invalid_pagination(self, api_client):
        """Invalid pagination parameters return error."""
        response = api_client.get("/api/v1/movies?page=0")  # page must be >= 1
        assert response.status_code == 422

        response = api_client.get("/api/v1/movies?per_page=1000")  # max is usually 100
        assert response.status_code == 422

    def test_genre_movies_endpoint(self, api_client):
        """Get movies for a specific genre."""
        response = api_client.get("/api/v1/genres/Action/movies")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["genre"] == "Action"
