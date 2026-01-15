"""
Genre endpoints for the public API.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_db, paginate, validate_pagination
from api.schemas.common import MovieSortBy, SortOrder
from tmdb_pipeline.database import DatabaseManager

router = APIRouter()


@router.get("/genres")
async def list_genres(
    db: DatabaseManager = Depends(get_db),
):
    """
    Get list of all genres with movie counts.
    """
    genres = db.get_all_genres_with_counts()
    return {"data": genres}


@router.get("/genres/{genre_name}/movies")
async def get_genre_movies(
    genre_name: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: MovieSortBy = Query(MovieSortBy.popularity, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.desc, description="Sort order"),
    year: Optional[int] = Query(None, description="Filter by year"),
    min_rating: Optional[float] = Query(None, ge=0, le=10, description="Minimum rating"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Get movies for a specific genre.
    """
    validate_pagination(page, per_page)

    movies, total = db.get_movies_by_genre(
        genre_name=genre_name,
        page=page,
        per_page=per_page,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
        year=year,
        min_rating=min_rating,
    )

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return {
        "genre": genre_name,
        "data": movies,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total,
            "total_pages": total_pages,
        },
    }
