"""
User-related Pydantic schemas.
"""

from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Request to create a user with Firebase ID."""

    firebase_id: str = Field(..., description="Firebase authentication ID")


class UserResponse(BaseModel):
    """User response with internal ID."""

    user_id: int = Field(..., description="Internal user ID")
    firebase_id: Optional[str] = None
    consented: bool = False
    imported: bool = False


class UserIdResponse(BaseModel):
    """Simple response with just user ID."""

    user_id: int


class ConsentResponse(BaseModel):
    """Response for consent status."""

    consented: bool


class ImportStatusResponse(BaseModel):
    """Response for import status."""

    imported: bool


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = True
