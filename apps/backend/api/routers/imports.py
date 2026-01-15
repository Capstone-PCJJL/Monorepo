"""
CSV import endpoints.

Handles importing ratings and likes from Letterboxd CSV exports.
"""

import logging
from typing import List, Literal, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import text

from api.dependencies import get_db
from api.services.fuzzy_match import fuzzy_match_ratings, fuzzy_match_likes
from tmdb_pipeline.database import DatabaseManager

router = APIRouter()
logger = logging.getLogger(__name__)

# Thread pool for background tasks
executor = ThreadPoolExecutor(max_workers=2)


class RatingImportRow(BaseModel):
    """A single row from ratings.csv."""

    Name: str
    Year: Optional[int] = None
    Date: Optional[str] = None
    Rating: Optional[float] = None
    LetterboxdURI: Optional[str] = Field(None, alias="Letterboxd URI")

    class Config:
        populate_by_name = True


class LikeImportRow(BaseModel):
    """A single row from likes.csv."""

    Name: str
    Year: Optional[int] = None
    Date: Optional[str] = None
    LetterboxdURI: Optional[str] = Field(None, alias="Letterboxd URI")

    class Config:
        populate_by_name = True


class ImportRequest(BaseModel):
    """Request to import CSV data."""

    data: List[dict] = Field(..., description="Array of CSV rows")
    table: Literal["ratings", "likes"] = Field(..., description="Target table")


class ImportResponse(BaseModel):
    """Response after import."""

    message: str
    inserted: int
    matched: int = 0


def run_fuzzy_match_background(user_id: int, table: str, db: DatabaseManager):
    """Run fuzzy matching in background thread."""
    try:
        if table == "ratings":
            matched = fuzzy_match_ratings(user_id, db.engine)
            logger.info(f"Background fuzzy match completed for ratings: {matched} matched")
        elif table == "likes":
            matched = fuzzy_match_likes(user_id, db.engine)
            logger.info(f"Background fuzzy match completed for likes: {matched} matched")
    except Exception as e:
        logger.error(f"Background fuzzy match failed: {e}")


@router.post("/users/{user_id}/import", response_model=ImportResponse)
async def import_csv(
    user_id: int,
    request: ImportRequest,
    db: DatabaseManager = Depends(get_db),
):
    """
    Import ratings or likes from Letterboxd CSV export.

    After import, fuzzy matching runs in the background.
    """
    if not request.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data provided"
        )

    with db.engine.connect() as conn:
        inserted = 0

        if request.table == "ratings":
            # Batch insert ratings
            batch = []
            for row in request.data:
                try:
                    batch.append({
                        "user_id": user_id,
                        "name": row.get("Name"),
                        "year": int(row.get("Year")) if row.get("Year") else None,
                        "date": row.get("Date") or None,
                        "uri": row.get("Letterboxd URI"),
                        "rating": float(row.get("Rating")) if row.get("Rating") else None,
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse rating row: {e}")

            if batch:
                conn.execute(
                    text("""
                        INSERT INTO ratings (userId, name, year, watched_date, letterboxd_uri, rating)
                        VALUES (:user_id, :name, :year, :date, :uri, :rating)
                    """),
                    batch
                )
                inserted = len(batch)
                conn.commit()

        elif request.table == "likes":
            # Batch insert likes
            batch = []
            for row in request.data:
                try:
                    batch.append({
                        "user_id": user_id,
                        "date": row.get("Date") or None,
                        "name": row.get("Name"),
                        "year": int(row.get("Year")) if row.get("Year") else None,
                        "uri": row.get("Letterboxd URI"),
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse like row: {e}")

            if batch:
                conn.execute(
                    text("""
                        INSERT INTO likes (userId, date, name, year, letterboxd_uri)
                        VALUES (:user_id, :date, :name, :year, :uri)
                    """),
                    batch
                )
                inserted = len(batch)
                conn.commit()

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid table specified"
            )

    # Run fuzzy matching in background (don't block response)
    executor.submit(run_fuzzy_match_background, user_id, request.table, db)

    return ImportResponse(
        message=f"{request.table} CSV imported successfully (fuzzy matching in progress)",
        inserted=inserted,
        matched=0,  # Will be done in background
    )
