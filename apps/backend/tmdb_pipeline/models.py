"""
Data models for TMDB Pipeline.

Provides dataclasses for type-safe data handling throughout the pipeline.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional
import json


@dataclass
class PersonData:
    """Person data from TMDB (actor, director, etc.)."""

    id: int
    name: str
    profile_path: Optional[str] = None
    gender: Optional[int] = None  # 0=unknown, 1=female, 2=male, 3=non-binary
    known_for_department: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "name": self.name,
            "profile_path": self.profile_path,
            "gender": self.gender,
            "known_for_department": self.known_for_department,
        }

    @classmethod
    def from_tmdb(cls, data: dict) -> "PersonData":
        """Create PersonData from TMDB API response."""
        return cls(
            id=data.get("id"),
            name=data.get("name", "Unknown"),
            profile_path=data.get("profile_path"),
            gender=data.get("gender"),
            known_for_department=data.get("known_for_department"),
        )


@dataclass
class CreditData:
    """Credit data (cast or crew member for a movie)."""

    person_id: int
    person_name: str
    credit_type: str  # 'cast' or 'crew'
    character_name: Optional[str] = None  # For cast
    credit_order: Optional[int] = None  # For cast ordering
    department: Optional[str] = None  # For crew
    job: Optional[str] = None  # For crew (e.g., 'Director')

    # Person data (for inserting into people table)
    profile_path: Optional[str] = None
    gender: Optional[int] = None
    known_for_department: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "person_id": self.person_id,
            "credit_type": self.credit_type,
            "character_name": self.character_name,
            "credit_order": self.credit_order,
            "department": self.department,
            "job": self.job,
        }

    def to_person_data(self) -> PersonData:
        """Extract PersonData from this credit."""
        return PersonData(
            id=self.person_id,
            name=self.person_name,
            profile_path=self.profile_path,
            gender=self.gender,
            known_for_department=self.known_for_department,
        )

    @classmethod
    def from_cast(cls, data: dict, order: int) -> "CreditData":
        """Create CreditData from TMDB cast entry."""
        return cls(
            person_id=data.get("id"),
            person_name=data.get("name", "Unknown"),
            credit_type="cast",
            character_name=data.get("character"),
            credit_order=order,
            profile_path=data.get("profile_path"),
            gender=data.get("gender"),
            known_for_department=data.get("known_for_department"),
        )

    @classmethod
    def from_crew(cls, data: dict) -> "CreditData":
        """Create CreditData from TMDB crew entry."""
        return cls(
            person_id=data.get("id"),
            person_name=data.get("name", "Unknown"),
            credit_type="crew",
            department=data.get("department"),
            job=data.get("job"),
            profile_path=data.get("profile_path"),
            gender=data.get("gender"),
            known_for_department=data.get("known_for_department"),
        )


@dataclass
class MovieData:
    """Complete movie data from TMDB."""

    id: int
    title: str
    original_title: Optional[str] = None
    overview: Optional[str] = None
    release_date: Optional[date] = None
    runtime: Optional[int] = None
    status: Optional[str] = None
    tagline: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None
    popularity: Optional[float] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    budget: Optional[int] = None
    revenue: Optional[int] = None
    imdb_id: Optional[str] = None
    original_language: Optional[str] = None
    origin_country: Optional[List[str]] = None
    english_name: Optional[str] = None
    spoken_language_codes: Optional[str] = None
    adult: bool = False

    # Related data
    genres: List[str] = field(default_factory=list)
    credits: List[CreditData] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "title": self.title,
            "original_title": self.original_title,
            "overview": self.overview,
            "release_date": self.release_date,
            "runtime": self.runtime,
            "status": self.status,
            "tagline": self.tagline,
            "vote_average": self.vote_average,
            "vote_count": self.vote_count,
            "popularity": self.popularity,
            "poster_path": self.poster_path,
            "backdrop_path": self.backdrop_path,
            "budget": self.budget,
            "revenue": self.revenue,
            "imdb_id": self.imdb_id,
            "original_language": self.original_language,
            "origin_country": json.dumps(self.origin_country) if self.origin_country else None,
            "english_name": self.english_name,
            "spoken_language_codes": self.spoken_language_codes,
        }

    def get_director(self) -> Optional[CreditData]:
        """Get the director from credits."""
        for credit in self.credits:
            if credit.credit_type == "crew" and credit.job == "Director":
                return credit
        return None

    def get_cast(self) -> List[CreditData]:
        """Get cast members from credits, ordered by credit_order."""
        cast = [c for c in self.credits if c.credit_type == "cast"]
        return sorted(cast, key=lambda c: c.credit_order or 999)

    def get_people(self) -> List[PersonData]:
        """Extract unique PersonData from all credits."""
        seen_ids = set()
        people = []
        for credit in self.credits:
            if credit.person_id not in seen_ids:
                seen_ids.add(credit.person_id)
                people.append(credit.to_person_data())
        return people

    def display_summary(self) -> str:
        """Return formatted string for terminal display."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"TITLE: {self.title}")

        if self.original_title and self.original_title != self.title:
            lines.append(f"ORIGINAL TITLE: {self.original_title}")

        lines.append(f"RELEASE DATE: {self.release_date or 'Unknown'}")
        lines.append(f"TMDB ID: {self.id}")

        if self.imdb_id:
            lines.append(f"IMDB ID: {self.imdb_id}")

        lines.append("-" * 60)

        if self.overview:
            overview = self.overview[:300] + "..." if len(self.overview) > 300 else self.overview
            lines.append(f"OVERVIEW: {overview}")
            lines.append("-" * 60)

        if self.genres:
            lines.append(f"GENRES: {', '.join(self.genres)}")

        director = self.get_director()
        if director:
            lines.append(f"DIRECTOR: {director.person_name}")

        cast = self.get_cast()[:5]
        if cast:
            lines.append("CAST:")
            for c in cast:
                char = f" as {c.character_name}" if c.character_name else ""
                lines.append(f"  - {c.person_name}{char}")

        lines.append("-" * 60)

        if self.runtime:
            lines.append(f"RUNTIME: {self.runtime} min")
        if self.vote_average:
            lines.append(f"RATING: {self.vote_average}/10 ({self.vote_count or 0} votes)")
        if self.popularity:
            lines.append(f"POPULARITY: {self.popularity:.1f}")

        lines.append("=" * 60)
        return "\n".join(lines)

    @classmethod
    def from_tmdb(cls, data: dict, max_cast: int = 8) -> "MovieData":
        """
        Create MovieData from TMDB API response.

        Args:
            data: TMDB movie response (with credits appended)
            max_cast: Maximum number of cast members to include

        Returns:
            MovieData instance with all fields populated
        """
        # Parse release date
        release_date = None
        if data.get("release_date"):
            try:
                from datetime import datetime
                release_date = datetime.strptime(data["release_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        # Parse genres
        genres = [g.get("name") for g in data.get("genres", []) if g.get("name")]

        # Parse origin country
        origin_country = data.get("origin_country", [])

        # Parse spoken languages
        spoken_langs = data.get("spoken_languages", [])
        spoken_codes = ",".join([l.get("iso_639_1", "") for l in spoken_langs if l.get("iso_639_1")])

        # Get english name from spoken languages
        english_name = None
        for lang in spoken_langs:
            if lang.get("iso_639_1") == "en":
                english_name = lang.get("english_name")
                break

        # Parse credits
        credits_data = data.get("credits", {})
        credits = []

        # Add top cast
        for i, cast_member in enumerate(credits_data.get("cast", [])[:max_cast]):
            credits.append(CreditData.from_cast(cast_member, i))

        # Add director(s) from crew
        for crew_member in credits_data.get("crew", []):
            if crew_member.get("job") == "Director":
                credits.append(CreditData.from_crew(crew_member))

        return cls(
            id=data.get("id"),
            title=data.get("title", "Unknown"),
            original_title=data.get("original_title"),
            overview=data.get("overview"),
            release_date=release_date,
            runtime=data.get("runtime"),
            status=data.get("status"),
            tagline=data.get("tagline"),
            vote_average=data.get("vote_average"),
            vote_count=data.get("vote_count"),
            popularity=data.get("popularity"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            budget=data.get("budget"),
            revenue=data.get("revenue"),
            imdb_id=data.get("imdb_id"),
            original_language=data.get("original_language"),
            origin_country=origin_country if origin_country else None,
            english_name=english_name,
            spoken_language_codes=spoken_codes if spoken_codes else None,
            adult=data.get("adult", False),
            genres=genres,
            credits=credits,
        )


@dataclass
class MovieSearchResult:
    """Search result for display to user."""

    id: int
    title: str
    release_date: Optional[str] = None
    overview: Optional[str] = None
    genres: List[str] = field(default_factory=list)
    popularity: Optional[float] = None
    vote_average: Optional[float] = None
    poster_path: Optional[str] = None
    exists_in_production: bool = False
    exists_in_pending: bool = False

    def display_line(self, index: int) -> str:
        """Return single-line display for search results list."""
        year = self.release_date[:4] if self.release_date else "Unknown"
        status = ""
        if self.exists_in_production:
            status = " [IN DB]"
        elif self.exists_in_pending:
            status = " [PENDING]"
        return f"  [{index}] {self.title} ({year}) - ID: {self.id}{status}"

    @classmethod
    def from_tmdb_search(cls, data: dict) -> "MovieSearchResult":
        """Create from TMDB search result."""
        return cls(
            id=data.get("id"),
            title=data.get("title", "Unknown"),
            release_date=data.get("release_date"),
            overview=data.get("overview"),
            popularity=data.get("popularity"),
            vote_average=data.get("vote_average"),
            poster_path=data.get("poster_path"),
        )

    @classmethod
    def from_movie_data(cls, movie: MovieData, in_production: bool = False, in_pending: bool = False) -> "MovieSearchResult":
        """Create from MovieData instance."""
        return cls(
            id=movie.id,
            title=movie.title,
            release_date=str(movie.release_date) if movie.release_date else None,
            overview=movie.overview[:100] + "..." if movie.overview and len(movie.overview) > 100 else movie.overview,
            genres=movie.genres,
            popularity=movie.popularity,
            vote_average=movie.vote_average,
            poster_path=movie.poster_path,
            exists_in_production=in_production,
            exists_in_pending=in_pending,
        )


@dataclass
class PipelineStats:
    """Statistics for pipeline operations."""

    processed: int = 0
    inserted: int = 0
    updated: int = 0
    skipped_existing: int = 0
    skipped_adult: int = 0
    skipped_no_date: int = 0
    errors: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "processed": self.processed,
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped_existing": self.skipped_existing,
            "skipped_adult": self.skipped_adult,
            "skipped_no_date": self.skipped_no_date,
            "errors": self.errors,
        }

    def __str__(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Processed: {self.processed}",
            f"Inserted: {self.inserted}",
        ]
        if self.updated:
            lines.append(f"Updated: {self.updated}")
        if self.skipped_existing:
            lines.append(f"Skipped (existing): {self.skipped_existing}")
        if self.skipped_adult:
            lines.append(f"Skipped (adult): {self.skipped_adult}")
        if self.skipped_no_date:
            lines.append(f"Skipped (no date): {self.skipped_no_date}")
        if self.errors:
            lines.append(f"Errors: {self.errors}")
        return "\n".join(lines)


@dataclass
class ApprovalStats:
    """Statistics for approval operations."""

    reviewed: int = 0
    approved: int = 0
    skipped: int = 0
    deleted: int = 0
    remaining_pending: int = 0
    exit_reason: str = "completed"  # "completed", "quit", "limit_reached", "interrupted"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "reviewed": self.reviewed,
            "approved": self.approved,
            "skipped": self.skipped,
            "deleted": self.deleted,
            "remaining_pending": self.remaining_pending,
            "exit_reason": self.exit_reason,
        }

    def __str__(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Reviewed: {self.reviewed}",
            f"Approved: {self.approved}",
            f"Skipped: {self.skipped}",
            f"Deleted: {self.deleted}",
            f"Remaining in pending: {self.remaining_pending}",
            f"Exit reason: {self.exit_reason}",
        ]
        return "\n".join(lines)
