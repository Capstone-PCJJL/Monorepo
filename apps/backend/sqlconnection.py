from dotenv import load_dotenv
import os
from pathlib import Path
from sqlalchemy import create_engine


def get_db_config():
    """Get database configuration based on DB_MODE (local or remote)."""
    db_mode = os.getenv("DB_MODE", "local").lower()

    if db_mode == "remote":
        # Use REMOTE_SQL_* variables (AWS RDS)
        return {
            "host": os.getenv("REMOTE_SQL_HOST", os.getenv("SQL_HOST", "localhost")),
            "port": os.getenv("REMOTE_SQL_PORT", os.getenv("SQL_PORT", "3306")),
            "user": os.getenv("REMOTE_SQL_USER", os.getenv("SQL_USER", "")),
            "password": os.getenv("REMOTE_SQL_PASS", os.getenv("SQL_PASS", "")),
            "database": os.getenv("REMOTE_SQL_DB", os.getenv("SQL_DB", "")),
        }
    else:
        # Use LOCAL_SQL_* variables (Docker MySQL) - default
        return {
            "host": os.getenv("LOCAL_SQL_HOST", os.getenv("SQL_HOST", "localhost")),
            "port": os.getenv("LOCAL_SQL_PORT", os.getenv("SQL_PORT", "3306")),
            "user": os.getenv("LOCAL_SQL_USER", os.getenv("SQL_USER", "root")),
            "password": os.getenv("LOCAL_SQL_PASS", os.getenv("SQL_PASS", "password")),
            "database": os.getenv("LOCAL_SQL_DB", os.getenv("SQL_DB", "tmdb")),
        }


def create_db_engine():
    # Try monorepo root first, then current directory
    root_env = Path(__file__).parent.parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

    config = get_db_config()
    db_mode = os.getenv("DB_MODE", "local").lower()

    DATABASE_URL = (
        f"mysql+pymysql://{config['user']}:{config['password']}"
        f"@{config['host']}:{config['port']}/{config['database']}"
    )

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print(f"✅ Connected to database ({db_mode} mode): {config['host']}")

    return engine
