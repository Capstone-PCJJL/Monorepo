"""
People endpoints for the public API.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_db, paginate, validate_pagination
from api.exceptions import NotFoundError
from api.schemas.common import CreditType, SortOrder
from tmdb_pipeline.database import DatabaseManager

router = APIRouter()


@router.get("/people")
async def list_people(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    department: Optional[str] = Query(None, description="Filter by department"),
    search: Optional[str] = Query(None, description="Search by name"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Browse people (actors, directors, crew) with pagination.
    """
    validate_pagination(page, per_page)

    people, total = db.get_people_paginated(
        page=page,
        per_page=per_page,
        department=department,
        search=search,
    )

    return paginate(people, total, page, per_page)


@router.get("/people/{person_id}")
async def get_person(
    person_id: int,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get details for a specific person including filmography.
    """
    person = db.get_person_detail(person_id)
    if not person:
        raise NotFoundError("Person", person_id)
    return person


@router.get("/people/{person_id}/movies")
async def get_person_movies(
    person_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    credit_type: Optional[CreditType] = Query(None, description="Filter: cast or crew"),
    sort_by: str = Query("release_date", description="Sort field"),
    db: DatabaseManager = Depends(get_db),
):
    """
    Get paginated filmography for a person.
    """
    validate_pagination(page, per_page)

    credit_type_value = credit_type.value if credit_type else None
    movies, total, person_name = db.get_person_movies_paginated(
        person_id=person_id,
        page=page,
        per_page=per_page,
        credit_type=credit_type_value,
        sort_by=sort_by,
    )

    if not person_name:
        raise NotFoundError("Person", person_id)

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return {
        "person_id": person_id,
        "person_name": person_name,
        "data": movies,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total,
            "total_pages": total_pages,
        },
    }
