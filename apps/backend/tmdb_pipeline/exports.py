"""
TMDB Daily Export file handler.

Downloads and parses TMDB's daily export files which contain ALL movie IDs
in the database, bypassing the 10k pagination limit of the discover API.

Export files are available at:
http://files.tmdb.org/p/exports/movie_ids_MM_DD_YYYY.json.gz

Adult content is ALWAYS filtered out - this is not configurable.
"""

import gzip
import json
import requests
from datetime import date
from pathlib import Path
from typing import Iterator, Optional
from dataclasses import dataclass

from .utils import setup_logger

logger = setup_logger(__name__)


@dataclass
class ExportMovie:
    """Lightweight movie data from export file."""
    id: int
    original_title: str
    popularity: float
    video: bool = False

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, ExportMovie):
            return self.id == other.id
        return False


class TMDBExportHandler:
    """
    Handler for TMDB daily export files.

    Downloads and parses the daily movie ID exports from TMDB.
    These files contain ALL movies in the database without pagination limits.

    NOTE: Adult content is always excluded - this is not configurable.
    """

    BASE_URL = "http://files.tmdb.org/p/exports"
    DEFAULT_CACHE_DIR = Path("tmdb_pipeline/cache/exports")

    def __init__(self, cache_dir: Optional[Path] = None, log_dir: Optional[Path] = None):
        """
        Initialize export handler.

        Args:
            cache_dir: Directory to cache downloaded exports
            log_dir: Directory for log files
        """
        self.cache_dir = cache_dir or self.DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger("tmdb_exports", log_dir)

    def get_export_url(self, export_date: Optional[date] = None) -> str:
        """
        Get URL for daily export file.

        Args:
            export_date: Date of export (default: today)

        Returns:
            Full URL to gzipped export file
        """
        if export_date is None:
            export_date = date.today()

        filename = f"movie_ids_{export_date.strftime('%m_%d_%Y')}.json.gz"
        return f"{self.BASE_URL}/{filename}"

    def download_export(
        self,
        export_date: Optional[date] = None,
        use_cache: bool = True
    ) -> Path:
        """
        Download daily export file.

        Args:
            export_date: Date of export (default: today)
            use_cache: Use cached file if available

        Returns:
            Path to downloaded (or cached) file

        Raises:
            requests.HTTPError: If download fails
        """
        if export_date is None:
            export_date = date.today()

        cache_file = self.cache_dir / f"movie_ids_{export_date.isoformat()}.json.gz"

        if use_cache and cache_file.exists():
            self.logger.info(f"Using cached export: {cache_file}")
            return cache_file

        url = self.get_export_url(export_date)
        self.logger.info(f"Downloading export from: {url}")

        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        # Get file size for progress
        total_size = int(response.headers.get('content-length', 0))
        self.logger.info(f"Export file size: {total_size / 1024 / 1024:.1f} MB")

        with open(cache_file, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)

        self.logger.info(f"Downloaded export to: {cache_file}")
        return cache_file

    def parse_export(self, file_path: Path) -> Iterator[ExportMovie]:
        """
        Parse export file and yield non-adult movie records.

        Adult content is always filtered out automatically.

        Args:
            file_path: Path to gzipped export file

        Yields:
            ExportMovie objects (adult content excluded)
        """
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())

                    # Always skip adult content - not configurable
                    if data.get('adult', False):
                        continue

                    movie = ExportMovie(
                        id=data['id'],
                        original_title=data.get('original_title', ''),
                        popularity=data.get('popularity', 0.0),
                        video=data.get('video', False)
                    )

                    yield movie

                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.warning(f"Failed to parse line: {e}")
                    continue

    def get_all_movie_ids(self, export_date: Optional[date] = None) -> set[int]:
        """
        Get all non-adult movie IDs from daily export.

        Adult content is always filtered out automatically.

        Args:
            export_date: Date of export (default: today)

        Returns:
            Set of all non-adult movie IDs
        """
        file_path = self.download_export(export_date)
        return {movie.id for movie in self.parse_export(file_path)}

    def get_movies_by_popularity(
        self,
        export_date: Optional[date] = None,
        min_popularity: float = 0.0
    ) -> list[ExportMovie]:
        """
        Get movies filtered and sorted by popularity.

        Args:
            export_date: Date of export (default: today)
            min_popularity: Minimum popularity threshold

        Returns:
            List of ExportMovie sorted by popularity descending
        """
        file_path = self.download_export(export_date)
        movies = [
            m for m in self.parse_export(file_path)
            if m.popularity >= min_popularity
        ]
        return sorted(movies, key=lambda m: m.popularity, reverse=True)

    def get_export_stats(self, export_date: Optional[date] = None) -> dict:
        """
        Get statistics about the export file.

        Args:
            export_date: Date of export (default: today)

        Returns:
            Dict with total count, min/max popularity, etc.
        """
        file_path = self.download_export(export_date)

        total = 0
        adult_skipped = 0
        min_pop = float('inf')
        max_pop = 0.0

        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())

                    if data.get('adult', False):
                        adult_skipped += 1
                        continue

                    total += 1
                    pop = data.get('popularity', 0.0)
                    min_pop = min(min_pop, pop)
                    max_pop = max(max_pop, pop)

                except (json.JSONDecodeError, KeyError):
                    continue

        return {
            "date": export_date or date.today(),
            "total_movies": total,
            "adult_skipped": adult_skipped,
            "min_popularity": min_pop if min_pop != float('inf') else 0,
            "max_popularity": max_pop,
        }

    def clear_cache(self, older_than_days: int = 7) -> int:
        """
        Clear old cached export files.

        Args:
            older_than_days: Delete files older than this many days

        Returns:
            Number of files deleted
        """
        deleted = 0
        cutoff = date.today().toordinal() - older_than_days

        for file_path in self.cache_dir.glob("movie_ids_*.json.gz"):
            # Parse date from filename
            try:
                date_str = file_path.stem.replace("movie_ids_", "")
                file_date = date.fromisoformat(date_str)
                if file_date.toordinal() < cutoff:
                    file_path.unlink()
                    deleted += 1
                    self.logger.info(f"Deleted old cache: {file_path}")
            except (ValueError, OSError) as e:
                self.logger.warning(f"Could not process cache file {file_path}: {e}")

        return deleted
