"""
Configuration management for TMDB Pipeline.

Loads configuration from environment variables and provides
a centralized Config dataclass for all settings.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Centralized configuration from environment variables."""

    # TMDB API
    api_key: str
    bearer_token: str
    base_url: str = "https://api.themoviedb.org/3"

    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = ""
    db_password: str = ""
    db_name: str = ""

    # Pipeline settings
    batch_size: int = 100
    max_workers: int = 10
    rate_limit_per_second: int = 40

    # Paths
    project_dir: Path = field(default_factory=Path.cwd)
    log_dir: Path = field(default_factory=lambda: Path.cwd() / "tmdb_pipeline" / "logs")

    # Content filtering
    include_adult: bool = False

    # Credits settings
    max_cast_members: int = 8  # Top N cast members to store
    include_director: bool = True  # Always include director from crew

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False

    # JWT settings
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Admin credentials
    admin_username: str = "admin"
    admin_password_hash: str = ""

    # CORS settings
    allowed_origins: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls, env_path: Optional[str] = None) -> "Config":
        """
        Load configuration from environment variables.

        Args:
            env_path: Optional path to .env file. If not provided,
                     looks for .env in monorepo root, then current directory.

        Returns:
            Config instance with loaded values.

        Raises:
            ValueError: If required environment variables are missing.
        """
        # Load .env file
        if env_path:
            load_dotenv(env_path)
        else:
            # Try monorepo root first (../../.env from this file)
            root_env = Path(__file__).parent.parent.parent.parent / ".env"
            if root_env.exists():
                load_dotenv(root_env)
            else:
                load_dotenv()  # Fall back to current directory

        # Required variables
        api_key = os.getenv("API_KEY")
        bearer_token = os.getenv("TMDB_BEARER_TOKEN")

        if not api_key:
            raise ValueError("API_KEY environment variable is required")
        if not bearer_token:
            raise ValueError("TMDB_BEARER_TOKEN environment variable is required")

        # Database config
        db_host = os.getenv("SQL_HOST", "localhost")
        db_port = int(os.getenv("SQL_PORT", "3306"))
        db_user = os.getenv("SQL_USER", "")
        db_password = os.getenv("SQL_PASS", "")
        db_name = os.getenv("SQL_DB", "")

        if not db_user or not db_name:
            raise ValueError("SQL_USER and SQL_DB environment variables are required")

        # Optional settings
        base_url = os.getenv("BASE_URL", "https://api.themoviedb.org/3")
        project_dir = Path(os.getenv("PROJECT_DIR", Path.cwd()))

        # API settings
        api_host = os.getenv("API_HOST", "0.0.0.0")
        api_port = int(os.getenv("API_PORT", "8000"))
        api_debug = os.getenv("API_DEBUG", "false").lower() == "true"

        # JWT settings
        jwt_secret_key = os.getenv("JWT_SECRET_KEY", "")
        jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

        # Admin credentials
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")

        # CORS settings
        origins_str = os.getenv("ALLOWED_ORIGINS", "")
        allowed_origins = [o.strip() for o in origins_str.split(",") if o.strip()]

        return cls(
            api_key=api_key,
            bearer_token=bearer_token,
            base_url=base_url,
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            db_password=db_password,
            db_name=db_name,
            project_dir=project_dir,
            log_dir=project_dir / "tmdb_pipeline" / "logs",
            api_host=api_host,
            api_port=api_port,
            api_debug=api_debug,
            jwt_secret_key=jwt_secret_key,
            jwt_algorithm=jwt_algorithm,
            jwt_expire_minutes=jwt_expire_minutes,
            admin_username=admin_username,
            admin_password_hash=admin_password_hash,
            allowed_origins=allowed_origins,
        )

    def get_db_url(self) -> str:
        """Get SQLAlchemy database URL."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def get_headers(self) -> dict:
        """Get headers for TMDB API requests."""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
