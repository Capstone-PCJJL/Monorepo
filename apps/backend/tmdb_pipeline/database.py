"""
Database manager for TMDB Pipeline.

Handles all database operations including:
- Connection management with SQLAlchemy
- CRUD operations for production and pending tables
- Guardrail checks
- Approval workflow operations
"""

import json
from datetime import date
from pathlib import Path
from typing import List, Optional, Set, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from .config import Config
from .models import MovieData, CreditData, PersonData, MovieSearchResult
from .utils import setup_logger


class DatabaseManager:
    """
    Handles all database operations.

    Responsibilities:
    - Connection management with SQLAlchemy
    - Transaction management
    - CRUD for all tables (production and pending)
    - Guardrail checks
    """

    # Required tables for the pipeline
    PRODUCTION_TABLES = ["movies", "credits", "genres", "people"]
    PENDING_TABLES = ["movies_pending", "credits_pending", "genres_pending", "people_pending"]

    def __init__(self, config: Config):
        self.config = config
        self.engine = self._create_engine()
        self.logger = setup_logger("database", config.log_dir)

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with connection pooling."""
        return create_engine(
            self.config.get_db_url(),
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

    def _execute(self, query: str, params: dict = None) -> list:
        """Execute a query and return results."""
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            conn.commit()
            return result.fetchall() if result.returns_rows else []

    def _execute_many(self, query: str, params_list: List[dict]) -> int:
        """Execute a query for multiple parameter sets."""
        with self.engine.connect() as conn:
            for params in params_list:
                conn.execute(text(query), params)
            conn.commit()
        return len(params_list)

    # ============ GUARDRAIL CHECKS ============

    def is_production_empty(self) -> bool:
        """Check if production movies table is empty."""
        result = self._execute("SELECT COUNT(*) as cnt FROM movies")
        return result[0][0] == 0

    def is_pending_empty(self) -> bool:
        """Check if pending movies table is empty."""
        result = self._execute("SELECT COUNT(*) as cnt FROM movies_pending")
        return result[0][0] == 0

    def get_production_count(self) -> int:
        """Get count of movies in production table."""
        result = self._execute("SELECT COUNT(*) as cnt FROM movies")
        return result[0][0]

    def get_pending_count(self) -> int:
        """Get count of movies in pending table."""
        result = self._execute("SELECT COUNT(*) as cnt FROM movies_pending")
        return result[0][0]

    # ============ PRODUCTION TABLE OPERATIONS ============

    def get_all_movie_ids(self) -> Set[int]:
        """Get all movie IDs from production movies table."""
        result = self._execute("SELECT id FROM movies")
        return {row[0] for row in result}

    def get_latest_movie_date(self) -> Optional[date]:
        """Get the most recent release_date from production movies table."""
        result = self._execute(
            "SELECT MAX(release_date) FROM movies WHERE release_date IS NOT NULL"
        )
        return result[0][0] if result and result[0][0] else None

    def movie_exists(self, movie_id: int) -> bool:
        """Check if movie exists in production table."""
        result = self._execute(
            "SELECT 1 FROM movies WHERE id = :id LIMIT 1",
            {"id": movie_id}
        )
        return len(result) > 0

    def insert_movie(self, movie_data: MovieData) -> bool:
        """
        Insert movie into production tables.
        Inserts into: movies, credits, genres, people (if not exists)
        """
        try:
            with self.engine.connect() as conn:
                # Insert movie
                movie_dict = movie_data.to_dict()
                columns = ", ".join(movie_dict.keys())
                placeholders = ", ".join(f":{k}" for k in movie_dict.keys())
                conn.execute(
                    text(f"INSERT INTO movies ({columns}) VALUES ({placeholders})"),
                    movie_dict
                )

                # Insert people (ignore duplicates)
                for person in movie_data.get_people():
                    self._insert_person(conn, person, pending=False)

                # Insert credits
                for credit in movie_data.credits:
                    self._insert_credit(conn, movie_data.id, credit, pending=False)

                # Insert genres
                for genre in movie_data.genres:
                    conn.execute(
                        text("INSERT IGNORE INTO genres (movie_id, genre_name) VALUES (:movie_id, :genre_name)"),
                        {"movie_id": movie_data.id, "genre_name": genre}
                    )

                conn.commit()
                return True

        except IntegrityError as e:
            self.logger.warning(f"Duplicate movie {movie_data.id}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error inserting movie {movie_data.id}: {e}")
            return False

    def insert_movies_batch(self, movies: List[MovieData]) -> int:
        """Batch insert movies into production tables."""
        inserted = 0
        for movie in movies:
            if self.insert_movie(movie):
                inserted += 1
        return inserted

    def update_movie(self, movie_data: MovieData) -> bool:
        """Update existing movie in production tables."""
        try:
            with self.engine.connect() as conn:
                # Update movie
                movie_dict = movie_data.to_dict()
                del movie_dict["id"]  # Don't update ID
                set_clause = ", ".join(f"{k} = :{k}" for k in movie_dict.keys())
                movie_dict["id"] = movie_data.id
                conn.execute(
                    text(f"UPDATE movies SET {set_clause} WHERE id = :id"),
                    movie_dict
                )

                # Delete existing credits and genres for this movie
                conn.execute(
                    text("DELETE FROM credits WHERE movie_id = :movie_id"),
                    {"movie_id": movie_data.id}
                )
                conn.execute(
                    text("DELETE FROM genres WHERE movie_id = :movie_id"),
                    {"movie_id": movie_data.id}
                )

                # Re-insert people, credits, genres
                for person in movie_data.get_people():
                    self._insert_person(conn, person, pending=False)

                for credit in movie_data.credits:
                    self._insert_credit(conn, movie_data.id, credit, pending=False)

                for genre in movie_data.genres:
                    conn.execute(
                        text("INSERT IGNORE INTO genres (movie_id, genre_name) VALUES (:movie_id, :genre_name)"),
                        {"movie_id": movie_data.id, "genre_name": genre}
                    )

                conn.commit()
                return True

        except Exception as e:
            self.logger.error(f"Error updating movie {movie_data.id}: {e}")
            return False

    def _insert_person(self, conn, person: PersonData, pending: bool = False) -> None:
        """Insert person into people table (ignores duplicates)."""
        table = "people_pending" if pending else "people"
        person_dict = person.to_dict()
        columns = ", ".join(person_dict.keys())
        placeholders = ", ".join(f":{k}" for k in person_dict.keys())
        conn.execute(
            text(f"INSERT IGNORE INTO {table} ({columns}) VALUES ({placeholders})"),
            person_dict
        )

    def _insert_credit(self, conn, movie_id: int, credit: CreditData, pending: bool = False) -> None:
        """Insert credit into credits table."""
        table = "credits_pending" if pending else "credits"
        credit_dict = credit.to_dict()
        credit_dict["movie_id"] = movie_id
        columns = ", ".join(credit_dict.keys())
        placeholders = ", ".join(f":{k}" for k in credit_dict.keys())
        try:
            conn.execute(
                text(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"),
                credit_dict
            )
        except IntegrityError:
            pass  # Duplicate credit, ignore

    # ============ PENDING TABLE OPERATIONS ============

    def get_pending_movie_ids(self) -> Set[int]:
        """Get all movie IDs from pending movies table."""
        result = self._execute("SELECT id FROM movies_pending")
        return {row[0] for row in result}

    def get_latest_pending_date(self) -> Optional[date]:
        """Get the most recent release_date from pending movies table."""
        result = self._execute(
            "SELECT MAX(release_date) FROM movies_pending WHERE release_date IS NOT NULL"
        )
        return result[0][0] if result and result[0][0] else None

    def pending_movie_exists(self, movie_id: int) -> bool:
        """Check if movie exists in pending table."""
        result = self._execute(
            "SELECT 1 FROM movies_pending WHERE id = :id LIMIT 1",
            {"id": movie_id}
        )
        return len(result) > 0

    def insert_pending_movie(self, movie_data: MovieData) -> bool:
        """Insert movie into pending tables."""
        try:
            with self.engine.connect() as conn:
                # Insert movie
                movie_dict = movie_data.to_dict()
                columns = ", ".join(movie_dict.keys())
                placeholders = ", ".join(f":{k}" for k in movie_dict.keys())
                conn.execute(
                    text(f"INSERT INTO movies_pending ({columns}) VALUES ({placeholders})"),
                    movie_dict
                )

                # Insert people (ignore duplicates)
                for person in movie_data.get_people():
                    self._insert_person(conn, person, pending=True)

                # Insert credits
                for credit in movie_data.credits:
                    self._insert_credit(conn, movie_data.id, credit, pending=True)

                # Insert genres
                for genre in movie_data.genres:
                    conn.execute(
                        text("INSERT IGNORE INTO genres_pending (movie_id, genre_name) VALUES (:movie_id, :genre_name)"),
                        {"movie_id": movie_data.id, "genre_name": genre}
                    )

                conn.commit()
                return True

        except IntegrityError as e:
            self.logger.warning(f"Duplicate pending movie {movie_data.id}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error inserting pending movie {movie_data.id}: {e}")
            return False

    def insert_pending_movies_batch(self, movies: List[MovieData]) -> int:
        """Batch insert movies into pending tables."""
        inserted = 0
        for movie in movies:
            if self.insert_pending_movie(movie):
                inserted += 1
        return inserted

    def get_pending_movie(self, movie_id: int) -> Optional[MovieData]:
        """Get full movie data from pending tables."""
        with self.engine.connect() as conn:
            # Get movie using named column access
            result = conn.execute(
                text("SELECT * FROM movies_pending WHERE id = :id"),
                {"id": movie_id}
            )
            row = result.mappings().fetchone()
            if not row:
                return None

            movie_dict = dict(row)

            # Get genres
            genres_result = conn.execute(
                text("SELECT genre_name FROM genres_pending WHERE movie_id = :id"),
                {"id": movie_id}
            )
            genres = [r["genre_name"] for r in genres_result.mappings()]

            # Get credits with named column access
            credits_result = conn.execute(
                text("""SELECT
                        c.person_id, c.credit_type, c.character_name,
                        c.credit_order, c.department, c.job,
                        p.name as person_name, p.profile_path, p.gender, p.known_for_department
                    FROM credits_pending c
                    LEFT JOIN people_pending p ON c.person_id = p.id
                    WHERE c.movie_id = :id"""),
                {"id": movie_id}
            )

            credits = []
            for cr in credits_result.mappings():
                credit = CreditData(
                    person_id=cr["person_id"],
                    person_name=cr["person_name"] or "Unknown",
                    credit_type=cr["credit_type"],
                    character_name=cr["character_name"],
                    credit_order=cr["credit_order"],
                    department=cr["department"],
                    job=cr["job"],
                    profile_path=cr["profile_path"],
                    gender=cr["gender"],
                    known_for_department=cr["known_for_department"],
                )
                credits.append(credit)

        # Parse origin_country from JSON
        origin_country = None
        if movie_dict.get("origin_country"):
            try:
                origin_country = json.loads(movie_dict["origin_country"]) if isinstance(movie_dict["origin_country"], str) else movie_dict["origin_country"]
            except (json.JSONDecodeError, TypeError):
                pass

        return MovieData(
            id=movie_dict["id"],
            title=movie_dict["title"],
            original_title=movie_dict.get("original_title"),
            overview=movie_dict.get("overview"),
            release_date=movie_dict.get("release_date"),
            runtime=movie_dict.get("runtime"),
            status=movie_dict.get("status"),
            tagline=movie_dict.get("tagline"),
            vote_average=movie_dict.get("vote_average"),
            vote_count=movie_dict.get("vote_count"),
            popularity=movie_dict.get("popularity"),
            poster_path=movie_dict.get("poster_path"),
            backdrop_path=movie_dict.get("backdrop_path"),
            budget=movie_dict.get("budget"),
            revenue=movie_dict.get("revenue"),
            imdb_id=movie_dict.get("imdb_id"),
            original_language=movie_dict.get("original_language"),
            origin_country=origin_country,
            english_name=movie_dict.get("english_name"),
            spoken_language_codes=movie_dict.get("spoken_language_codes"),
            genres=genres,
            credits=credits,
        )

    def get_pending_movies_ordered(
        self,
        oldest_first: bool = True,
        limit: Optional[int] = None
    ) -> List[MovieData]:
        """Get pending movies ordered by release_date."""
        order = "ASC" if oldest_first else "DESC"
        limit_clause = f"LIMIT {limit}" if limit else ""

        result = self._execute(
            f"SELECT id FROM movies_pending ORDER BY release_date {order} {limit_clause}"
        )

        movies = []
        for row in result:
            movie = self.get_pending_movie(row[0])
            if movie:
                movies.append(movie)
        return movies

    def search_pending_movies(self, query: str) -> List[MovieSearchResult]:
        """Search pending movies by title."""
        result = self._execute(
            """SELECT id, title, release_date, overview, popularity, vote_average, poster_path
               FROM movies_pending
               WHERE title LIKE :query
               ORDER BY popularity DESC
               LIMIT 20""",
            {"query": f"%{query}%"}
        )

        return [
            MovieSearchResult(
                id=r[0],
                title=r[1],
                release_date=str(r[2]) if r[2] else None,
                overview=r[3][:100] + "..." if r[3] and len(r[3]) > 100 else r[3],
                popularity=r[4],
                vote_average=r[5],
                poster_path=r[6],
                exists_in_pending=True,
            )
            for r in result
        ]

    def delete_pending_movie(self, movie_id: int) -> bool:
        """Delete movie from all pending tables."""
        try:
            with self.engine.connect() as conn:
                # Delete in correct order (foreign key considerations)
                conn.execute(
                    text("DELETE FROM credits_pending WHERE movie_id = :id"),
                    {"id": movie_id}
                )
                conn.execute(
                    text("DELETE FROM genres_pending WHERE movie_id = :id"),
                    {"id": movie_id}
                )
                conn.execute(
                    text("DELETE FROM movies_pending WHERE id = :id"),
                    {"id": movie_id}
                )
                # Note: We don't delete from people_pending as people may be shared
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error deleting pending movie {movie_id}: {e}")
            return False

    # ============ APPROVAL OPERATIONS ============

    def approve_movie(self, movie_id: int) -> bool:
        """
        Move single movie from pending to production.

        All operations happen in a SINGLE TRANSACTION to ensure atomicity.
        If any step fails, the entire operation is rolled back.

        Steps (in transaction):
        1. Get movie data from pending tables
        2. Insert into production tables
        3. Merge people (don't duplicate)
        4. Delete from pending tables
        """
        movie = self.get_pending_movie(movie_id)
        if not movie:
            self.logger.error(f"Movie {movie_id} not found in pending")
            return False

        try:
            # Use a single transaction for atomicity
            with self.engine.begin() as conn:
                # Step 1: Insert movie into production
                movie_dict = movie.to_dict()
                columns = ", ".join(movie_dict.keys())
                placeholders = ", ".join(f":{k}" for k in movie_dict.keys())
                conn.execute(
                    text(f"INSERT INTO movies ({columns}) VALUES ({placeholders})"),
                    movie_dict
                )

                # Step 2: Insert people (ignore duplicates)
                for person in movie.get_people():
                    person_dict = person.to_dict()
                    p_columns = ", ".join(person_dict.keys())
                    p_placeholders = ", ".join(f":{k}" for k in person_dict.keys())
                    conn.execute(
                        text(f"INSERT IGNORE INTO people ({p_columns}) VALUES ({p_placeholders})"),
                        person_dict
                    )

                # Step 3: Insert credits
                for credit in movie.credits:
                    credit_dict = credit.to_dict()
                    credit_dict["movie_id"] = movie_id
                    c_columns = ", ".join(credit_dict.keys())
                    c_placeholders = ", ".join(f":{k}" for k in credit_dict.keys())
                    try:
                        conn.execute(
                            text(f"INSERT INTO credits ({c_columns}) VALUES ({c_placeholders})"),
                            credit_dict
                        )
                    except IntegrityError:
                        pass  # Duplicate credit, ignore

                # Step 4: Insert genres
                for genre in movie.genres:
                    conn.execute(
                        text("INSERT IGNORE INTO genres (movie_id, genre_name) VALUES (:movie_id, :genre_name)"),
                        {"movie_id": movie_id, "genre_name": genre}
                    )

                # Step 5: Delete from pending tables (order matters for integrity)
                conn.execute(
                    text("DELETE FROM credits_pending WHERE movie_id = :id"),
                    {"id": movie_id}
                )
                conn.execute(
                    text("DELETE FROM genres_pending WHERE movie_id = :id"),
                    {"id": movie_id}
                )
                conn.execute(
                    text("DELETE FROM movies_pending WHERE id = :id"),
                    {"id": movie_id}
                )

            # Transaction committed successfully
            self.logger.info(f"Approved movie: {movie.title} ({movie_id})")
            return True

        except Exception as e:
            # Transaction automatically rolled back on exception
            self.logger.error(f"Error approving movie {movie_id}: {e}")
            return False

    # ============ SETUP OPERATIONS ============

    def table_exists(self, table_name: str) -> bool:
        """Check if a specific table exists."""
        result = self._execute(
            """SELECT COUNT(*) FROM information_schema.tables
               WHERE table_schema = :db AND table_name = :table""",
            {"db": self.config.db_name, "table": table_name}
        )
        return result[0][0] > 0

    def get_missing_tables(self) -> Tuple[List[str], List[str]]:
        """
        Get lists of required tables that don't exist.

        Returns:
            Tuple of (missing_production, missing_pending)
        """
        missing_production = [t for t in self.PRODUCTION_TABLES if not self.table_exists(t)]
        missing_pending = [t for t in self.PENDING_TABLES if not self.table_exists(t)]
        return missing_production, missing_pending

    def check_and_create_tables(self) -> dict:
        """
        Check which tables exist and create any that are missing.

        Returns:
            {
                "existing_production": List[str],
                "existing_pending": List[str],
                "created_production": List[str],
                "created_pending": List[str],
                "all_present": bool
            }
        """
        result = {
            "existing_production": [],
            "existing_pending": [],
            "created_production": [],
            "created_pending": [],
            "all_present": False,
        }

        # Check production tables
        for table in self.PRODUCTION_TABLES:
            if self.table_exists(table):
                result["existing_production"].append(table)
            else:
                if self._create_table(table, pending=False):
                    result["created_production"].append(table)

        # Check pending tables
        for table in self.PENDING_TABLES:
            if self.table_exists(table):
                result["existing_pending"].append(table)
            else:
                if self._create_table(table.replace("_pending", ""), pending=True):
                    result["created_pending"].append(table)

        # Check if all present
        total_existing = len(result["existing_production"]) + len(result["existing_pending"])
        total_created = len(result["created_production"]) + len(result["created_pending"])
        total_required = len(self.PRODUCTION_TABLES) + len(self.PENDING_TABLES)
        result["all_present"] = (total_existing + total_created) == total_required

        return result

    def _create_table(self, table_type: str, pending: bool = False) -> bool:
        """Create a specific table with its indexes."""
        suffix = "_pending" if pending else ""

        sql_templates = {
            "movies": f"""
                CREATE TABLE IF NOT EXISTS movies{suffix} (
                    id INT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    original_title VARCHAR(255),
                    overview TEXT,
                    release_date DATE,
                    runtime INT,
                    status VARCHAR(50),
                    tagline TEXT,
                    vote_average FLOAT,
                    vote_count INT,
                    popularity FLOAT,
                    poster_path VARCHAR(255),
                    backdrop_path VARCHAR(255),
                    budget BIGINT,
                    revenue BIGINT,
                    imdb_id VARCHAR(25),
                    original_language VARCHAR(25),
                    origin_country JSON,
                    english_name VARCHAR(255),
                    spoken_language_codes VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_{suffix.replace('_', '') if suffix else 'prod'}_movies_release_date (release_date),
                    INDEX idx_{suffix.replace('_', '') if suffix else 'prod'}_movies_title (title)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            "people": f"""
                CREATE TABLE IF NOT EXISTS people{suffix} (
                    id INT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    profile_path VARCHAR(255),
                    gender INT,
                    known_for_department VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_{suffix.replace('_', '') if suffix else 'prod'}_people_name (name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            "credits": f"""
                CREATE TABLE IF NOT EXISTS credits{suffix} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    movie_id INT NOT NULL,
                    person_id INT NOT NULL,
                    credit_type VARCHAR(50) NOT NULL,
                    character_name VARCHAR(255),
                    credit_order INT,
                    department VARCHAR(100),
                    job VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_{suffix.replace('_', '') if suffix else 'prod'}_credits_movie_id (movie_id),
                    INDEX idx_{suffix.replace('_', '') if suffix else 'prod'}_credits_person_id (person_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            "genres": f"""
                CREATE TABLE IF NOT EXISTS genres{suffix} (
                    movie_id INT NOT NULL,
                    genre_name VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (movie_id, genre_name),
                    INDEX idx_{suffix.replace('_', '') if suffix else 'prod'}_genres_movie_id (movie_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
        }

        try:
            self._execute(sql_templates[table_type])
            self.logger.info(f"Created table: {table_type}{suffix}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating table {table_type}{suffix}: {e}")
            return False

    def create_all_tables(self) -> None:
        """Create all production and pending tables with indexes."""
        for table in self.PRODUCTION_TABLES:
            if not self.table_exists(table):
                self._create_table(table, pending=False)

        for table in self.PENDING_TABLES:
            if not self.table_exists(table):
                base_table = table.replace("_pending", "")
                self._create_table(base_table, pending=True)

    def drop_all_movie_tables(self, confirm: bool = False) -> bool:
        """
        Drop all movie-related tables (production and pending).
        USE WITH CAUTION - this is destructive!
        """
        if not confirm:
            self.logger.warning("drop_all_movie_tables called without confirmation")
            return False

        tables_to_drop = [
            "credits", "credits_pending",
            "genres", "genres_pending",
            "movies", "movies_pending",
            "people", "people_pending",
        ]

        try:
            with self.engine.connect() as conn:
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                for table in tables_to_drop:
                    if self.table_exists(table):
                        conn.execute(text(f"DROP TABLE {table}"))
                        self.logger.info(f"Dropped table: {table}")
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error dropping tables: {e}")
            return False

    def drop_tables(self, drop_production: bool = True, drop_pending: bool = True) -> dict:
        """
        Drop specified movie tables.

        Args:
            drop_production: Drop production tables (movies, credits, genres, people)
            drop_pending: Drop pending tables (movies_pending, credits_pending, etc.)

        Returns:
            {"dropped": List[str], "errors": List[str]}
        """
        result = {"dropped": [], "errors": []}

        tables_to_drop = []
        if drop_production:
            # Order matters: credits/genres first (FK), then movies, then people
            tables_to_drop.extend(["credits", "genres", "movies", "people"])
        if drop_pending:
            tables_to_drop.extend(["credits_pending", "genres_pending", "movies_pending", "people_pending"])

        try:
            with self.engine.connect() as conn:
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                for table in tables_to_drop:
                    try:
                        if self.table_exists(table):
                            conn.execute(text(f"DROP TABLE {table}"))
                            result["dropped"].append(table)
                            self.logger.info(f"Dropped table: {table}")
                    except Exception as e:
                        result["errors"].append(f"{table}: {str(e)}")
                        self.logger.error(f"Error dropping table {table}: {e}")
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                conn.commit()
        except Exception as e:
            result["errors"].append(f"Connection error: {str(e)}")
            self.logger.error(f"Error in drop_tables: {e}")

        return result

    def get_status(self) -> dict:
        """Get current database status."""
        missing_prod, missing_pending = self.get_missing_tables()

        status = {
            "production_count": 0,
            "pending_count": 0,
            "latest_production_date": None,
            "latest_pending_date": None,
            "missing_production_tables": missing_prod,
            "missing_pending_tables": missing_pending,
            "all_tables_exist": len(missing_prod) == 0 and len(missing_pending) == 0,
        }

        if self.table_exists("movies"):
            status["production_count"] = self.get_production_count()
            latest = self.get_latest_movie_date()
            status["latest_production_date"] = str(latest) if latest else None

        if self.table_exists("movies_pending"):
            status["pending_count"] = self.get_pending_count()
            latest = self.get_latest_pending_date()
            status["latest_pending_date"] = str(latest) if latest else None

        return status

    # ============ API QUERY METHODS ============

    def get_movies_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "popularity",
        sort_order: str = "desc",
        genre: Optional[str] = None,
        year: Optional[int] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        min_rating: Optional[float] = None,
        min_votes: Optional[int] = None,
        language: Optional[str] = None,
    ) -> Tuple[List[dict], int]:
        """Get paginated movies with filtering and sorting."""
        # Build WHERE clauses
        where_clauses = []
        params = {}

        if genre:
            where_clauses.append("m.id IN (SELECT movie_id FROM genres WHERE genre_name = :genre)")
            params["genre"] = genre

        if year:
            where_clauses.append("YEAR(m.release_date) = :year")
            params["year"] = year

        if year_from:
            where_clauses.append("YEAR(m.release_date) >= :year_from")
            params["year_from"] = year_from

        if year_to:
            where_clauses.append("YEAR(m.release_date) <= :year_to")
            params["year_to"] = year_to

        if min_rating:
            where_clauses.append("m.vote_average >= :min_rating")
            params["min_rating"] = min_rating

        if min_votes:
            where_clauses.append("m.vote_count >= :min_votes")
            params["min_votes"] = min_votes

        if language:
            where_clauses.append("m.original_language = :language")
            params["language"] = language

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Validate sort_by
        valid_sort_fields = ["popularity", "release_date", "vote_average", "title", "revenue"]
        if sort_by not in valid_sort_fields:
            sort_by = "popularity"

        order_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM movies m WHERE {where_sql}"
        count_result = self._execute(count_query, params)
        total = count_result[0][0]

        # Get paginated results
        offset = (page - 1) * per_page
        params["offset"] = offset
        params["limit"] = per_page

        query = f"""
            SELECT m.id, m.title, m.original_title, m.overview, m.release_date,
                   m.runtime, m.vote_average, m.vote_count, m.popularity,
                   m.poster_path, m.backdrop_path,
                   (SELECT GROUP_CONCAT(genre_name) FROM genres WHERE movie_id = m.id) as genres
            FROM movies m
            WHERE {where_sql}
            ORDER BY m.{sort_by} {order_dir}
            LIMIT :limit OFFSET :offset
        """

        result = self._execute(query, params)

        movies = []
        for row in result:
            genres_str = row[11] or ""
            movies.append({
                "id": row[0],
                "title": row[1],
                "original_title": row[2],
                "overview": row[3],
                "release_date": row[4],
                "runtime": row[5],
                "vote_average": row[6],
                "vote_count": row[7],
                "popularity": row[8],
                "poster_path": row[9],
                "backdrop_path": row[10],
                "genres": genres_str.split(",") if genres_str else [],
            })

        return movies, total

    def get_movie_detail(self, movie_id: int) -> Optional[dict]:
        """Get full movie details with credits and genres."""
        # Get movie
        result = self._execute(
            "SELECT * FROM movies WHERE id = :id",
            {"id": movie_id}
        )
        if not result:
            return None

        with self.engine.connect() as conn:
            movie_result = conn.execute(
                text("SELECT * FROM movies WHERE id = :id"),
                {"id": movie_id}
            )
            row = movie_result.mappings().fetchone()
            if not row:
                return None

            movie = dict(row)

            # Get genres
            genres_result = conn.execute(
                text("SELECT genre_name FROM genres WHERE movie_id = :id"),
                {"id": movie_id}
            )
            movie["genres"] = [r["genre_name"] for r in genres_result.mappings()]

            # Get credits
            credits_result = conn.execute(
                text("""
                    SELECT c.person_id, c.credit_type, c.character_name,
                           c.credit_order, c.department, c.job,
                           p.name, p.profile_path, p.gender, p.known_for_department
                    FROM credits c
                    LEFT JOIN people p ON c.person_id = p.id
                    WHERE c.movie_id = :id
                    ORDER BY c.credit_order ASC
                """),
                {"id": movie_id}
            )

            cast = []
            crew = []
            for cr in credits_result.mappings():
                credit = {
                    "id": cr["person_id"],
                    "name": cr["name"],
                    "profile_path": cr["profile_path"],
                    "gender": cr["gender"],
                    "known_for_department": cr["known_for_department"],
                }
                if cr["credit_type"] == "cast":
                    credit["character"] = cr["character_name"]
                    credit["order"] = cr["credit_order"]
                    cast.append(credit)
                else:
                    credit["job"] = cr["job"]
                    credit["department"] = cr["department"]
                    crew.append(credit)

            movie["credits"] = {"cast": cast, "crew": crew}

            # Parse origin_country from JSON
            if movie.get("origin_country"):
                try:
                    if isinstance(movie["origin_country"], str):
                        movie["origin_country"] = json.loads(movie["origin_country"])
                except (json.JSONDecodeError, TypeError):
                    movie["origin_country"] = []

            return movie

    def get_movie_credits(
        self,
        movie_id: int,
        cast_limit: int = 20,
        crew_limit: int = 10
    ) -> Optional[dict]:
        """Get movie credits with limits."""
        # Check movie exists
        if not self.movie_exists(movie_id):
            return None

        with self.engine.connect() as conn:
            # Get cast count and limited cast
            cast_count_result = conn.execute(
                text("SELECT COUNT(*) FROM credits WHERE movie_id = :id AND credit_type = 'cast'"),
                {"id": movie_id}
            )
            cast_total = cast_count_result.fetchone()[0]

            cast_result = conn.execute(
                text("""
                    SELECT c.person_id, c.character_name, c.credit_order,
                           p.name, p.profile_path, p.gender, p.known_for_department
                    FROM credits c
                    LEFT JOIN people p ON c.person_id = p.id
                    WHERE c.movie_id = :id AND c.credit_type = 'cast'
                    ORDER BY c.credit_order ASC
                    LIMIT :limit
                """),
                {"id": movie_id, "limit": cast_limit}
            )

            cast = []
            for cr in cast_result.mappings():
                cast.append({
                    "id": cr["person_id"],
                    "name": cr["name"],
                    "character": cr["character_name"],
                    "order": cr["credit_order"],
                    "profile_path": cr["profile_path"],
                    "gender": cr["gender"],
                    "known_for_department": cr["known_for_department"],
                })

            # Get crew count and limited crew
            crew_count_result = conn.execute(
                text("SELECT COUNT(*) FROM credits WHERE movie_id = :id AND credit_type = 'crew'"),
                {"id": movie_id}
            )
            crew_total = crew_count_result.fetchone()[0]

            crew_result = conn.execute(
                text("""
                    SELECT c.person_id, c.department, c.job,
                           p.name, p.profile_path, p.gender, p.known_for_department
                    FROM credits c
                    LEFT JOIN people p ON c.person_id = p.id
                    WHERE c.movie_id = :id AND c.credit_type = 'crew'
                    LIMIT :limit
                """),
                {"id": movie_id, "limit": crew_limit}
            )

            crew = []
            for cr in crew_result.mappings():
                crew.append({
                    "id": cr["person_id"],
                    "name": cr["name"],
                    "job": cr["job"],
                    "department": cr["department"],
                    "profile_path": cr["profile_path"],
                    "gender": cr["gender"],
                    "known_for_department": cr["known_for_department"],
                })

            # Get director
            director_result = conn.execute(
                text("""
                    SELECT c.person_id, p.name, p.profile_path
                    FROM credits c
                    LEFT JOIN people p ON c.person_id = p.id
                    WHERE c.movie_id = :id AND c.job = 'Director'
                    LIMIT 1
                """),
                {"id": movie_id}
            )
            director_row = director_result.mappings().fetchone()
            director = None
            if director_row:
                director = {
                    "id": director_row["person_id"],
                    "name": director_row["name"],
                    "profile_path": director_row["profile_path"],
                }

            return {
                "movie_id": movie_id,
                "cast": cast,
                "cast_total": cast_total,
                "crew": crew,
                "crew_total": crew_total,
                "director": director,
            }

    def get_similar_movies(self, movie_id: int, limit: int = 10) -> List[dict]:
        """Get similar movies based on shared genres."""
        # Get source movie genres
        genres_result = self._execute(
            "SELECT genre_name FROM genres WHERE movie_id = :id",
            {"id": movie_id}
        )
        if not genres_result:
            return []

        source_genres = [r[0] for r in genres_result]
        if not source_genres:
            return []

        # Find movies with most shared genres
        placeholders = ", ".join([f":g{i}" for i in range(len(source_genres))])
        params = {"movie_id": movie_id, "limit": limit}
        for i, g in enumerate(source_genres):
            params[f"g{i}"] = g

        query = f"""
            SELECT m.id, m.title, m.poster_path, m.vote_average, m.release_date,
                   COUNT(g.genre_name) as shared_genres,
                   (SELECT GROUP_CONCAT(genre_name) FROM genres WHERE movie_id = m.id) as genres
            FROM movies m
            JOIN genres g ON m.id = g.movie_id
            WHERE g.genre_name IN ({placeholders})
              AND m.id != :movie_id
            GROUP BY m.id
            ORDER BY shared_genres DESC, m.vote_average DESC
            LIMIT :limit
        """

        result = self._execute(query, params)

        similar = []
        for row in result:
            genres_str = row[6] or ""
            similar.append({
                "id": row[0],
                "title": row[1],
                "poster_path": row[2],
                "vote_average": row[3],
                "release_date": row[4],
                "genres": genres_str.split(",") if genres_str else [],
                "similarity_score": row[5] / len(source_genres) if source_genres else 0,
            })

        return similar

    def get_people_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        department: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[dict], int]:
        """Get paginated people with movie counts."""
        where_clauses = []
        params = {}

        if department:
            where_clauses.append("p.known_for_department = :department")
            params["department"] = department

        if search:
            where_clauses.append("p.name LIKE :search")
            params["search"] = f"%{search}%"

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM people p WHERE {where_sql}"
        count_result = self._execute(count_query, params)
        total = count_result[0][0]

        # Get paginated results
        offset = (page - 1) * per_page
        params["offset"] = offset
        params["limit"] = per_page

        query = f"""
            SELECT p.id, p.name, p.profile_path, p.gender, p.known_for_department,
                   (SELECT COUNT(DISTINCT movie_id) FROM credits WHERE person_id = p.id) as movie_count
            FROM people p
            WHERE {where_sql}
            ORDER BY movie_count DESC
            LIMIT :limit OFFSET :offset
        """

        result = self._execute(query, params)

        people = []
        for row in result:
            people.append({
                "id": row[0],
                "name": row[1],
                "profile_path": row[2],
                "gender": row[3],
                "known_for_department": row[4],
                "movie_count": row[5],
            })

        return people, total

    def get_person_detail(self, person_id: int) -> Optional[dict]:
        """Get person details with filmography."""
        # Get person
        result = self._execute(
            "SELECT * FROM people WHERE id = :id",
            {"id": person_id}
        )
        if not result:
            return None

        with self.engine.connect() as conn:
            person_result = conn.execute(
                text("SELECT * FROM people WHERE id = :id"),
                {"id": person_id}
            )
            row = person_result.mappings().fetchone()
            if not row:
                return None

            person = dict(row)

            # Get filmography
            filmography_result = conn.execute(
                text("""
                    SELECT c.movie_id, m.title, m.release_date, m.poster_path, m.vote_average,
                           c.credit_type, c.character_name, c.job, c.department
                    FROM credits c
                    JOIN movies m ON c.movie_id = m.id
                    WHERE c.person_id = :id
                    ORDER BY m.release_date DESC
                """),
                {"id": person_id}
            )

            cast_films = []
            crew_films = []
            for f in filmography_result.mappings():
                film = {
                    "movie_id": f["movie_id"],
                    "title": f["title"],
                    "release_date": f["release_date"],
                    "poster_path": f["poster_path"],
                    "vote_average": f["vote_average"],
                }
                if f["credit_type"] == "cast":
                    film["character"] = f["character_name"]
                    film["credit_type"] = "cast"
                    cast_films.append(film)
                else:
                    film["job"] = f["job"]
                    film["department"] = f["department"]
                    film["credit_type"] = "crew"
                    crew_films.append(film)

            person["filmography"] = {"cast": cast_films, "crew": crew_films}

            # Calculate stats
            total_movies = len(set([f["movie_id"] for f in cast_films + crew_films]))
            all_ratings = [f["vote_average"] for f in cast_films + crew_films if f["vote_average"]]
            avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else None

            person["stats"] = {
                "total_movies": total_movies,
                "as_cast": len(cast_films),
                "as_crew": len(crew_films),
                "average_movie_rating": round(avg_rating, 2) if avg_rating else None,
            }

            return person

    def get_person_movies_paginated(
        self,
        person_id: int,
        page: int = 1,
        per_page: int = 20,
        credit_type: Optional[str] = None,
        sort_by: str = "release_date",
    ) -> Tuple[List[dict], int, str]:
        """Get paginated filmography for a person."""
        # Get person name
        person_result = self._execute(
            "SELECT name FROM people WHERE id = :id",
            {"id": person_id}
        )
        if not person_result:
            return [], 0, ""

        person_name = person_result[0][0]

        where_clauses = ["c.person_id = :person_id"]
        params = {"person_id": person_id}

        if credit_type:
            where_clauses.append("c.credit_type = :credit_type")
            params["credit_type"] = credit_type

        where_sql = " AND ".join(where_clauses)

        # Valid sort fields
        valid_sort = ["release_date", "popularity", "vote_average"]
        if sort_by not in valid_sort:
            sort_by = "release_date"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM credits c WHERE {where_sql}"
        count_result = self._execute(count_query, params)
        total = count_result[0][0]

        # Get paginated results
        offset = (page - 1) * per_page
        params["offset"] = offset
        params["limit"] = per_page

        query = f"""
            SELECT c.movie_id, m.title, m.release_date, m.poster_path, m.vote_average,
                   c.credit_type, c.character_name, c.job, c.department
            FROM credits c
            JOIN movies m ON c.movie_id = m.id
            WHERE {where_sql}
            ORDER BY m.{sort_by} DESC
            LIMIT :limit OFFSET :offset
        """

        result = self._execute(query, params)

        movies = []
        for row in result:
            movies.append({
                "movie_id": row[0],
                "title": row[1],
                "release_date": row[2],
                "poster_path": row[3],
                "vote_average": row[4],
                "credit_type": row[5],
                "character": row[6],
                "job": row[7],
                "department": row[8],
            })

        return movies, total, person_name

    def get_all_genres_with_counts(self) -> List[dict]:
        """Get all genres with movie counts."""
        result = self._execute("""
            SELECT genre_name, COUNT(DISTINCT movie_id) as movie_count
            FROM genres
            GROUP BY genre_name
            ORDER BY movie_count DESC
        """)

        return [{"name": row[0], "movie_count": row[1]} for row in result]

    def get_movies_by_genre(
        self,
        genre_name: str,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "popularity",
        sort_order: str = "desc",
        year: Optional[int] = None,
        min_rating: Optional[float] = None,
    ) -> Tuple[List[dict], int]:
        """Get movies for a specific genre."""
        where_clauses = ["g.genre_name = :genre_name"]
        params = {"genre_name": genre_name}

        if year:
            where_clauses.append("YEAR(m.release_date) = :year")
            params["year"] = year

        if min_rating:
            where_clauses.append("m.vote_average >= :min_rating")
            params["min_rating"] = min_rating

        where_sql = " AND ".join(where_clauses)

        valid_sort = ["popularity", "release_date", "vote_average", "title"]
        if sort_by not in valid_sort:
            sort_by = "popularity"

        order_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

        # Get total count
        count_query = f"""
            SELECT COUNT(DISTINCT m.id)
            FROM movies m
            JOIN genres g ON m.id = g.movie_id
            WHERE {where_sql}
        """
        count_result = self._execute(count_query, params)
        total = count_result[0][0]

        # Get paginated results
        offset = (page - 1) * per_page
        params["offset"] = offset
        params["limit"] = per_page

        query = f"""
            SELECT m.id, m.title, m.release_date, m.vote_average, m.popularity, m.poster_path
            FROM movies m
            JOIN genres g ON m.id = g.movie_id
            WHERE {where_sql}
            ORDER BY m.{sort_by} {order_dir}
            LIMIT :limit OFFSET :offset
        """

        result = self._execute(query, params)

        movies = []
        for row in result:
            movies.append({
                "id": row[0],
                "title": row[1],
                "release_date": row[2],
                "vote_average": row[3],
                "popularity": row[4],
                "poster_path": row[5],
            })

        return movies, total

    def search_movies_fulltext(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        genre: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        min_rating: Optional[float] = None,
        search_in: str = "title",
    ) -> Tuple[List[dict], int]:
        """Search movies with full-text or LIKE search."""
        where_clauses = []
        params = {"query": f"%{query}%"}

        if search_in == "title":
            where_clauses.append("m.title LIKE :query")
        elif search_in == "overview":
            where_clauses.append("m.overview LIKE :query")
        else:  # both
            where_clauses.append("(m.title LIKE :query OR m.overview LIKE :query)")

        if genre:
            where_clauses.append("m.id IN (SELECT movie_id FROM genres WHERE genre_name = :genre)")
            params["genre"] = genre

        if year_from:
            where_clauses.append("YEAR(m.release_date) >= :year_from")
            params["year_from"] = year_from

        if year_to:
            where_clauses.append("YEAR(m.release_date) <= :year_to")
            params["year_to"] = year_to

        if min_rating:
            where_clauses.append("m.vote_average >= :min_rating")
            params["min_rating"] = min_rating

        where_sql = " AND ".join(where_clauses)

        # Get total count
        count_query = f"SELECT COUNT(*) FROM movies m WHERE {where_sql}"
        count_result = self._execute(count_query, params)
        total = count_result[0][0]

        # Get paginated results
        offset = (page - 1) * per_page
        params["offset"] = offset
        params["limit"] = per_page

        query_sql = f"""
            SELECT m.id, m.title, m.original_title, m.overview, m.release_date,
                   m.vote_average, m.popularity, m.poster_path,
                   (SELECT GROUP_CONCAT(genre_name) FROM genres WHERE movie_id = m.id) as genres
            FROM movies m
            WHERE {where_sql}
            ORDER BY m.popularity DESC
            LIMIT :limit OFFSET :offset
        """

        result = self._execute(query_sql, params)

        movies = []
        for row in result:
            genres_str = row[8] or ""
            movies.append({
                "id": row[0],
                "title": row[1],
                "original_title": row[2],
                "overview": row[3],
                "release_date": row[4],
                "vote_average": row[5],
                "popularity": row[6],
                "poster_path": row[7],
                "genres": genres_str.split(",") if genres_str else [],
            })

        return movies, total

    def search_people(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        department: Optional[str] = None,
    ) -> Tuple[List[dict], int]:
        """Search people by name."""
        where_clauses = ["p.name LIKE :query"]
        params = {"query": f"%{query}%"}

        if department:
            where_clauses.append("p.known_for_department = :department")
            params["department"] = department

        where_sql = " AND ".join(where_clauses)

        # Get total count
        count_query = f"SELECT COUNT(*) FROM people p WHERE {where_sql}"
        count_result = self._execute(count_query, params)
        total = count_result[0][0]

        # Get paginated results
        offset = (page - 1) * per_page
        params["offset"] = offset
        params["limit"] = per_page

        query_sql = f"""
            SELECT p.id, p.name, p.profile_path, p.known_for_department,
                   (SELECT COUNT(DISTINCT movie_id) FROM credits WHERE person_id = p.id) as movie_count
            FROM people p
            WHERE {where_sql}
            ORDER BY movie_count DESC
            LIMIT :limit OFFSET :offset
        """

        result = self._execute(query_sql, params)

        people = []
        for row in result:
            people.append({
                "id": row[0],
                "name": row[1],
                "profile_path": row[2],
                "known_for_department": row[3],
                "movie_count": row[4],
            })

        return people, total

    def get_trending_movies(
        self,
        limit: int = 20,
        time_window: str = "week",
    ) -> List[dict]:
        """Get trending movies by popularity."""
        # For now, we use popularity as the trending metric
        # In a full implementation, you might track daily/weekly popularity changes

        date_filter = ""
        params = {"limit": limit}

        if time_window == "day":
            date_filter = "AND m.release_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
        elif time_window == "week":
            date_filter = "AND m.release_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)"
        elif time_window == "month":
            date_filter = "AND m.release_date >= DATE_SUB(CURDATE(), INTERVAL 180 DAY)"

        query = f"""
            SELECT m.id, m.title, m.poster_path, m.backdrop_path, m.vote_average,
                   m.popularity, m.release_date,
                   (SELECT GROUP_CONCAT(genre_name) FROM genres WHERE movie_id = m.id) as genres
            FROM movies m
            WHERE m.popularity IS NOT NULL {date_filter}
            ORDER BY m.popularity DESC
            LIMIT :limit
        """

        result = self._execute(query, params)

        movies = []
        for row in result:
            genres_str = row[7] or ""
            movies.append({
                "id": row[0],
                "title": row[1],
                "poster_path": row[2],
                "backdrop_path": row[3],
                "vote_average": row[4],
                "popularity": row[5],
                "release_date": row[6],
                "genres": genres_str.split(",") if genres_str else [],
            })

        return movies

    def get_top_rated_movies(
        self,
        limit: int = 20,
        min_votes: int = 1000,
        genre: Optional[str] = None,
    ) -> List[dict]:
        """Get highest rated movies with minimum vote threshold."""
        where_clauses = ["m.vote_count >= :min_votes"]
        params = {"min_votes": min_votes, "limit": limit}

        if genre:
            where_clauses.append("m.id IN (SELECT movie_id FROM genres WHERE genre_name = :genre)")
            params["genre"] = genre

        where_sql = " AND ".join(where_clauses)

        query = f"""
            SELECT m.id, m.title, m.poster_path, m.vote_average, m.vote_count,
                   m.release_date,
                   (SELECT GROUP_CONCAT(genre_name) FROM genres WHERE movie_id = m.id) as genres
            FROM movies m
            WHERE {where_sql}
            ORDER BY m.vote_average DESC
            LIMIT :limit
        """

        result = self._execute(query, params)

        movies = []
        for row in result:
            genres_str = row[6] or ""
            movies.append({
                "id": row[0],
                "title": row[1],
                "poster_path": row[2],
                "vote_average": row[3],
                "vote_count": row[4],
                "release_date": row[5],
                "genres": genres_str.split(",") if genres_str else [],
            })

        return movies

    def get_new_releases(
        self,
        limit: int = 20,
        days: int = 30,
        min_rating: Optional[float] = None,
    ) -> Tuple[List[dict], date, date]:
        """Get recently released movies."""
        where_clauses = [
            "m.release_date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)",
            "m.release_date <= CURDATE()"
        ]
        params = {"days": days, "limit": limit}

        if min_rating:
            where_clauses.append("m.vote_average >= :min_rating")
            params["min_rating"] = min_rating

        where_sql = " AND ".join(where_clauses)

        query = f"""
            SELECT m.id, m.title, m.poster_path, m.vote_average, m.release_date,
                   (SELECT GROUP_CONCAT(genre_name) FROM genres WHERE movie_id = m.id) as genres
            FROM movies m
            WHERE {where_sql}
            ORDER BY m.release_date DESC
            LIMIT :limit
        """

        result = self._execute(query, params)

        movies = []
        for row in result:
            genres_str = row[5] or ""
            movies.append({
                "id": row[0],
                "title": row[1],
                "poster_path": row[2],
                "vote_average": row[3],
                "release_date": row[4],
                "genres": genres_str.split(",") if genres_str else [],
            })

        # Calculate date range
        from datetime import timedelta
        today = date.today()
        from_date = today - timedelta(days=days)

        return movies, from_date, today

    def get_upcoming_movies(
        self,
        limit: int = 20,
        days: int = 60,
    ) -> Tuple[List[dict], date, date]:
        """Get movies releasing in the future."""
        params = {"days": days, "limit": limit}

        query = """
            SELECT m.id, m.title, m.poster_path, m.release_date,
                   (SELECT GROUP_CONCAT(genre_name) FROM genres WHERE movie_id = m.id) as genres
            FROM movies m
            WHERE m.release_date > CURDATE()
              AND m.release_date <= DATE_ADD(CURDATE(), INTERVAL :days DAY)
            ORDER BY m.release_date ASC
            LIMIT :limit
        """

        result = self._execute(query, params)

        movies = []
        for row in result:
            genres_str = row[4] or ""
            movies.append({
                "id": row[0],
                "title": row[1],
                "poster_path": row[2],
                "release_date": row[3],
                "genres": genres_str.split(",") if genres_str else [],
            })

        # Calculate date range
        from datetime import timedelta
        today = date.today()
        to_date = today + timedelta(days=days)

        return movies, today, to_date

    def get_movies_by_decade(
        self,
        decade: str,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "vote_average",
    ) -> Tuple[List[dict], int, int, int]:
        """Get movies from a specific decade."""
        # Parse decade (e.g., "1990s" -> 1990-1999)
        try:
            start_year = int(decade.replace("s", ""))
            end_year = start_year + 9
        except ValueError:
            return [], 0, 0, 0

        params = {
            "start_year": start_year,
            "end_year": end_year,
        }

        valid_sort = ["vote_average", "popularity", "release_date"]
        if sort_by not in valid_sort:
            sort_by = "vote_average"

        # Get total count
        count_query = """
            SELECT COUNT(*)
            FROM movies m
            WHERE YEAR(m.release_date) BETWEEN :start_year AND :end_year
        """
        count_result = self._execute(count_query, params)
        total = count_result[0][0]

        # Get paginated results
        offset = (page - 1) * per_page
        params["offset"] = offset
        params["limit"] = per_page

        query = f"""
            SELECT m.id, m.title, m.poster_path, m.vote_average, m.popularity,
                   m.release_date,
                   (SELECT GROUP_CONCAT(genre_name) FROM genres WHERE movie_id = m.id) as genres
            FROM movies m
            WHERE YEAR(m.release_date) BETWEEN :start_year AND :end_year
            ORDER BY m.{sort_by} DESC
            LIMIT :limit OFFSET :offset
        """

        result = self._execute(query, params)

        movies = []
        for row in result:
            genres_str = row[6] or ""
            movies.append({
                "id": row[0],
                "title": row[1],
                "poster_path": row[2],
                "vote_average": row[3],
                "popularity": row[4],
                "release_date": row[5],
                "genres": genres_str.split(",") if genres_str else [],
            })

        return movies, total, start_year, end_year

    # ============ PENDING API METHODS ============

    def get_pending_movies_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: Optional[str] = None,
        movie_id: Optional[int] = None,
    ) -> Tuple[List[dict], int]:
        """Get paginated pending movies with search."""
        where_clauses = []
        params = {}

        if movie_id:
            where_clauses.append("m.id = :movie_id")
            params["movie_id"] = movie_id
        elif search:
            where_clauses.append("m.title LIKE :search")
            params["search"] = f"%{search}%"

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        valid_sort = ["created_at", "release_date", "popularity", "title"]
        if sort_by not in valid_sort:
            sort_by = "created_at"

        order_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM movies_pending m WHERE {where_sql}"
        count_result = self._execute(count_query, params)
        total = count_result[0][0]

        # Get paginated results
        offset = (page - 1) * per_page
        params["offset"] = offset
        params["limit"] = per_page

        query = f"""
            SELECT m.id, m.title, m.original_title, m.overview, m.release_date,
                   m.runtime, m.vote_average, m.vote_count, m.popularity,
                   m.poster_path, m.backdrop_path, m.created_at,
                   (SELECT GROUP_CONCAT(genre_name) FROM genres_pending WHERE movie_id = m.id) as genres
            FROM movies_pending m
            WHERE {where_sql}
            ORDER BY m.{sort_by} {order_dir}
            LIMIT :limit OFFSET :offset
        """

        result = self._execute(query, params)

        movies = []
        for row in result:
            movie_id_val = row[0]

            # Get director
            director_result = self._execute("""
                SELECT c.person_id, p.name, p.profile_path
                FROM credits_pending c
                LEFT JOIN people_pending p ON c.person_id = p.id
                WHERE c.movie_id = :movie_id AND c.job = 'Director'
                LIMIT 1
            """, {"movie_id": movie_id_val})

            director = None
            if director_result:
                director = {
                    "id": director_result[0][0],
                    "name": director_result[0][1],
                    "profile_path": director_result[0][2],
                }

            # Get cast preview (first 3)
            cast_result = self._execute("""
                SELECT c.person_id, p.name, c.character_name
                FROM credits_pending c
                LEFT JOIN people_pending p ON c.person_id = p.id
                WHERE c.movie_id = :movie_id AND c.credit_type = 'cast'
                ORDER BY c.credit_order ASC
                LIMIT 3
            """, {"movie_id": movie_id_val})

            cast_preview = [
                {"id": r[0], "name": r[1], "character": r[2]}
                for r in cast_result
            ]

            genres_str = row[12] or ""
            movies.append({
                "id": row[0],
                "title": row[1],
                "original_title": row[2],
                "overview": row[3],
                "release_date": row[4],
                "runtime": row[5],
                "vote_average": row[6],
                "vote_count": row[7],
                "popularity": row[8],
                "poster_path": row[9],
                "backdrop_path": row[10],
                "created_at": row[11],
                "genres": genres_str.split(",") if genres_str else [],
                "director": director,
                "cast_preview": cast_preview,
            })

        return movies, total

    def approve_movies_bulk(self, movie_ids: List[int]) -> dict:
        """Approve multiple movies."""
        approved = []
        failed = []

        for movie_id in movie_ids:
            if self.movie_exists(movie_id):
                failed.append({
                    "movie_id": movie_id,
                    "error": "already_exists",
                })
            elif self.approve_movie(movie_id):
                approved.append(movie_id)
            else:
                failed.append({
                    "movie_id": movie_id,
                    "error": "approval_failed",
                })

        return {
            "approved": approved,
            "failed": failed,
        }

    def delete_pending_movies_bulk(self, movie_ids: List[int]) -> List[int]:
        """Delete multiple pending movies."""
        deleted = []
        for movie_id in movie_ids:
            if self.delete_pending_movie(movie_id):
                deleted.append(movie_id)
        return deleted

    def approve_all_pending(self) -> dict:
        """Approve all pending movies."""
        pending_ids = list(self.get_pending_movie_ids())
        return self.approve_movies_bulk(pending_ids)

    def delete_all_pending(self) -> int:
        """Delete all pending movies."""
        pending_ids = list(self.get_pending_movie_ids())
        deleted = self.delete_pending_movies_bulk(pending_ids)
        return len(deleted)

    def get_people_count(self) -> int:
        """Get count of people in production table."""
        result = self._execute("SELECT COUNT(*) FROM people")
        return result[0][0]

    def get_credits_count(self) -> int:
        """Get count of credits in production table."""
        result = self._execute("SELECT COUNT(*) FROM credits")
        return result[0][0]

    def get_genres_distribution(self) -> dict:
        """Get genre distribution."""
        result = self._execute("""
            SELECT genre_name, COUNT(*) as count
            FROM genres
            GROUP BY genre_name
            ORDER BY count DESC
            LIMIT 10
        """)
        return {row[0]: row[1] for row in result}

    def get_movies_by_decade_stats(self) -> dict:
        """Get movies count by decade."""
        result = self._execute("""
            SELECT CONCAT(FLOOR(YEAR(release_date) / 10) * 10, 's') as decade,
                   COUNT(*) as count
            FROM movies
            WHERE release_date IS NOT NULL
            GROUP BY decade
            ORDER BY decade DESC
        """)
        return {row[0]: row[1] for row in result}

    def get_oldest_pending_date(self) -> Optional[str]:
        """Get the oldest created_at from pending movies."""
        result = self._execute(
            "SELECT MIN(created_at) FROM movies_pending"
        )
        return str(result[0][0]) if result and result[0][0] else None

    def get_newest_pending_date(self) -> Optional[str]:
        """Get the newest created_at from pending movies."""
        result = self._execute(
            "SELECT MAX(created_at) FROM movies_pending"
        )
        return str(result[0][0]) if result and result[0][0] else None
