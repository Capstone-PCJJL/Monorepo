"""
Discovery endpoints for the public API.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_db, paginate, validate_pagination
from api.schemas.common import TimeWindow
from tmdb_pipeline.database import DatabaseManager

router = APIRouter()


@router.get("/discover/trending")
async def get_trending(
    limit: int = Query(20, ge=1, le=50, description="Number of results"),
    time_window: TimeWindow = Query(TimeWindow.week, description="Trending window"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Get currently trending/popular movies.
    """
    movies = db.get_trending_movies(limit=limit, time_window=time_window.value)
    return {
        "time_window": time_window.value,
        "data": movies,
    }


@router.get("/discover/top-rated")
async def get_top_rated(
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    min_votes: int = Query(1000, ge=0, description="Minimum vote count"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Get highest rated movies with minimum vote threshold.
    """
    movies = db.get_top_rated_movies(limit=limit, min_votes=min_votes, genre=genre)
    return {
        "min_votes": min_votes,
        "data": movies,
    }


@router.get("/discover/new-releases")
async def get_new_releases(
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    days: int = Query(30, ge=1, le=365, description="Movies released within N days"),
    min_rating: Optional[float] = Query(None, ge=0, le=10, description="Minimum rating"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Get recently released movies.
    """
    movies, from_date, to_date = db.get_new_releases(
        limit=limit, days=days, min_rating=min_rating
    )
    return {
        "date_range": {
            "from": str(from_date),
            "to": str(to_date),
        },
        "data": movies,
    }


@router.get("/discover/upcoming")
async def get_upcoming(
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    days: int = Query(60, ge=1, le=365, description="Movies releasing within N days"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Get movies releasing soon.
    """
    movies, from_date, to_date = db.get_upcoming_movies(limit=limit, days=days)
    return {
        "date_range": {
            "from": str(from_date),
            "to": str(to_date),
        },
        "data": movies,
    }


@router.get("/discover/by-decade")
async def get_by_decade(
    decade: str = Query(..., description="Decade: 1990s, 2000s, 2010s, 2020s"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("vote_average", description="Sort field"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Get movies from a specific decade.
    """
    validate_pagination(page, per_page)

    movies, total, start_year, end_year = db.get_movies_by_decade(
        decade=decade,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
    )

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return {
        "decade": decade,
        "year_range": {
            "from": start_year,
            "to": end_year,
        },
        "data": movies,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total,
            "total_pages": total_pages,
        },
    }
