"""
Approval workflow manager for TMDB Pipeline.

Handles interactive approval of pending movies:
- Interactive mode: Show movie details, approve/skip each one
- Search mode: Find specific movie, show details, approve/skip
- Quick mode: Approve all without prompts
- Safe exit: Ctrl+C or 'q' to exit, progress is saved
"""

from typing import List, Optional

from tqdm import tqdm

from .database import DatabaseManager
from .models import MovieData, MovieSearchResult, ApprovalStats
from .utils import setup_logger, format_number


class ApprovalManager:
    """
    Handles interactive approval workflow for pending movies.

    Features:
    - Interactive mode: Show movie details, approve/skip each one
    - Search mode: Find specific movie, show details, approve/skip
    - Quick mode: Approve all without prompts
    - Safe exit: Ctrl+C or 'q' to exit, progress is saved
    """

    def __init__(self, db: DatabaseManager, log_dir=None):
        self.db = db
        self.logger = setup_logger("approval", log_dir)

    def display_movie_details(self, movie: MovieData) -> None:
        """
        Display formatted movie details in terminal.

        Shows:
        - Title, Original Title, Release Date
        - Overview (truncated if long)
        - Genres
        - Director
        - Top Cast (with character names)
        - Runtime, Rating, Popularity
        - TMDB ID, IMDB ID
        """
        print(movie.display_summary())

    def prompt_approval(self) -> str:
        """
        Prompt user for approval decision.

        Returns:
            'y' - approve
            'n' - skip (don't approve, keep in pending)
            's' - skip (same as 'n')
            'q' - quit (safe exit)
            'd' - delete from pending (reject permanently)
        """
        print("\nOptions:")
        print("  [Y] Approve (move to production)")
        print("  [N/S] Skip (keep in pending for later)")
        print("  [D] Delete (remove from pending permanently)")
        print("  [Q] Quit (exit approval, progress saved)")
        print()

        while True:
            try:
                response = input("Your choice [Y/N/S/D/Q]: ").strip().lower()
                if response in ("y", "n", "s", "d", "q", ""):
                    return response if response else "n"  # Default to skip
            except EOFError:
                return "q"
            print("Invalid input. Please enter Y, N, S, D, or Q.")

    def approve_interactive(self, limit: Optional[int] = None) -> ApprovalStats:
        """
        Interactive approval: show each movie, let user decide.

        Args:
            limit: Max number of movies to process in this session

        Returns:
            ApprovalStats with results
        """
        stats = ApprovalStats()

        pending_movies = self.db.get_pending_movies_ordered(oldest_first=True, limit=limit)

        if not pending_movies:
            print("\nNo movies in pending queue!")
            stats.remaining_pending = 0
            stats.exit_reason = "completed"
            return stats

        print(f"\n{format_number(len(pending_movies))} movies to review...")
        print("(Press Ctrl+C at any time to safely exit)\n")

        try:
            for i, movie in enumerate(pending_movies, 1):
                print(f"\n[{i}/{len(pending_movies)}]")
                self.display_movie_details(movie)

                decision = self.prompt_approval()
                stats.reviewed += 1

                if decision == "y":
                    if self.db.approve_movie(movie.id):
                        print(f"Approved: {movie.title}")
                        stats.approved += 1
                        self.logger.info(f"Approved: {movie.title} ({movie.id})")
                    else:
                        print(f"ERROR approving {movie.title}")
                        self.logger.error(f"Failed to approve: {movie.title} ({movie.id})")

                elif decision in ("n", "s"):
                    print(f"Skipped: {movie.title}")
                    stats.skipped += 1

                elif decision == "d":
                    if self.db.delete_pending_movie(movie.id):
                        print(f"Deleted from pending: {movie.title}")
                        stats.deleted += 1
                        self.logger.info(f"Deleted: {movie.title} ({movie.id})")
                    else:
                        print(f"ERROR deleting {movie.title}")
                        self.logger.error(f"Failed to delete: {movie.title} ({movie.id})")

                elif decision == "q":
                    print("\nExiting approval process...")
                    stats.remaining_pending = self.db.get_pending_count()
                    stats.exit_reason = "quit"
                    return stats

        except KeyboardInterrupt:
            print("\n\nInterrupted! Progress has been saved.")
            stats.remaining_pending = self.db.get_pending_count()
            stats.exit_reason = "interrupted"
            return stats

        stats.remaining_pending = self.db.get_pending_count()
        stats.exit_reason = "completed" if not limit else "limit_reached"

        print(f"\n{stats}")
        return stats

    def approve_by_search(self, query: str) -> ApprovalStats:
        """
        Search pending movies, show matches, let user approve.

        Args:
            query: Search term for movie title

        Returns:
            ApprovalStats with results
        """
        stats = ApprovalStats()

        results = self.db.search_pending_movies(query)

        if not results:
            print(f"\nNo pending movies found matching '{query}'")
            return stats

        print(f"\nFound {len(results)} pending movies matching '{query}':\n")
        for i, movie in enumerate(results, 1):
            print(movie.display_line(i))

        print("  [0] Cancel")
        print()

        while True:
            try:
                selection = input("Select movie to review (number): ").strip()
                if selection == "0" or selection == "":
                    print("Cancelled.")
                    return stats

                idx = int(selection) - 1
                if 0 <= idx < len(results):
                    break
                print(f"Please enter a number between 1 and {len(results)}")
            except ValueError:
                print("Please enter a valid number")
            except EOFError:
                print("Cancelled.")
                return stats

        # Get full movie data
        selected = results[idx]
        movie = self.db.get_pending_movie(selected.id)

        if not movie:
            print(f"Error: Could not load movie data for ID {selected.id}")
            return stats

        self.display_movie_details(movie)
        decision = self.prompt_approval()
        stats.reviewed = 1

        if decision == "y":
            if self.db.approve_movie(movie.id):
                print(f"Approved: {movie.title}")
                stats.approved = 1
                self.logger.info(f"Approved via search: {movie.title} ({movie.id})")
        elif decision == "d":
            if self.db.delete_pending_movie(movie.id):
                print(f"Deleted: {movie.title}")
                stats.deleted = 1
                self.logger.info(f"Deleted via search: {movie.title} ({movie.id})")
        else:
            print(f"Skipped: {movie.title}")
            stats.skipped = 1

        stats.remaining_pending = self.db.get_pending_count()
        return stats

    def approve_by_id(self, movie_id: int) -> ApprovalStats:
        """
        Approve specific movie by ID.

        Args:
            movie_id: TMDB movie ID

        Returns:
            ApprovalStats with results
        """
        stats = ApprovalStats()

        movie = self.db.get_pending_movie(movie_id)

        if not movie:
            print(f"Movie {movie_id} not found in pending queue")
            return stats

        self.display_movie_details(movie)
        decision = self.prompt_approval()
        stats.reviewed = 1

        if decision == "y":
            if self.db.approve_movie(movie.id):
                print(f"Approved: {movie.title}")
                stats.approved = 1
                self.logger.info(f"Approved by ID: {movie.title} ({movie.id})")
        elif decision == "d":
            if self.db.delete_pending_movie(movie.id):
                print(f"Deleted: {movie.title}")
                stats.deleted = 1
                self.logger.info(f"Deleted by ID: {movie.title} ({movie.id})")
        else:
            print(f"Skipped: {movie.title}")
            stats.skipped = 1

        stats.remaining_pending = self.db.get_pending_count()
        return stats

    def approve_all_quick(self, batch_size: int = 100) -> ApprovalStats:
        """
        Quick mode: approve all pending without prompts.

        USE WITH CAUTION - approves everything!

        Args:
            batch_size: Process in batches of this size

        Returns:
            ApprovalStats with results
        """
        stats = ApprovalStats()

        pending_count = self.db.get_pending_count()

        if pending_count == 0:
            print("No movies in pending queue!")
            return stats

        print(f"\nWARNING: This will approve ALL {format_number(pending_count)} pending movies without review!")
        try:
            confirm = input("Type 'APPROVE ALL' to confirm: ").strip()
        except EOFError:
            print("Cancelled.")
            return stats

        if confirm != "APPROVE ALL":
            print("Cancelled.")
            return stats

        self.logger.info(f"Quick approve started for {pending_count} movies")

        # Process in batches
        with tqdm(total=pending_count, desc="Approving", unit="movie") as pbar:
            while True:
                # Get next batch of pending movies
                pending = self.db.get_pending_movies_ordered(oldest_first=True, limit=batch_size)

                if not pending:
                    break

                for movie in pending:
                    stats.reviewed += 1
                    if self.db.approve_movie(movie.id):
                        stats.approved += 1
                    else:
                        stats.skipped += 1  # Use skipped for errors in quick mode
                    pbar.update(1)

        stats.remaining_pending = self.db.get_pending_count()
        stats.exit_reason = "completed"

        self.logger.info(f"Quick approve complete: {stats.approved} approved, {stats.skipped} errors")
        print(f"\nDone! Approved {format_number(stats.approved)} movies, {stats.skipped} errors.")

        return stats

    def list_pending(self, limit: int = 20) -> List[MovieSearchResult]:
        """
        List pending movies for preview.

        Args:
            limit: Max number to show

        Returns:
            List of MovieSearchResult (basic info only)
        """
        movies = self.db.get_pending_movies_ordered(oldest_first=True, limit=limit)

        results = []
        for m in movies:
            results.append(
                MovieSearchResult.from_movie_data(m, in_production=False, in_pending=True)
            )

        return results

    def display_pending_list(self, limit: int = 20) -> None:
        """Display pending movies list."""
        pending_count = self.db.get_pending_count()

        if pending_count == 0:
            print("\nNo movies in pending queue!")
            return

        movies = self.list_pending(limit)

        print(f"\nPending movies ({format_number(pending_count)} total, showing {len(movies)}):\n")
        for i, movie in enumerate(movies, 1):
            print(movie.display_line(i))

        if pending_count > limit:
            print(f"\n... and {format_number(pending_count - limit)} more")
