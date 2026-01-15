"""
Database verification against TMDB exports.

Compares the local database against TMDB daily exports to identify
missing movies and provide coverage statistics.

Adult content is always excluded from verification.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .database import DatabaseManager
from .exports import TMDBExportHandler
from .utils import setup_logger

logger = setup_logger(__name__)


@dataclass
class VerificationResult:
    """Results of database verification against TMDB export."""

    export_date: date
    export_count: int
    database_count: int
    pending_count: int
    missing_ids: list[int] = field(default_factory=list)
    extra_ids: list[int] = field(default_factory=list)

    @property
    def total_in_db(self) -> int:
        """Total movies in both production and pending."""
        return self.database_count + self.pending_count

    @property
    def missing_count(self) -> int:
        """Number of movies missing from database."""
        return len(self.missing_ids)

    @property
    def extra_count(self) -> int:
        """Number of movies in DB but not in export (possibly deleted from TMDB)."""
        return len(self.extra_ids)

    @property
    def coverage_percent(self) -> float:
        """Percentage of TMDB movies present in database."""
        if self.export_count == 0:
            return 0.0
        return (self.total_in_db - self.extra_count) / self.export_count * 100

    @property
    def is_complete(self) -> bool:
        """True if database has all movies from export."""
        return self.missing_count == 0

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Verification Results ({self.export_date})",
            "-" * 40,
            f"TMDB Export Total:   {self.export_count:>12,}",
            f"Database (prod):     {self.database_count:>12,}",
            f"Database (pending):  {self.pending_count:>12,}",
            f"Total in DB:         {self.total_in_db:>12,}",
            "-" * 40,
            f"Missing movies:      {self.missing_count:>12,}",
            f"Extra in DB:         {self.extra_count:>12,}",
            f"Coverage:            {self.coverage_percent:>11.2f}%",
        ]

        if self.is_complete:
            lines.append("-" * 40)
            lines.append("Status: COMPLETE")
        else:
            lines.append("-" * 40)
            lines.append(f"Status: INCOMPLETE ({self.missing_count:,} missing)")

        return "\n".join(lines)


class DatabaseVerifier:
    """
    Verifies database completeness against TMDB exports.

    Compares local database contents against TMDB's daily export files
    to identify missing movies and calculate coverage statistics.

    NOTE: Adult content is always excluded from verification.
    """

    def __init__(self, db: DatabaseManager, log_dir: Optional[str] = None):
        """
        Initialize verifier.

        Args:
            db: Database manager instance
            log_dir: Directory for log files
        """
        self.db = db
        self.export_handler = TMDBExportHandler()
        self.logger = setup_logger("verifier", log_dir)

    def verify_against_export(
        self,
        export_date: Optional[date] = None,
        include_pending: bool = True
    ) -> VerificationResult:
        """
        Verify database against daily export.

        Args:
            export_date: Date of export to verify against (default: yesterday)
            include_pending: Also check pending tables

        Returns:
            VerificationResult with missing/extra IDs and stats
        """
        # Use yesterday's export by default (today's may not be ready)
        if export_date is None:
            from datetime import timedelta
            export_date = date.today() - timedelta(days=1)

        self.logger.info(f"Starting verification against export from {export_date}")

        # Get all IDs from export
        self.logger.info("Downloading and parsing export file...")
        export_ids = self.export_handler.get_all_movie_ids(export_date)
        self.logger.info(f"Export contains {len(export_ids):,} non-adult movies")

        # Get database IDs
        self.logger.info("Fetching database IDs...")
        production_ids = self.db.get_all_movie_ids()
        self.logger.info(f"Production database has {len(production_ids):,} movies")

        pending_ids = set()
        if include_pending:
            pending_ids = self.db.get_pending_movie_ids()
            self.logger.info(f"Pending database has {len(pending_ids):,} movies")

        # Combine DB IDs
        all_db_ids = production_ids.union(pending_ids)

        # Calculate differences
        missing_ids = list(export_ids - all_db_ids)
        extra_ids = list(all_db_ids - export_ids)

        self.logger.info(f"Missing: {len(missing_ids):,}, Extra: {len(extra_ids):,}")

        return VerificationResult(
            export_date=export_date,
            export_count=len(export_ids),
            database_count=len(production_ids),
            pending_count=len(pending_ids),
            missing_ids=missing_ids,
            extra_ids=extra_ids,
        )

    def get_missing_by_popularity(
        self,
        verification: Optional[VerificationResult] = None,
        min_popularity: float = 0.0,
        limit: Optional[int] = None,
        export_date: Optional[date] = None
    ) -> list[tuple[int, float]]:
        """
        Get missing movie IDs sorted by popularity.

        Args:
            verification: Previous verification result (runs verify if None)
            min_popularity: Only include movies above this popularity
            limit: Maximum number of IDs to return
            export_date: Export date for popularity data

        Returns:
            List of (movie_id, popularity) tuples sorted by popularity desc
        """
        if verification is None:
            verification = self.verify_against_export(export_date)

        if not verification.missing_ids:
            return []

        # Get popularity data from export
        self.logger.info("Getting popularity data for missing movies...")
        movies = self.export_handler.get_movies_by_popularity(
            export_date=verification.export_date,
            min_popularity=min_popularity
        )

        missing_set = set(verification.missing_ids)
        prioritized = [
            (m.id, m.popularity)
            for m in movies
            if m.id in missing_set
        ]

        if limit:
            prioritized = prioritized[:limit]

        return prioritized

    def get_coverage_by_popularity_tier(
        self,
        export_date: Optional[date] = None
    ) -> dict:
        """
        Get coverage statistics broken down by popularity tiers.

        Args:
            export_date: Export date to analyze

        Returns:
            Dict with coverage stats per popularity tier
        """
        if export_date is None:
            from datetime import timedelta
            export_date = date.today() - timedelta(days=1)

        self.logger.info("Analyzing coverage by popularity tier...")

        # Get all data
        movies = self.export_handler.get_movies_by_popularity(export_date)
        db_ids = self.db.get_all_movie_ids().union(self.db.get_pending_movie_ids())

        # Define tiers
        tiers = {
            "very_high (>100)": lambda p: p > 100,
            "high (10-100)": lambda p: 10 < p <= 100,
            "medium (1-10)": lambda p: 1 < p <= 10,
            "low (0.1-1)": lambda p: 0.1 < p <= 1,
            "very_low (<0.1)": lambda p: p <= 0.1,
        }

        results = {}
        for tier_name, condition in tiers.items():
            tier_movies = [m for m in movies if condition(m.popularity)]
            tier_ids = {m.id for m in tier_movies}
            in_db = len(tier_ids.intersection(db_ids))
            total = len(tier_ids)
            coverage = (in_db / total * 100) if total > 0 else 0

            results[tier_name] = {
                "total": total,
                "in_database": in_db,
                "missing": total - in_db,
                "coverage_percent": coverage,
            }

        return results
