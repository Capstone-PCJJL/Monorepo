"""
Fuzzy matching service for CSV imports.

Matches imported movie names to database movies using string similarity.
"""

import logging
from typing import List, Optional, Tuple

from thefuzz import fuzz
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def fuzzy_match_ratings(user_id: int, engine: Engine, threshold: float = 0.7) -> int:
    """
    Fuzzy match ratings for a user after CSV import.

    Finds ratings without movie_id and tries to match them to movies
    in the database based on name and year.

    Args:
        user_id: User ID to match ratings for
        engine: SQLAlchemy engine
        threshold: Minimum similarity ratio (0-1) for a match

    Returns:
        Number of ratings matched
    """
    matched_count = 0

    with engine.connect() as conn:
        # Get unmatched ratings
        result = conn.execute(
            text("SELECT id, name, year FROM ratings WHERE userId = :user_id AND movie_id IS NULL"),
            {"user_id": user_id}
        )
        ratings = result.fetchall()

        if not ratings:
            return 0

        # Get all movies with release years
        result = conn.execute(
            text("SELECT id, title, YEAR(release_date) as year FROM movies")
        )
        movies = result.fetchall()

        # Create lookup by year for efficiency
        movies_by_year = {}
        for movie in movies:
            year = movie[2]
            if year not in movies_by_year:
                movies_by_year[year] = []
            movies_by_year[year].append((movie[0], movie[1]))  # (id, title)

        # Match each rating
        for rating in ratings:
            rating_id, rating_name, rating_year = rating

            if rating_year not in movies_by_year:
                logger.debug(f"No movies for year {rating_year}")
                continue

            # Find best match within the year
            best_match = None
            best_score = 0

            for movie_id, movie_title in movies_by_year[rating_year]:
                score = fuzz.ratio(rating_name.lower(), movie_title.lower()) / 100

                if score > best_score:
                    best_score = score
                    best_match = (movie_id, movie_title)

            if best_match and best_score >= threshold:
                conn.execute(
                    text("UPDATE ratings SET movie_id = :movie_id WHERE id = :rating_id"),
                    {"movie_id": best_match[0], "rating_id": rating_id}
                )
                logger.info(f"Matched: '{rating_name}' ({rating_year}) -> '{best_match[1]}' (id={best_match[0]})")
                matched_count += 1
            else:
                logger.debug(f"No good match for: '{rating_name}' ({rating_year})")

        conn.commit()

    return matched_count


def fuzzy_match_likes(user_id: int, engine: Engine, threshold: float = 0.7) -> int:
    """
    Fuzzy match likes for a user after CSV import.

    Finds likes without movie_id and tries to match them to movies
    in the database based on name and year.

    Args:
        user_id: User ID to match likes for
        engine: SQLAlchemy engine
        threshold: Minimum similarity ratio (0-1) for a match

    Returns:
        Number of likes matched
    """
    matched_count = 0

    with engine.connect() as conn:
        # Get unmatched likes
        result = conn.execute(
            text("SELECT id, name, year FROM likes WHERE userId = :user_id AND movie_id IS NULL"),
            {"user_id": user_id}
        )
        likes = result.fetchall()

        if not likes:
            return 0

        # Get all movies with release years
        result = conn.execute(
            text("SELECT id, title, YEAR(release_date) as year FROM movies")
        )
        movies = result.fetchall()

        # Create lookup by year for efficiency
        movies_by_year = {}
        for movie in movies:
            year = movie[2]
            if year not in movies_by_year:
                movies_by_year[year] = []
            movies_by_year[year].append((movie[0], movie[1]))  # (id, title)

        # Match each like
        for like in likes:
            like_id, like_name, like_year = like

            if like_year not in movies_by_year:
                logger.debug(f"No movies for year {like_year}")
                continue

            # Find best match within the year
            best_match = None
            best_score = 0

            for movie_id, movie_title in movies_by_year[like_year]:
                score = fuzz.ratio(like_name.lower(), movie_title.lower()) / 100

                if score > best_score:
                    best_score = score
                    best_match = (movie_id, movie_title)

            if best_match and best_score >= threshold:
                conn.execute(
                    text("UPDATE likes SET movie_id = :movie_id WHERE id = :like_id"),
                    {"movie_id": best_match[0], "like_id": like_id}
                )
                logger.info(f"Matched Like: '{like_name}' ({like_year}) -> '{best_match[1]}' (id={best_match[0]})")
                matched_count += 1
            else:
                logger.debug(f"No good match for Like: '{like_name}' ({like_year})")

        conn.commit()

    return matched_count
