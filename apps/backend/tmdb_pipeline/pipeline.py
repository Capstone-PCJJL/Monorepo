"""
TMDB Pipeline orchestrator.

Main class that coordinates all pipeline operations:
- Initial ingestion
- Differential updates
- Adding new movies
- Search and add
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Set

from tqdm import tqdm

from .client import TMDBClient
from .config import Config
from .database import DatabaseManager
from .exports import TMDBExportHandler
from .models import MovieData, MovieSearchResult, PipelineStats
from .utils import setup_logger, format_number, Timer
from .verification import DatabaseVerifier, VerificationResult


class TMDBPipeline:
    """
    Main orchestrator for all pipeline operations.

    Each method is designed to be:
    - Self-contained (can run as Lambda)
    - Guarded (checks preconditions)
    - Observable (logging, progress bars)
    """

    def __init__(self, client: TMDBClient, db: DatabaseManager, config: Config):
        self.client = client
        self.db = db
        self.config = config
        self.logger = setup_logger("pipeline", config.log_dir)
        # Initialize export handler and verifier (lazy - created on demand)
        self._export_handler = None
        self._verifier = None

    @property
    def export_handler(self) -> TMDBExportHandler:
        """Lazy-initialized export handler."""
        if self._export_handler is None:
            self._export_handler = TMDBExportHandler(log_dir=self.config.log_dir)
        return self._export_handler

    @property
    def verifier(self) -> DatabaseVerifier:
        """Lazy-initialized database verifier."""
        if self._verifier is None:
            self._verifier = DatabaseVerifier(self.db, log_dir=self.config.log_dir)
        return self._verifier

    # ============ OPERATION 1: INITIAL INGESTION ============

    def initial_ingest(
        self,
        test_limit: Optional[int] = None,
        force: bool = False,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> dict:
        """
        Ingest all movies from TMDB into PRODUCTION tables.

        GUARDRAIL: Refuses to run if production tables have data (unless force=True)

        Args:
            test_limit: If set, only process this many movies (for testing)
            force: If True, bypass the empty check (DANGEROUS)
            start_year: Year to start from (default: current year)
            end_year: Year to end at (default: earliest in TMDB)

        Returns:
            Statistics dictionary
        """
        stats = PipelineStats()

        # GUARDRAIL: Check if production already has data
        if not force:
            count = self.db.get_production_count()
            if count > 0:
                raise RuntimeError(
                    f"BLOCKED: Production tables already contain {format_number(count)} movies!\n"
                    f"Initial ingestion would create duplicates.\n"
                    f"Use --force to override (DANGEROUS - will add duplicates)"
                )

        # Warn if pending has data
        pending_count = self.db.get_pending_count()
        if pending_count > 0:
            self.logger.warning(
                f"Note: {format_number(pending_count)} movies exist in pending tables. "
                f"These will NOT be affected by initial ingestion."
            )

        # Determine year range
        current_year = datetime.now().year
        if start_year is None:
            start_year = current_year
        if end_year is None:
            end_year = self.client.get_earliest_movie_year()

        self.logger.info(f"Starting initial ingestion: {start_year} -> {end_year}")
        if test_limit:
            self.logger.info(f"TEST MODE: Limited to {test_limit} movies")

        # Get existing IDs to avoid duplicates
        existing_ids = self.db.get_all_movie_ids()

        # Process years from newest to oldest
        years = list(range(start_year, end_year - 1, -1))

        with Timer("Initial ingestion") as timer:
            for year in tqdm(years, desc="Years", unit="year"):
                if test_limit and stats.inserted >= test_limit:
                    break

                year_stats = self._process_year(
                    year,
                    existing_ids,
                    test_limit=test_limit - stats.inserted if test_limit else None,
                    to_pending=False,
                )

                stats.processed += year_stats.processed
                stats.inserted += year_stats.inserted
                stats.skipped_existing += year_stats.skipped_existing
                stats.skipped_adult += year_stats.skipped_adult
                stats.skipped_no_date += year_stats.skipped_no_date
                stats.errors += year_stats.errors

                self.logger.info(f"Year {year}: +{year_stats.inserted} movies")

        self.logger.info(f"Initial ingestion complete: {stats}")
        self.logger.info(str(timer))

        return stats.to_dict()

    def _process_year(
        self,
        year: int,
        existing_ids: Set[int],
        test_limit: Optional[int] = None,
        to_pending: bool = False,
    ) -> PipelineStats:
        """Process all movies for a specific year."""
        stats = PipelineStats()

        # Get first page to know total
        movie_ids, total_pages = self.client.discover_movies_by_year(year, page=1)

        # Collect all movie IDs
        all_ids = list(movie_ids)
        for page in range(2, min(total_pages + 1, 501)):  # Max 500 pages
            if test_limit and len(all_ids) >= test_limit:
                break
            ids, _ = self.client.discover_movies_by_year(year, page=page)
            all_ids.extend(ids)

        # Apply test limit
        if test_limit:
            all_ids = all_ids[:test_limit]

        # Process each movie
        for movie_id in tqdm(all_ids, desc=f"Year {year}", leave=False):
            stats.processed += 1

            # Skip if already exists
            if movie_id in existing_ids:
                stats.skipped_existing += 1
                continue

            # Fetch movie with credits
            movie = self.client.get_movie_with_credits(movie_id)

            if movie is None:
                stats.errors += 1
                continue

            if movie.adult:
                stats.skipped_adult += 1
                continue

            if movie.release_date is None:
                stats.skipped_no_date += 1
                continue

            # Insert into database
            if to_pending:
                success = self.db.insert_pending_movie(movie)
            else:
                success = self.db.insert_movie(movie)

            if success:
                stats.inserted += 1
                existing_ids.add(movie_id)
            else:
                stats.errors += 1

        return stats

    # ============ OPERATION 2: DIFFERENTIAL UPDATES ============

    def differential_update(
        self,
        days_back: int = 14,
        test_limit: Optional[int] = None
    ) -> dict:
        """
        Update movies that have changed in TMDB.

        Args:
            days_back: How many days back to check (max 14 per TMDB API)
            test_limit: Limit number of movies to update

        Returns:
            Statistics dictionary
        """
        stats = PipelineStats()

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=min(days_back, 14))

        self.logger.info(f"Checking for changes: {start_date} to {end_date}")

        # Get our existing movie IDs
        our_movie_ids = self.db.get_all_movie_ids()

        if not our_movie_ids:
            self.logger.info("No movies in production to update")
            return stats.to_dict()

        # Get changed movie IDs from TMDB
        changed_ids = set()
        page = 1
        while True:
            ids, total_pages = self.client.get_movie_changes(start_date, end_date, page)
            changed_ids.update(ids)

            if page >= total_pages:
                break
            page += 1

        self.logger.info(f"Found {format_number(len(changed_ids))} changed movies in TMDB")

        # Filter to only movies we have
        to_update = changed_ids & our_movie_ids
        self.logger.info(f"Of these, {format_number(len(to_update))} are in our database")

        # Apply test limit
        if test_limit:
            to_update = set(list(to_update)[:test_limit])

        # Update each movie
        for movie_id in tqdm(to_update, desc="Updating", unit="movie"):
            stats.processed += 1

            movie = self.client.get_movie_with_credits(movie_id)
            if movie is None:
                stats.errors += 1
                continue

            if self.db.update_movie(movie):
                stats.updated += 1
            else:
                stats.errors += 1

        self.logger.info(f"Differential update complete: {stats}")
        return stats.to_dict()

    # ============ OPERATION 3: ADD NEW MOVIES ============

    def add_new_movies(self, test_limit: Optional[int] = None) -> dict:
        """
        Add movies released after our newest movie.

        Movies go to PENDING tables (not production directly).

        Args:
            test_limit: Limit number of movies to add

        Returns:
            Statistics dictionary
        """
        stats = PipelineStats()

        # Get newest release_date from pending (check first) or production
        latest_date = self.db.get_latest_pending_date()
        source = "pending"

        if latest_date is None:
            latest_date = self.db.get_latest_movie_date()
            source = "production"

        if latest_date is None:
            self.logger.warning("No movies in database. Use initial_ingest instead.")
            return stats.to_dict()

        self.logger.info(f"Latest movie date (from {source}): {latest_date}")

        # Add one day to avoid re-fetching the same day's movies
        start_date = latest_date + timedelta(days=1)
        end_date = date.today()

        if start_date > end_date:
            self.logger.info("Database is up to date, no new movies to fetch")
            return stats.to_dict()

        self.logger.info(f"Fetching movies from {start_date} to {end_date}")

        # Get existing IDs from both tables to avoid duplicates
        existing_ids = self.db.get_all_movie_ids() | self.db.get_pending_movie_ids()

        # Discover new movies
        all_new_ids = []
        page = 1
        while True:
            ids, total_pages = self.client.discover_movies_since_date(start_date, page)
            all_new_ids.extend(ids)

            if page >= total_pages:
                break
            page += 1

            if test_limit and len(all_new_ids) >= test_limit:
                break

        # Filter out existing
        new_ids = [mid for mid in all_new_ids if mid not in existing_ids]
        self.logger.info(f"Found {format_number(len(new_ids))} new movies to add")

        # Apply test limit
        if test_limit:
            new_ids = new_ids[:test_limit]

        # Fetch and insert each movie
        for movie_id in tqdm(new_ids, desc="Adding new movies", unit="movie"):
            stats.processed += 1

            movie = self.client.get_movie_with_credits(movie_id)
            if movie is None:
                stats.errors += 1
                continue

            if movie.adult:
                stats.skipped_adult += 1
                continue

            # Double-check it doesn't exist
            if self.db.movie_exists(movie_id) or self.db.pending_movie_exists(movie_id):
                stats.skipped_existing += 1
                continue

            if self.db.insert_pending_movie(movie):
                stats.inserted += 1
            else:
                stats.errors += 1

        self.logger.info(f"Add new movies complete: {stats}")
        return stats.to_dict()

    # ============ OPERATION 4: SEARCH AND ADD ============

    def search_movies(self, query: str) -> List[MovieSearchResult]:
        """
        Search TMDB for movies by title or ID.

        Args:
            query: Search term (title) or TMDB ID (if numeric)

        Returns:
            List of MovieSearchResult with exists_in_production/exists_in_pending flags
        """
        # Check if query is numeric (TMDB ID)
        if query.isdigit():
            movie_id = int(query)
            movie = self.client.get_movie_with_credits(movie_id)
            if movie:
                in_prod = self.db.movie_exists(movie_id)
                in_pending = self.db.pending_movie_exists(movie_id)
                return [MovieSearchResult.from_movie_data(movie, in_prod, in_pending)]
            return []

        # Search by title
        results = self.client.search_movies(query)

        # Mark which ones exist in our database
        for result in results:
            result.exists_in_production = self.db.movie_exists(result.id)
            result.exists_in_pending = self.db.pending_movie_exists(result.id)

        return results

    def add_movie_by_id(self, movie_id: int) -> dict:
        """
        Add specific movie by TMDB ID to pending tables.

        Args:
            movie_id: TMDB movie ID

        Returns:
            Result dictionary
        """
        result = {
            "success": False,
            "message": "",
            "movie_title": None,
        }

        # Check if already exists
        if self.db.movie_exists(movie_id):
            result["message"] = f"Movie {movie_id} already exists in production"
            return result

        if self.db.pending_movie_exists(movie_id):
            result["message"] = f"Movie {movie_id} already exists in pending"
            return result

        # Fetch from TMDB
        movie = self.client.get_movie_with_credits(movie_id)
        if movie is None:
            result["message"] = f"Movie {movie_id} not found in TMDB"
            return result

        if movie.adult and not self.config.include_adult:
            result["message"] = f"Movie {movie_id} is adult content"
            return result

        # Insert into pending
        if self.db.insert_pending_movie(movie):
            result["success"] = True
            result["message"] = f"Added '{movie.title}' to pending"
            result["movie_title"] = movie.title
            self.logger.info(f"Added movie to pending: {movie.title} ({movie_id})")
        else:
            result["message"] = f"Failed to insert movie {movie_id}"

        return result

    # ============ UTILITY METHODS ============

    def get_status(self) -> dict:
        """
        Get current pipeline status.

        Returns:
            Status dictionary
        """
        return self.db.get_status()

    def setup_database(self) -> dict:
        """
        Check for missing tables and create them.

        Returns:
            Setup results dictionary
        """
        return self.db.check_and_create_tables()

    def test_connection(self) -> dict:
        """
        Test API and database connections.

        Returns:
            Connection test results
        """
        results = {
            "api_connected": False,
            "db_connected": False,
            "api_error": None,
            "db_error": None,
        }

        # Test API
        try:
            results["api_connected"] = self.client.test_connection()
        except Exception as e:
            results["api_error"] = str(e)

        # Test DB
        try:
            self.db.get_production_count()
            results["db_connected"] = True
        except Exception as e:
            results["db_error"] = str(e)

        return results

    # ============ OPERATION 5: BULK INGEST FROM EXPORT ============

    def bulk_ingest_from_export(
        self,
        export_date: Optional[date] = None,
        min_popularity: float = 0.0,
        test_limit: Optional[int] = None,
        to_pending: bool = True,
    ) -> dict:
        """
        Bulk ingest all movies from TMDB daily export.

        This is the most comprehensive ingestion method - it captures ALL
        movies in TMDB without pagination limits. Downloads the daily export
        file, filters to new movies, then fetches details for each.

        Args:
            export_date: Export file date (default: yesterday)
            min_popularity: Only process movies above this popularity
            test_limit: Limit movies processed (for testing)
            to_pending: Insert to pending tables (True) or production (False)

        Returns:
            Statistics dictionary
        """
        stats = PipelineStats()

        # Use yesterday's export by default
        if export_date is None:
            export_date = date.today() - timedelta(days=1)

        self.logger.info(f"Starting bulk ingest from export ({export_date})")
        if min_popularity > 0:
            self.logger.info(f"Filtering to popularity >= {min_popularity}")

        # Get all movie IDs from export, sorted by popularity
        self.logger.info("Downloading and parsing export file...")
        movies = self.export_handler.get_movies_by_popularity(
            export_date=export_date,
            min_popularity=min_popularity
        )
        self.logger.info(f"Export contains {format_number(len(movies))} movies (popularity >= {min_popularity})")

        # Filter out existing
        existing_ids = self.db.get_all_movie_ids()
        if to_pending:
            existing_ids = existing_ids.union(self.db.get_pending_movie_ids())

        new_movies = [m for m in movies if m.id not in existing_ids]
        self.logger.info(f"Found {format_number(len(new_movies))} new movies to process")

        # Apply test limit
        if test_limit:
            new_movies = new_movies[:test_limit]
            self.logger.info(f"TEST MODE: Limited to {test_limit} movies")

        # Process each movie
        with Timer("Bulk ingest") as timer:
            for export_movie in tqdm(new_movies, desc="Ingesting", unit="movie"):
                stats.processed += 1

                try:
                    movie = self.client.get_movie_with_credits(export_movie.id)

                    if movie is None:
                        stats.errors += 1
                        continue

                    if movie.adult:
                        stats.skipped_adult += 1
                        continue

                    if movie.release_date is None:
                        stats.skipped_no_date += 1
                        continue

                    # Insert into database
                    if to_pending:
                        success = self.db.insert_pending_movie(movie)
                    else:
                        success = self.db.insert_movie(movie)

                    if success:
                        stats.inserted += 1
                    else:
                        stats.errors += 1

                except Exception as e:
                    self.logger.error(f"Error processing movie {export_movie.id}: {e}")
                    stats.errors += 1

        self.logger.info(f"Bulk ingest complete: {stats}")
        self.logger.info(str(timer))

        return stats.to_dict()

    # ============ OPERATION 6: VERIFY DATABASE ============

    def verify_database(self, export_date: Optional[date] = None) -> VerificationResult:
        """
        Verify database completeness against TMDB daily export.

        Compares local database against TMDB export to identify
        missing movies and calculate coverage statistics.

        Args:
            export_date: Export date to verify against (default: yesterday)

        Returns:
            VerificationResult with stats and missing IDs
        """
        return self.verifier.verify_against_export(export_date)

    def get_coverage_by_popularity(self, export_date: Optional[date] = None) -> dict:
        """
        Get coverage statistics broken down by popularity tier.

        Args:
            export_date: Export date to analyze

        Returns:
            Dict with coverage stats per popularity tier
        """
        return self.verifier.get_coverage_by_popularity_tier(export_date)

    # ============ OPERATION 7: BACKFILL MISSING ============

    def backfill_missing(
        self,
        verification: Optional[VerificationResult] = None,
        min_popularity: float = 0.0,
        test_limit: Optional[int] = None,
        to_pending: bool = True,
    ) -> dict:
        """
        Backfill missing movies identified by verification.

        Fetches movies that exist in TMDB export but not in database,
        prioritized by popularity.

        Args:
            verification: Previous verification result (runs verify if None)
            min_popularity: Only backfill movies above this popularity
            test_limit: Limit movies processed
            to_pending: Insert to pending tables

        Returns:
            Statistics dictionary
        """
        stats = PipelineStats()

        # Run verification if needed
        if verification is None:
            self.logger.info("Running verification...")
            verification = self.verify_database()

        if verification.is_complete:
            self.logger.info("Database is complete - no backfill needed")
            return stats.to_dict()

        self.logger.info(f"Backfilling from {verification.missing_count:,} missing movies")

        # Get prioritized missing IDs
        missing_with_popularity = self.verifier.get_missing_by_popularity(
            verification=verification,
            min_popularity=min_popularity,
            limit=test_limit,
        )

        if not missing_with_popularity:
            self.logger.info(f"No missing movies with popularity >= {min_popularity}")
            return stats.to_dict()

        self.logger.info(f"Processing {len(missing_with_popularity):,} missing movies (popularity >= {min_popularity})")

        # Process each missing movie
        with Timer("Backfill") as timer:
            for movie_id, popularity in tqdm(missing_with_popularity, desc="Backfilling", unit="movie"):
                stats.processed += 1

                try:
                    movie = self.client.get_movie_with_credits(movie_id)

                    if movie is None:
                        stats.errors += 1
                        continue

                    if movie.adult:
                        stats.skipped_adult += 1
                        continue

                    if movie.release_date is None:
                        stats.skipped_no_date += 1
                        continue

                    # Insert into database
                    if to_pending:
                        success = self.db.insert_pending_movie(movie)
                    else:
                        success = self.db.insert_movie(movie)

                    if success:
                        stats.inserted += 1
                    else:
                        stats.errors += 1

                except Exception as e:
                    self.logger.error(f"Error backfilling movie {movie_id}: {e}")
                    stats.errors += 1

        self.logger.info(f"Backfill complete: {stats}")
        self.logger.info(str(timer))

        return stats.to_dict()

    # ============ OPERATION 8: REINGEST YEAR WITH MONTHLY QUERIES ============

    def reingest_year_monthly(
        self,
        year: int,
        test_limit: Optional[int] = None,
        to_pending: bool = True,
    ) -> dict:
        """
        Re-ingest a specific year using monthly queries.

        This captures ALL movies for a year, even in high-volume years
        that exceed the 10k pagination limit. Movies already in the
        database are skipped.

        Args:
            year: Year to re-ingest
            test_limit: Limit movies processed
            to_pending: Insert to pending tables

        Returns:
            Statistics dictionary
        """
        stats = PipelineStats()

        self.logger.info(f"Re-ingesting year {year} using monthly queries...")

        # Get all IDs for the year using monthly queries
        all_ids = self.client.get_all_movie_ids_for_year_monthly(year)
        self.logger.info(f"Found {format_number(len(all_ids))} total movies for {year}")

        # Filter out existing
        existing_ids = self.db.get_all_movie_ids()
        if to_pending:
            existing_ids = existing_ids.union(self.db.get_pending_movie_ids())

        new_ids = [mid for mid in all_ids if mid not in existing_ids]
        self.logger.info(f"Found {format_number(len(new_ids))} new movies to add")

        # Apply test limit
        if test_limit:
            new_ids = new_ids[:test_limit]
            self.logger.info(f"TEST MODE: Limited to {test_limit} movies")

        # Process each movie
        with Timer(f"Reingest year {year}") as timer:
            for movie_id in tqdm(new_ids, desc=f"Year {year}", unit="movie"):
                stats.processed += 1

                try:
                    movie = self.client.get_movie_with_credits(movie_id)

                    if movie is None:
                        stats.errors += 1
                        continue

                    if movie.adult:
                        stats.skipped_adult += 1
                        continue

                    if movie.release_date is None:
                        stats.skipped_no_date += 1
                        continue

                    # Insert into database
                    if to_pending:
                        success = self.db.insert_pending_movie(movie)
                    else:
                        success = self.db.insert_movie(movie)

                    if success:
                        stats.inserted += 1
                    else:
                        stats.errors += 1

                except Exception as e:
                    self.logger.error(f"Error processing movie {movie_id}: {e}")
                    stats.errors += 1

        self.logger.info(f"Year {year} reingest complete: {stats}")
        self.logger.info(str(timer))

        return stats.to_dict()
