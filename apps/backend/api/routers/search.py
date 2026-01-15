"""
Search endpoints for the public API.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_db, paginate, validate_pagination
from api.schemas.common import SearchIn
from tmdb_pipeline.database import DatabaseManager

router = APIRouter()


@router.get("/search")
async def unified_search(
    q: str = Query(..., min_length=1, description="Search query"),
    movies_limit: int = Query(10, ge=1, le=50, description="Max movies to return"),
    people_limit: int = Query(5, ge=1, le=20, description="Max people to return"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Unified search across movies and people.

    For full pagination, use the dedicated /search/movies or /search/people endpoints.
    """
    # Search movies
    movies, movies_total = db.search_movies_fulltext(
        query=q,
        page=1,
        per_page=movies_limit,
    )

    # Search people
    people, people_total = db.search_people(
        query=q,
        page=1,
        per_page=people_limit,
    )

    return {
        "query": q,
        "movies": {
            "data": movies,
            "total": movies_total,
            "returned": len(movies),
        },
        "people": {
            "data": people,
            "total": people_total,
            "returned": len(people),
        },
    }


@router.get("/search/movies")
async def search_movies(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    year_from: Optional[int] = Query(None, description="Year range start"),
    year_to: Optional[int] = Query(None, description="Year range end"),
    min_rating: Optional[float] = Query(None, ge=0, le=10, description="Minimum rating"),
    search_in: SearchIn = Query(SearchIn.title, description="Where to search"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Search movies with advanced filtering and pagination.
    """
    validate_pagination(page, per_page)

    movies, total = db.search_movies_fulltext(
        query=q,
        page=page,
        per_page=per_page,
        genre=genre,
        year_from=year_from,
        year_to=year_to,
        min_rating=min_rating,
        search_in=search_in.value,
    )

    # Build filters dict for response
    filters = {}
    if genre:
        filters["genre"] = genre
    if year_from:
        filters["year_from"] = year_from
    if year_to:
        filters["year_to"] = year_to
    if min_rating:
        filters["min_rating"] = min_rating

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return {
        "query": q,
        "filters": filters if filters else None,
        "data": movies,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total,
            "total_pages": total_pages,
        },
    }


@router.get("/search/people")
async def search_people(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    department: Optional[str] = Query(None, description="Filter by department"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Search people by name with pagination.
    """
    validate_pagination(page, per_page)

    people, total = db.search_people(
        query=q,
        page=page,
        per_page=per_page,
        department=department,
    )

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return {
        "query": q,
        "data": people,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total,
            "total_pages": total_pages,
        },
    }
