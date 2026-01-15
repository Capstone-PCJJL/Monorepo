"""
Movie endpoints for the public API.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from api.dependencies import get_db, paginate, validate_pagination
from api.exceptions import NotFoundError
from api.schemas.common import MovieSortBy, SortOrder
from tmdb_pipeline.database import DatabaseManager

router = APIRouter()


@router.get("/movies")
async def list_movies(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: MovieSortBy = Query(MovieSortBy.popularity, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.desc, description="Sort order"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    year: Optional[int] = Query(None, description="Filter by release year"),
    year_from: Optional[int] = Query(None, description="Year range start"),
    year_to: Optional[int] = Query(None, description="Year range end"),
    min_rating: Optional[float] = Query(None, ge=0, le=10, description="Minimum rating"),
    min_votes: Optional[int] = Query(None, ge=0, description="Minimum vote count"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Browse movies with filtering, sorting, and pagination.
    """
    validate_pagination(page, per_page)

    movies, total = db.get_movies_paginated(
        page=page,
        per_page=per_page,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
        genre=genre,
        year=year,
        year_from=year_from,
        year_to=year_to,
        min_rating=min_rating,
        min_votes=min_votes,
        language=language,
    )

    return paginate(movies, total, page, per_page)


@router.get("/movies/{movie_id}")
async def get_movie(
    movie_id: int,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get complete details for a specific movie.
    """
    movie = db.get_movie_detail(movie_id)
    if not movie:
        raise NotFoundError("Movie", movie_id)
    return movie


@router.get("/movies/{movie_id}/credits")
async def get_movie_credits(
    movie_id: int,
    cast_limit: int = Query(20, ge=1, le=100, description="Max cast members"),
    crew_limit: int = Query(10, ge=1, le=50, description="Max crew members"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Get credits for a movie with configurable limits.
    """
    credits = db.get_movie_credits(movie_id, cast_limit, crew_limit)
    if not credits:
        raise NotFoundError("Movie", movie_id)
    return credits


@router.get("/movies/recommended/{user_id}")
async def get_recommended_movies(
    user_id: int,
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Get recommended movies for a user.

    Returns movies that the user hasn't:
    - Marked as not interested
    - Added to watchlist
    - Rated
    """
    with db.engine.connect() as conn:
        # Optimized query - only fetch fields needed by UI
        result = conn.execute(
            text("""
                SELECT m.id, m.title, m.poster_path, m.release_date, m.runtime, m.overview
                FROM movies m
                LEFT JOIN not_interested ni ON m.id = ni.movie_id AND ni.user_id = :user_id
                LEFT JOIN watchlists w ON m.id = w.movie_id AND w.user_id = :user_id
                LEFT JOIN ratings r ON m.id = r.movie_id AND r.userId = :user_id
                WHERE ni.movie_id IS NULL
                  AND w.movie_id IS NULL
                  AND r.movie_id IS NULL
                ORDER BY m.popularity DESC
                LIMIT :limit
            """),
            {"user_id": user_id, "limit": limit}
        )
        rows = result.fetchall()

        if not rows:
            return []

        movies = [dict(row._mapping) for row in rows]
        movie_ids = [m['id'] for m in movies]

        # Step 2: Batch fetch genres for all movies at once
        genres_result = conn.execute(
            text("""
                SELECT movie_id, GROUP_CONCAT(genre_name) as genres
                FROM genres
                WHERE movie_id IN :movie_ids
                GROUP BY movie_id
            """),
            {"movie_ids": tuple(movie_ids)}
        )

        # Build genres lookup
        genres_map = {}
        for row in genres_result.fetchall():
            genres_map[row[0]] = row[1].split(',') if row[1] else []

        # Attach genres to movies
        for movie in movies:
            movie['genres'] = genres_map.get(movie['id'], [])

        return movies


@router.get("/movies/{movie_id}/similar")
async def get_similar_movies(
    movie_id: int,
    limit: int = Query(10, ge=1, le=20, description="Number of results"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Get movies similar to this one based on shared genres.
    """
    if not db.movie_exists(movie_id):
        raise NotFoundError("Movie", movie_id)

    similar = db.get_similar_movies(movie_id, limit)
    return {
        "movie_id": movie_id,
        "similar": similar,
    }
