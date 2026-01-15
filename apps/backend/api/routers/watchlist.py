"""
Watchlist endpoints.

Handles user watchlist and not-interested functionality.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from api.dependencies import get_db
from api.schemas.watchlist import (
    WatchlistAdd,
    WatchlistMovie,
    WatchlistResponse,
    NotInterestedAdd,
)
from api.schemas.user import SuccessResponse
from tmdb_pipeline.database import DatabaseManager

router = APIRouter()
logger = logging.getLogger("api.watchlist")


@router.get("/users/{user_id}/watchlist", response_model=WatchlistResponse)
async def get_watchlist(
    user_id: int,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get all movies in user's watchlist with movie details.
    """
    with db.engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT m.id, m.title, m.poster_path, m.vote_average,
                       m.release_date, m.overview
                FROM watchlists w
                JOIN movies m ON w.movie_id = m.id
                WHERE w.user_id = :user_id
            """),
            {"user_id": user_id}
        )
        rows = result.fetchall()

        movies = [
            WatchlistMovie(
                id=row[0],
                title=row[1],
                poster_path=row[2],
                vote_average=row[3],
                release_date=row[4],
                overview=row[5],
            )
            for row in rows
        ]

        return WatchlistResponse(data=movies, total=len(movies))


@router.post("/users/{user_id}/watchlist", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    user_id: int,
    request: WatchlistAdd,
    db: DatabaseManager = Depends(get_db),
):
    """
    Add a movie to user's watchlist.
    """
    with db.engine.connect() as conn:
        try:
            conn.execute(
                text("INSERT INTO watchlists (user_id, movie_id) VALUES (:user_id, :movie_id)"),
                {"user_id": user_id, "movie_id": request.movie_id}
            )
            conn.commit()
            logger.info(f"Watchlist add: user_id={user_id} movie_id={request.movie_id}")
            return SuccessResponse()
        except Exception as e:
            if "Duplicate entry" in str(e):
                logger.warning(f"Watchlist duplicate: user_id={user_id} movie_id={request.movie_id}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Movie already in watchlist"
                )
            logger.error(f"Watchlist add failed: user_id={user_id} movie_id={request.movie_id} error={e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add movie to watchlist"
            )


@router.delete("/users/{user_id}/watchlist/{movie_id}", response_model=SuccessResponse)
async def remove_from_watchlist(
    user_id: int,
    movie_id: int,
    db: DatabaseManager = Depends(get_db),
):
    """
    Remove a movie from user's watchlist.
    """
    with db.engine.connect() as conn:
        result = conn.execute(
            text("DELETE FROM watchlists WHERE user_id = :user_id AND movie_id = :movie_id"),
            {"user_id": user_id, "movie_id": movie_id}
        )
        conn.commit()

        if result.rowcount == 0:
            logger.warning(f"Watchlist remove failed: user_id={user_id} movie_id={movie_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie not found in watchlist"
            )

        logger.info(f"Watchlist remove: user_id={user_id} movie_id={movie_id}")
        return SuccessResponse()


@router.post("/users/{user_id}/not-interested", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def mark_not_interested(
    user_id: int,
    request: NotInterestedAdd,
    db: DatabaseManager = Depends(get_db),
):
    """
    Mark a movie as not interested for the user.
    """
    with db.engine.connect() as conn:
        try:
            conn.execute(
                text("INSERT INTO not_interested (user_id, movie_id) VALUES (:user_id, :movie_id)"),
                {"user_id": user_id, "movie_id": request.movie_id}
            )
            conn.commit()
            logger.info(f"Not interested: user_id={user_id} movie_id={request.movie_id}")
            return SuccessResponse()
        except Exception as e:
            if "Duplicate entry" in str(e):
                logger.warning(f"Not interested duplicate: user_id={user_id} movie_id={request.movie_id}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Movie already marked as not interested"
                )
            logger.error(f"Not interested failed: user_id={user_id} movie_id={request.movie_id} error={e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark movie as not interested"
            )
