"""
TMDB API client for the pipeline.

Handles all TMDB API interactions including:
- Rate limiting (35 requests/second with buffer)
- Retry logic with exponential backoff
- Response parsing into data models
"""

import random
import time
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Config
from .models import MovieData, MovieSearchResult
from .utils import RateLimiter, setup_logger


class TMDBClient:
    """
    Handles all TMDB API interactions.

    Responsibilities:
    - Rate limiting (35 requests/second - below TMDB's 40/sec limit for safety)
    - Retry logic with exponential backoff and jitter
    - Response parsing into data models
    """

    # Conservative rate limit (TMDB allows 40, we use 35 for safety buffer)
    DEFAULT_RATE_LIMIT = 35
    SLOW_MODE_RATE_LIMIT = 20  # Even more conservative for large batches

    def __init__(self, config: Config):
        self.config = config
        self.session = self._create_session()
        # Use conservative rate limit
        effective_rate = min(config.rate_limit_per_second, self.DEFAULT_RATE_LIMIT)
        self.rate_limiter = RateLimiter(effective_rate)
        self.logger = setup_logger("tmdb_client", config.log_dir)
        # Track consecutive errors for adaptive backoff
        self._consecutive_errors = 0
        self._last_request_time = 0

    def enable_slow_mode(self) -> None:
        """
        Enable slow mode for large batch operations.
        Reduces rate limit to 20 requests/second for safer processing.
        """
        self.rate_limiter = RateLimiter(self.SLOW_MODE_RATE_LIMIT)
        self.logger.info(f"Slow mode enabled: {self.SLOW_MODE_RATE_LIMIT} requests/second")

    def set_rate_limit(self, requests_per_second: int) -> None:
        """
        Set custom rate limit.

        Args:
            requests_per_second: Desired rate limit (will be capped at 40)
        """
        effective_rate = min(requests_per_second, 40)
        self.rate_limiter = RateLimiter(effective_rate)
        self.logger.info(f"Rate limit set to: {effective_rate} requests/second")

    def _create_session(self) -> requests.Session:
        """Create requests session with retry configuration."""
        session = requests.Session()

        # Configure retries with longer backoff
        retry_strategy = Retry(
            total=5,  # Increased from 3
            backoff_factor=2,  # Increased from 1 (2, 4, 8, 16 seconds)
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,  # Don't raise, let us handle it
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Set default headers
        session.headers.update(self.config.get_headers())

        return session

    def _calculate_backoff(self, retry_count: int, base_delay: float = 1.0) -> float:
        """
        Calculate backoff delay with exponential increase and jitter.

        Args:
            retry_count: Current retry attempt number
            base_delay: Base delay in seconds

        Returns:
            Delay in seconds with jitter
        """
        # Exponential backoff: 1, 2, 4, 8, 16, 32... seconds
        delay = base_delay * (2 ** retry_count)
        # Add jitter (±25%) to prevent thundering herd
        jitter = delay * 0.25 * (2 * random.random() - 1)
        return min(delay + jitter, 60)  # Cap at 60 seconds

    def _adaptive_delay(self) -> None:
        """
        Add adaptive delay based on recent error rate.
        Slows down when hitting errors, speeds up when successful.
        """
        if self._consecutive_errors > 0:
            # Add extra delay when we've been hitting errors
            extra_delay = min(self._consecutive_errors * 0.5, 5.0)
            time.sleep(extra_delay)

    def _request(
        self,
        endpoint: str,
        params: dict = None,
        _retry_count: int = 0
    ) -> Optional[dict]:
        """
        Make rate-limited API request with robust error handling.

        Args:
            endpoint: API endpoint (e.g., '/movie/123')
            params: Query parameters
            _retry_count: Internal retry counter (do not set manually)

        Returns:
            JSON response or None on error
        """
        max_retries = 8  # Increased from 5

        if _retry_count >= max_retries:
            self.logger.error(f"Max retries ({max_retries}) exceeded for {endpoint}")
            return None

        # Apply rate limiting
        self.rate_limiter.acquire()

        # Add adaptive delay based on error history
        self._adaptive_delay()

        url = f"{self.config.base_url}{endpoint}"
        params = params or {}

        try:
            response = self.session.get(url, params=params, timeout=30)

            # Success - reset error counter
            if response.status_code == 200:
                self._consecutive_errors = max(0, self._consecutive_errors - 1)
                return response.json()

            # Not found - don't retry
            if response.status_code == 404:
                return None

            # Rate limited (429)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                # Add some buffer to the retry-after time
                wait_time = retry_after + random.uniform(1, 3)
                self.logger.warning(
                    f"Rate limited (429), waiting {wait_time:.1f}s "
                    f"(retry {_retry_count + 1}/{max_retries})"
                )
                self._consecutive_errors += 1
                time.sleep(wait_time)
                return self._request(endpoint, params, _retry_count + 1)

            # Server errors (500, 502, 503, 504) - retry with backoff
            if response.status_code >= 500:
                self._consecutive_errors += 1
                backoff = self._calculate_backoff(_retry_count)
                self.logger.warning(
                    f"Server error ({response.status_code}), backing off {backoff:.1f}s "
                    f"(retry {_retry_count + 1}/{max_retries})"
                )
                time.sleep(backoff)
                return self._request(endpoint, params, _retry_count + 1)

            # Other client errors - log and return None
            self.logger.error(f"Client error ({response.status_code}) for {endpoint}")
            return None

        except requests.exceptions.Timeout:
            self._consecutive_errors += 1
            backoff = self._calculate_backoff(_retry_count)
            self.logger.warning(
                f"Timeout for {endpoint}, backing off {backoff:.1f}s "
                f"(retry {_retry_count + 1}/{max_retries})"
            )
            time.sleep(backoff)
            return self._request(endpoint, params, _retry_count + 1)

        except requests.exceptions.ConnectionError:
            self._consecutive_errors += 1
            backoff = self._calculate_backoff(_retry_count, base_delay=2.0)
            self.logger.warning(
                f"Connection error for {endpoint}, backing off {backoff:.1f}s "
                f"(retry {_retry_count + 1}/{max_retries})"
            )
            time.sleep(backoff)
            return self._request(endpoint, params, _retry_count + 1)

        except requests.exceptions.RequestException as e:
            self._consecutive_errors += 1
            self.logger.error(f"Request error for {endpoint}: {e}")
            if _retry_count < max_retries - 1:
                backoff = self._calculate_backoff(_retry_count)
                time.sleep(backoff)
                return self._request(endpoint, params, _retry_count + 1)
            return None

    def get_movie_with_credits(self, movie_id: int) -> Optional[MovieData]:
        """
        Get movie details AND credits in a SINGLE API call.
        Uses: /movie/{id}?append_to_response=credits

        Args:
            movie_id: TMDB movie ID

        Returns:
            MovieData with all movie fields, top cast, director, and genres
        """
        data = self._request(
            f"/movie/{movie_id}",
            params={"append_to_response": "credits"}
        )

        if not data:
            return None

        # Skip adult content
        if data.get("adult", False) and not self.config.include_adult:
            return None

        return MovieData.from_tmdb(data, max_cast=self.config.max_cast_members)

    def get_movie_basic(self, movie_id: int) -> Optional[dict]:
        """Get basic movie info without credits (for updates check)."""
        return self._request(f"/movie/{movie_id}")

    def discover_movies_by_year(
        self,
        year: int,
        page: int = 1
    ) -> Tuple[List[int], int]:
        """
        Discover movies for a specific year.
        Uses: /discover/movie?primary_release_year={year}&include_adult=false

        Args:
            year: Year to discover movies for
            page: Page number (1-indexed)

        Returns:
            Tuple of (list of movie IDs, total_pages)
        """
        data = self._request(
            "/discover/movie",
            params={
                "primary_release_year": year,
                "include_adult": "false",
                "sort_by": "popularity.desc",
                "page": page,
            }
        )

        if not data:
            return [], 0

        movie_ids = [m["id"] for m in data.get("results", [])]
        total_pages = min(data.get("total_pages", 0), 500)  # TMDB limits to 500 pages

        return movie_ids, total_pages

    def discover_movies_since_date(
        self,
        start_date: date,
        page: int = 1
    ) -> Tuple[List[int], int]:
        """
        Discover movies released on or after a date.
        Uses: /discover/movie?primary_release_date.gte={date}&include_adult=false

        Args:
            start_date: Start date for discovery
            page: Page number (1-indexed)

        Returns:
            Tuple of (list of movie IDs, total_pages)
        """
        data = self._request(
            "/discover/movie",
            params={
                "primary_release_date.gte": start_date.isoformat(),
                "include_adult": "false",
                "sort_by": "release_date.asc",
                "page": page,
            }
        )

        if not data:
            return [], 0

        movie_ids = [m["id"] for m in data.get("results", [])]
        total_pages = min(data.get("total_pages", 0), 500)

        return movie_ids, total_pages

    def discover_movies_date_range(
        self,
        start_date: date,
        end_date: date,
        page: int = 1
    ) -> Tuple[List[int], int]:
        """
        Discover movies released within a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            page: Page number (1-indexed)

        Returns:
            Tuple of (list of movie IDs, total_pages)
        """
        data = self._request(
            "/discover/movie",
            params={
                "primary_release_date.gte": start_date.isoformat(),
                "primary_release_date.lte": end_date.isoformat(),
                "include_adult": "false",
                "sort_by": "release_date.asc",
                "page": page,
            }
        )

        if not data:
            return [], 0

        movie_ids = [m["id"] for m in data.get("results", [])]
        total_pages = min(data.get("total_pages", 0), 500)

        return movie_ids, total_pages

    def get_movie_changes(
        self,
        start_date: date,
        end_date: date,
        page: int = 1
    ) -> Tuple[List[int], int]:
        """
        Get list of movie IDs that have changed in date range.
        Uses: /movie/changes?start_date={start}&end_date={end}

        Note: TMDB only allows 14-day windows.

        Args:
            start_date: Start date for changes
            end_date: End date for changes
            page: Page number (1-indexed)

        Returns:
            Tuple of (list of movie IDs, total_pages)
        """
        # Validate 14-day window
        if (end_date - start_date).days > 14:
            self.logger.warning("Changes API limited to 14-day window, truncating")
            start_date = end_date - timedelta(days=14)

        data = self._request(
            "/movie/changes",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "page": page,
            }
        )

        if not data:
            return [], 0

        movie_ids = [m["id"] for m in data.get("results", []) if not m.get("adult", False)]
        total_pages = min(data.get("total_pages", 0), 500)

        return movie_ids, total_pages

    def search_movies(self, query: str, page: int = 1) -> List[MovieSearchResult]:
        """
        Search movies by title.
        Uses: /search/movie?query={query}&include_adult=false

        Args:
            query: Search term (title)
            page: Page number (1-indexed)

        Returns:
            List of MovieSearchResult for user selection
        """
        data = self._request(
            "/search/movie",
            params={
                "query": query,
                "include_adult": "false",
                "page": page,
            }
        )

        if not data:
            return []

        results = []
        for movie in data.get("results", []):
            if not movie.get("adult", False):
                results.append(MovieSearchResult.from_tmdb_search(movie))

        return results

    def get_earliest_movie_year(self) -> int:
        """
        Get the earliest year with movies in TMDB.
        Uses: /discover/movie?sort_by=release_date.asc

        Returns:
            Year (typically around 1874)
        """
        data = self._request(
            "/discover/movie",
            params={
                "sort_by": "release_date.asc",
                "include_adult": "false",
                "page": 1,
            }
        )

        if not data or not data.get("results"):
            return 1900  # Safe default

        # Get the first movie's release date
        first_movie = data["results"][0]
        release_date = first_movie.get("release_date", "")

        if release_date:
            try:
                return datetime.strptime(release_date, "%Y-%m-%d").year
            except ValueError:
                pass

        return 1900

    def get_total_movies_for_year(self, year: int) -> int:
        """Get total number of movies for a year."""
        data = self._request(
            "/discover/movie",
            params={
                "primary_release_year": year,
                "include_adult": "false",
                "page": 1,
            }
        )

        if not data:
            return 0

        return data.get("total_results", 0)

    def get_all_movie_ids_for_year(self, year: int) -> List[int]:
        """
        Get all movie IDs for a specific year (handles pagination).

        WARNING: Limited to 10,000 movies (500 pages × 20). Use
        get_all_movie_ids_for_year_monthly() for complete coverage.

        Args:
            year: Year to get movies for

        Returns:
            List of all movie IDs for that year (max 10,000)
        """
        all_ids = []

        # Get first page to know total pages
        ids, total_pages = self.discover_movies_by_year(year, page=1)
        all_ids.extend(ids)

        # Get remaining pages
        for page in range(2, total_pages + 1):
            ids, _ = self.discover_movies_by_year(year, page=page)
            all_ids.extend(ids)

        return all_ids

    def discover_movies_by_month(
        self,
        year: int,
        month: int,
        page: int = 1
    ) -> Tuple[List[int], int]:
        """
        Discover movies for a specific month.

        This method bypasses the 10k per-year limit by querying
        smaller date ranges.

        Args:
            year: Target year
            month: Target month (1-12)
            page: Page number for pagination

        Returns:
            Tuple of (list of movie IDs, total_pages)
        """
        # Calculate date range for the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year, 12, 31)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        return self.discover_movies_date_range(start_date, end_date, page)

    def get_all_movie_ids_for_month(self, year: int, month: int) -> List[int]:
        """
        Get all movie IDs for a specific month, handling pagination.

        Args:
            year: Target year
            month: Target month (1-12)

        Returns:
            List of all movie IDs for that month
        """
        all_ids = []
        page = 1

        while True:
            ids, total_pages = self.discover_movies_by_month(year, month, page)

            if not ids:
                break

            all_ids.extend(ids)

            if page >= total_pages or page >= 500:
                break
            page += 1

        return all_ids

    def get_all_movie_ids_for_year_monthly(self, year: int) -> List[int]:
        """
        Get all movie IDs for a year using monthly queries.

        This is more comprehensive than get_all_movie_ids_for_year() -
        it captures ALL movies even in high-volume years with >10k movies
        by querying each month separately.

        Args:
            year: Target year

        Returns:
            Deduplicated list of all movie IDs
        """
        all_ids = set()

        for month in range(1, 13):
            month_ids = self.get_all_movie_ids_for_month(year, month)
            all_ids.update(month_ids)
            self.logger.info(f"Year {year} month {month}: found {len(month_ids)} movies")

        return list(all_ids)

    def get_year_monthly_stats(self, year: int) -> dict:
        """
        Get statistics for a year using monthly breakdown.

        Useful for understanding how many movies exist per month
        and total for the year.

        Args:
            year: Target year

        Returns:
            Dict with monthly counts and total
        """
        stats = {"year": year, "months": {}, "total": 0}

        for month in range(1, 13):
            # Just get first page to see total
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year, 12, 31)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)

            data = self._request(
                "/discover/movie",
                params={
                    "primary_release_date.gte": start_date.isoformat(),
                    "primary_release_date.lte": end_date.isoformat(),
                    "include_adult": "false",
                    "page": 1,
                }
            )

            if data:
                count = data.get("total_results", 0)
                stats["months"][month] = count
                stats["total"] += count

        return stats

    def test_connection(self) -> bool:
        """Test API connection by fetching a known movie."""
        try:
            data = self._request("/movie/550")  # Fight Club
            return data is not None and "title" in data
        except Exception as e:
            self.logger.error(f"API connection test failed: {e}")
            return False
