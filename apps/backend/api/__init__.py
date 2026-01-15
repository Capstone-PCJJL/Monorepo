"""
TMDB Pipeline REST API.

This module provides a FastAPI-based REST API for the TMDB Pipeline,
including public endpoints for browsing movies and admin endpoints
for managing the approval workflow.
"""

from api.main import app

__all__ = ["app"]
