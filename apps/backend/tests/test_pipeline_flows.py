"""
Pipeline user flow tests.

Tests mimic what a real user would do with the pipeline.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from conftest import (
    MockDatabaseManager,
    MockTMDBClient,
    SAMPLE_MOVIES,
    create_sample_movie,
)


class TestSetupAndStatusFlow:
    """Flow 1: First-time setup - setup → test → status → initial"""

    def test_setup_creates_tables(self, mock_db):
        """User runs setup on fresh database."""
        # Before setup
        assert not mock_db.tables_created

        # Run setup
        result = mock_db.check_and_create_tables()

        # After setup
        assert mock_db.tables_created
        assert "movies" in result["created"]

    def test_status_shows_empty_db(self, mock_db):
        """User checks status of empty database."""
        mock_db.check_and_create_tables()
        status = mock_db.get_status()

        assert status["production_movies"] == 0
        assert status["pending_movies"] == 0

    def test_initial_ingest_adds_movies_to_production(self, mock_db, mock_tmdb_client):
        """User runs initial ingest to populate database."""
        mock_db.check_and_create_tables()

        # Simulate what initial_ingest does (add movies directly to production)
        movies_to_add = list(mock_tmdb_client.sample_movies.values())[:3]
        for movie in movies_to_add:
            mock_db.insert_movie(movie)

        # Verify movies are in production
        assert mock_db.get_production_count() == 3
        assert mock_db.get_pending_count() == 0

    def test_status_shows_populated_db(self, mock_db_with_data):
        """User checks status after data is loaded."""
        status = mock_db_with_data.get_status()

        assert status["production_movies"] == 5  # SAMPLE_MOVIES has 5
        assert status["pending_movies"] == 0


class TestAddNewAndApproveFlow:
    """Flow 2: Adding new movies - add-new → list-pending → approve"""

    def test_add_new_movies_go_to_pending(self, mock_db_with_data, mock_tmdb_client):
        """New movies from TMDB go to pending queue."""
        # Create some new movies not in production
        new_movie = create_sample_movie(999, "New Movie", date.today())
        mock_tmdb_client.sample_movies[999] = new_movie

        # Simulate add-new: movies discovered go to pending
        mock_db_with_data.insert_pending_movie(new_movie)

        # Verify
        assert mock_db_with_data.get_pending_count() == 1
        assert 999 in mock_db_with_data.get_pending_movie_ids()

    def test_list_pending_shows_movies(self, mock_db_with_data):
        """User can see pending movies."""
        # Add movies to pending
        new_movies = [
            create_sample_movie(1001, "Pending Movie 1"),
            create_sample_movie(1002, "Pending Movie 2"),
            create_sample_movie(1003, "Pending Movie 3"),
        ]
        for movie in new_movies:
            mock_db_with_data.insert_pending_movie(movie)

        # List pending
        pending, total = mock_db_with_data.get_pending_movies_paginated()

        assert total == 3
        assert len(pending) == 3

    def test_approve_moves_to_production(self, mock_db_with_data):
        """Approving a movie moves it from pending to production."""
        # Add movie to pending
        new_movie = create_sample_movie(2001, "To Be Approved")
        mock_db_with_data.insert_pending_movie(new_movie)

        initial_prod_count = mock_db_with_data.get_production_count()

        # Approve
        success = mock_db_with_data.approve_movie(2001)

        # Verify
        assert success
        assert mock_db_with_data.get_pending_count() == 0
        assert mock_db_with_data.get_production_count() == initial_prod_count + 1
        assert mock_db_with_data.movie_exists(2001)

    def test_full_add_new_approve_flow(self, mock_db_with_data):
        """Complete flow: add 3 movies, approve 1, verify counts."""
        initial_prod = mock_db_with_data.get_production_count()

        # Add 3 new movies to pending
        for i in range(3):
            movie = create_sample_movie(3000 + i, f"New Release {i}")
            mock_db_with_data.insert_pending_movie(movie)

        assert mock_db_with_data.get_pending_count() == 3

        # Approve 1
        mock_db_with_data.approve_movie(3000)

        # Verify: 1 in production (new), 2 still pending
        assert mock_db_with_data.get_production_count() == initial_prod + 1
        assert mock_db_with_data.get_pending_count() == 2


class TestSearchAndAddFlow:
    """Flow 3: Search and add - search → select → approve"""

    def test_search_finds_movies(self, mock_tmdb_client):
        """User searches TMDB by title."""
        results = mock_tmdb_client.search_movies("Fight")

        assert len(results) >= 1
        assert any("Fight" in r.title for r in results)

    def test_search_and_add_to_pending(self, mock_db, mock_tmdb_client):
        """User finds a movie and adds it to pending."""
        mock_db.check_and_create_tables()

        # Search
        results = mock_tmdb_client.search_movies("Inception")
        assert len(results) >= 1

        # Get full movie data and add to pending
        movie_id = results[0].id
        movie = mock_tmdb_client.get_movie_with_credits(movie_id)
        mock_db.insert_pending_movie(movie)

        # Verify
        assert mock_db.get_pending_count() == 1
        pending_movie = mock_db.get_pending_movie(movie_id)
        assert pending_movie is not None
        assert pending_movie.title == "Inception"

    def test_search_add_and_approve(self, mock_db):
        """Complete flow: search → add → approve."""
        mock_db.check_and_create_tables()

        # Add movie to pending (simulating search result)
        movie = create_sample_movie(12345, "Searched Movie")
        mock_db.insert_pending_movie(movie)

        # Approve
        mock_db.approve_movie(12345)

        # Verify in production
        assert mock_db.movie_exists(12345)
        assert mock_db.get_pending_count() == 0


class TestDuplicatePrevention:
    """Flow 4: Duplicate prevention - guard rails work"""

    def test_cannot_add_existing_movie_to_pending(self, mock_db_with_data):
        """Movies already in production cannot be added to pending."""
        # Fight Club (550) is already in production
        existing_movie = create_sample_movie(550, "Fight Club")

        # Try to add to pending
        success = mock_db_with_data.insert_pending_movie(existing_movie)

        # Should fail
        assert not success
        assert mock_db_with_data.get_pending_count() == 0

    def test_cannot_insert_duplicate_to_production(self, mock_db_with_data):
        """Cannot insert a movie that's already in production."""
        # Fight Club (550) is already in production
        duplicate = create_sample_movie(550, "Fight Club Duplicate")

        success = mock_db_with_data.insert_movie(duplicate)

        # Should fail
        assert not success
        # Count unchanged
        assert mock_db_with_data.get_production_count() == 5

    def test_cannot_approve_already_in_production(self, mock_db_with_data):
        """Cannot approve a movie if same ID already in production."""
        # Add movie to pending
        movie = create_sample_movie(4001, "To Approve")
        mock_db_with_data.insert_pending_movie(movie)

        # First approval works
        success1 = mock_db_with_data.approve_movie(4001)
        assert success1

        # Try to approve again (now it's in production, not pending)
        success2 = mock_db_with_data.approve_movie(4001)
        assert not success2


class TestBulkOperations:
    """Flow 5: Bulk approve and delete operations"""

    def test_bulk_approve_selected_movies(self, mock_db_with_data):
        """Approve multiple selected movies at once."""
        # Add 5 movies to pending
        pending_ids = []
        for i in range(5):
            movie = create_sample_movie(5000 + i, f"Bulk Movie {i}")
            mock_db_with_data.insert_pending_movie(movie)
            pending_ids.append(5000 + i)

        initial_prod = mock_db_with_data.get_production_count()

        # Bulk approve first 3
        result = mock_db_with_data.approve_movies_bulk(pending_ids[:3])

        # Verify
        assert len(result["approved"]) == 3
        assert len(result["failed"]) == 0
        assert mock_db_with_data.get_production_count() == initial_prod + 3
        assert mock_db_with_data.get_pending_count() == 2

    def test_bulk_delete_selected_movies(self, mock_db_with_data):
        """Delete multiple selected pending movies."""
        # Add 5 movies to pending
        for i in range(5):
            movie = create_sample_movie(6000 + i, f"Delete Movie {i}")
            mock_db_with_data.insert_pending_movie(movie)

        # Bulk delete first 3
        deleted = mock_db_with_data.delete_pending_movies_bulk([6000, 6001, 6002])

        # Verify
        assert len(deleted) == 3
        assert mock_db_with_data.get_pending_count() == 2

    def test_approve_all_pending(self, mock_db_with_data):
        """Approve all movies in pending queue."""
        # Add 3 movies to pending
        for i in range(3):
            movie = create_sample_movie(7000 + i, f"Approve All Movie {i}")
            mock_db_with_data.insert_pending_movie(movie)

        initial_prod = mock_db_with_data.get_production_count()

        # Approve all
        result = mock_db_with_data.approve_all_pending()

        # Verify
        assert len(result["approved"]) == 3
        assert mock_db_with_data.get_pending_count() == 0
        assert mock_db_with_data.get_production_count() == initial_prod + 3

    def test_delete_all_pending(self, mock_db_with_data):
        """Delete all movies in pending queue."""
        # Add 3 movies to pending
        for i in range(3):
            movie = create_sample_movie(8000 + i, f"Delete All Movie {i}")
            mock_db_with_data.insert_pending_movie(movie)

        # Delete all
        count = mock_db_with_data.delete_all_pending()

        # Verify
        assert count == 3
        assert mock_db_with_data.get_pending_count() == 0


class TestTMDBClientBehavior:
    """Test TMDB client behaviors that pipeline depends on."""

    def test_get_movie_returns_full_data(self, mock_tmdb_client):
        """Getting a movie returns complete data with credits."""
        movie = mock_tmdb_client.get_movie_with_credits(550)

        assert movie is not None
        assert movie.title == "Fight Club"
        assert len(movie.credits) > 0
        assert len(movie.genres) > 0

    def test_get_nonexistent_movie_returns_none(self, mock_tmdb_client):
        """Getting unknown movie ID returns None."""
        movie = mock_tmdb_client.get_movie_with_credits(999999)
        assert movie is None

    def test_search_returns_results(self, mock_tmdb_client):
        """Search returns matching movies."""
        results = mock_tmdb_client.search_movies("Dark Knight")
        assert len(results) >= 1

    def test_search_no_results(self, mock_tmdb_client):
        """Search with no matches returns empty list."""
        results = mock_tmdb_client.search_movies("xyznonexistent123")
        assert len(results) == 0

    def test_connection_test(self, mock_tmdb_client):
        """Connection test works."""
        assert mock_tmdb_client.test_connection()

        mock_tmdb_client.connection_ok = False
        assert not mock_tmdb_client.test_connection()
