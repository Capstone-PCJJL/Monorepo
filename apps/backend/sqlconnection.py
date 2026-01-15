from dotenv import load_dotenv
import os
from pathlib import Path
from sqlalchemy import create_engine

def create_db_engine():
    # Try monorepo root first, then current directory
    root_env = Path(__file__).parent.parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

    SQL_HOST = os.getenv("SQL_HOST")
    SQL_PORT = os.getenv("SQL_PORT")
    SQL_USER = os.getenv("SQL_USER")
    SQL_PASS = os.getenv("SQL_PASS")
    SQL_DB   = os.getenv("SQL_DB")

    DATABASE_URL = f"mysql+pymysql://{SQL_USER}:{SQL_PASS}@{SQL_HOST}:{SQL_PORT}/{SQL_DB}"

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("✅ Successful connection")

    return engine
