"""
User management endpoints.

Handles user creation, consent, and import status.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from api.dependencies import get_db
from api.schemas.user import (
    UserCreate,
    UserIdResponse,
    ConsentResponse,
    ImportStatusResponse,
    SuccessResponse,
)
from tmdb_pipeline.database import DatabaseManager

router = APIRouter()
logger = logging.getLogger("api.users")


@router.post("/users/firebase", response_model=UserIdResponse, status_code=status.HTTP_200_OK)
async def get_or_create_user(
    request: UserCreate,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get existing user by Firebase ID or create a new one.

    Returns the internal user ID for the given Firebase ID.
    If user doesn't exist, creates a new user record.
    """
    with db.engine.connect() as conn:
        # Check if user exists
        result = conn.execute(
            text("SELECT userId FROM users WHERE firebaseId = :firebase_id"),
            {"firebase_id": request.firebase_id}
        )
        row = result.fetchone()

        if row:
            logger.info(f"Existing user found: user_id={row[0]}")
            return UserIdResponse(user_id=row[0])

        # Create new user
        result = conn.execute(
            text("INSERT INTO users (firebaseId, consented, imported) VALUES (:firebase_id, FALSE, FALSE)"),
            {"firebase_id": request.firebase_id}
        )
        conn.commit()

        # Get the new user ID
        result = conn.execute(
            text("SELECT userId FROM users WHERE firebaseId = :firebase_id"),
            {"firebase_id": request.firebase_id}
        )
        row = result.fetchone()

        logger.info(f"New user created: user_id={row[0]}")
        return UserIdResponse(user_id=row[0])


@router.get("/users/{user_id}/consent", response_model=ConsentResponse)
async def get_user_consent(
    user_id: int,
    db: DatabaseManager = Depends(get_db),
):
    """
    Check if a user has consented.
    """
    with db.engine.connect() as conn:
        result = conn.execute(
            text("SELECT consented FROM users WHERE userId = :user_id"),
            {"user_id": user_id}
        )
        row = result.fetchone()

        if not row:
            logger.warning(f"Consent check failed: user_id={user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return ConsentResponse(consented=bool(row[0]))


@router.put("/users/{user_id}/consent", response_model=SuccessResponse)
async def set_user_consent(
    user_id: int,
    db: DatabaseManager = Depends(get_db),
):
    """
    Set user consent to true.
    """
    with db.engine.connect() as conn:
        result = conn.execute(
            text("UPDATE users SET consented = TRUE WHERE userId = :user_id"),
            {"user_id": user_id}
        )
        conn.commit()

        if result.rowcount == 0:
            logger.warning(f"Set consent failed: user_id={user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"User consent granted: user_id={user_id}")
        return SuccessResponse()


@router.get("/users/{user_id}/import-status", response_model=ImportStatusResponse)
async def get_user_import_status(
    user_id: int,
    db: DatabaseManager = Depends(get_db),
):
    """
    Check if a user has imported their data.
    """
    with db.engine.connect() as conn:
        result = conn.execute(
            text("SELECT imported FROM users WHERE userId = :user_id"),
            {"user_id": user_id}
        )
        row = result.fetchone()

        if not row:
            logger.warning(f"Import status check failed: user_id={user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return ImportStatusResponse(imported=bool(row[0]))


@router.put("/users/{user_id}/import-status", response_model=SuccessResponse)
async def set_user_import_status(
    user_id: int,
    db: DatabaseManager = Depends(get_db),
):
    """
    Set user import status to true.
    """
    with db.engine.connect() as conn:
        result = conn.execute(
            text("UPDATE users SET imported = TRUE WHERE userId = :user_id"),
            {"user_id": user_id}
        )
        conn.commit()

        if result.rowcount == 0:
            logger.warning(f"Set import status failed: user_id={user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"User import status set: user_id={user_id}")
        return SuccessResponse()
