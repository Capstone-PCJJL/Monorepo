"""
TMDB Pipeline - Movie data ingestion and management system.

This package provides tools for:
- Initial ingestion of movies from TMDB API
- Bulk ingestion from TMDB daily exports
- Differential updates for changed movies
- Adding new movies to pending tables
- Manual search and add functionality
- Interactive approval workflow
- Database verification against TMDB exports
"""

from .config import Config
from .models import MovieData, CreditData, PersonData, MovieSearchResult
from .client import TMDBClient
from .database import DatabaseManager
from .pipeline import TMDBPipeline
from .approval import ApprovalManager
from .exports import TMDBExportHandler, ExportMovie
from .verification import DatabaseVerifier, VerificationResult

__version__ = "1.1.0"
__all__ = [
    "Config",
    "MovieData",
    "CreditData",
    "PersonData",
    "MovieSearchResult",
    "TMDBClient",
    "DatabaseManager",
    "TMDBPipeline",
    "ApprovalManager",
    "TMDBExportHandler",
    "ExportMovie",
    "DatabaseVerifier",
    "VerificationResult",
]
