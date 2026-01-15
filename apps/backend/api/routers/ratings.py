"""
Ratings and likes endpoints.

Handles user movie ratings and likes.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from api.dependencies import get_db
from api.schemas.rating import (
    RatingAdd,
    LikeAdd,
    RatingCreatedResponse,
    LikeCreatedResponse,
)
from tmdb_pipeline.database import DatabaseManager

router = APIRouter()
logger = logging.getLogger("api.ratings")


@router.post("/users/{user_id}/ratings", response_model=RatingCreatedResponse, status_code=status.HTTP_201_CREATED)
async def add_rating(
    user_id: int,
    request: RatingAdd,
    db: DatabaseManager = Depends(get_db),
):
    """
    Add a rating for a movie.

    Fetches the movie title and year, then creates a rating record.
    """
    with db.engine.connect() as conn:
        # Get movie details
        result = conn.execute(
            text("SELECT title, release_date FROM movies WHERE id = :movie_id"),
            {"movie_id": request.movie_id}
        )
        row = result.fetchone()

        if not row:
            logger.warning(f"Rating failed: movie_id={request.movie_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie not found"
            )

        title = row[0]
        release_date = row[1]
        year = release_date.year if release_date else None

        # Insert rating
        result = conn.execute(
            text("""
                INSERT INTO ratings (userId, name, year, rating, movie_id, watched_date, letterboxd_uri)
                VALUES (:user_id, :name, :year, :rating, :movie_id, NULL, NULL)
            """),
            {
                "user_id": user_id,
                "name": title,
                "year": year,
                "rating": request.rating,
                "movie_id": request.movie_id,
            }
        )
        conn.commit()

        # Get the inserted ID
        result = conn.execute(text("SELECT LAST_INSERT_ID()"))
        insert_id = result.fetchone()[0]

        logger.info(f"Rating added: user_id={user_id} movie_id={request.movie_id} rating={request.rating}")
        return RatingCreatedResponse(id=insert_id)


@router.post("/users/{user_id}/likes", response_model=LikeCreatedResponse, status_code=status.HTTP_201_CREATED)
async def like_movie(
    user_id: int,
    request: LikeAdd,
    db: DatabaseManager = Depends(get_db),
):
    """
    Like a movie.

    Fetches the movie title and year, then creates a like record.
    """
    with db.engine.connect() as conn:
        # Get movie details
        result = conn.execute(
            text("SELECT title, release_date FROM movies WHERE id = :movie_id"),
            {"movie_id": request.movie_id}
        )
        row = result.fetchone()

        if not row:
            logger.warning(f"Like failed: movie_id={request.movie_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie not found"
            )

        title = row[0]
        release_date = row[1]
        year = release_date.year if release_date else None

        # Insert like
        result = conn.execute(
            text("""
                INSERT INTO likes (userId, date, name, year, letterboxd_uri, movie_id)
                VALUES (:user_id, NULL, :name, :year, NULL, :movie_id)
            """),
            {
                "user_id": user_id,
                "name": title,
                "year": year,
                "movie_id": request.movie_id,
            }
        )
        conn.commit()

        # Get the inserted ID
        result = conn.execute(text("SELECT LAST_INSERT_ID()"))
        insert_id = result.fetchone()[0]

        logger.info(f"Like added: user_id={user_id} movie_id={request.movie_id}")
        return LikeCreatedResponse(id=insert_id)
