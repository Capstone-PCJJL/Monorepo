#!/usr/bin/env python3
"""
Seed local MySQL from AWS RDS.

This script is called by Docker on first run to populate the local database
with a subset of movies from the production AWS RDS database.

Data persistence strategy:
- After seeding from remote, dumps the database to a local SQL file
- On subsequent runs, restores from local dump (skips AWS RDS call)
- Use --force to re-fetch from remote and update the local dump

Usage:
    python scripts/seed_from_remote.py              # Default 5,000 movies
    python scripts/seed_from_remote.py --limit 1000 # Custom limit
    python scripts/seed_from_remote.py --force      # Force re-fetch from AWS
"""

import argparse
import gzip
import os
import subprocess
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pymysql
from dotenv import load_dotenv

# Local backup directory and file
DATA_DIR = Path(__file__).parent.parent / "data"
DUMP_FILE = DATA_DIR / "seed_backup.sql.gz"


def get_db_config(mode: str) -> dict:
    """Get database config for local or remote."""
    if mode == "remote":
        return {
            "host": os.getenv("REMOTE_SQL_HOST"),
            "port": int(os.getenv("REMOTE_SQL_PORT", "3306")),
            "user": os.getenv("REMOTE_SQL_USER"),
            "password": os.getenv("REMOTE_SQL_PASS"),
            "database": os.getenv("REMOTE_SQL_DB"),
        }
    else:
        return {
            "host": os.getenv("LOCAL_SQL_HOST", "localhost"),
            "port": int(os.getenv("LOCAL_SQL_PORT", "3306")),
            "user": os.getenv("LOCAL_SQL_USER", "root"),
            "password": os.getenv("LOCAL_SQL_PASS", "password"),
            "database": os.getenv("LOCAL_SQL_DB", "tmdb"),
        }


def wait_for_db(config: dict, max_retries: int = 30, delay: int = 2) -> bool:
    """Wait for database to be ready."""
    for i in range(max_retries):
        try:
            conn = pymysql.connect(**config)
            conn.close()
            return True
        except pymysql.Error:
            print(f"Waiting for database... ({i + 1}/{max_retries})")
            time.sleep(delay)
    return False


def get_movie_count(config: dict) -> int:
    """Get count of movies in database. Returns -1 if table doesn't exist."""
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM movies")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except pymysql.Error:
        return -1


def dump_database(config: dict) -> bool:
    """Dump local database to compressed SQL file."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\nBacking up database to {DUMP_FILE}...")
        print(f"DATA_DIR: {DATA_DIR}")

        cmd = [
            "mysqldump",
            f"--host={config['host']}",
            f"--port={config['port']}",
            f"--user={config['user']}",
            f"--password={config['password']}",
            "--single-transaction",
            "--routines",
            "--triggers",
            config["database"],
        ]

        # Run mysqldump and compress output
        result = subprocess.run(cmd, capture_output=True, check=True)
        with gzip.open(DUMP_FILE, "wb") as f:
            f.write(result.stdout)

        size_mb = DUMP_FILE.stat().st_size / (1024 * 1024)
        print(f"Backup complete: {size_mb:.1f} MB")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: mysqldump failed: {e.stderr.decode()}")
        return False
    except FileNotFoundError:
        print("WARNING: mysqldump not available, skipping backup")
        return False
    except Exception as e:
        print(f"ERROR: Backup failed with unexpected error: {e}")
        return False


def restore_from_dump(config: dict) -> bool:
    """Restore database from compressed SQL dump."""
    if not DUMP_FILE.exists():
        return False

    print(f"\nRestoring database from {DUMP_FILE}...")

    cmd = [
        "mysql",
        f"--host={config['host']}",
        f"--port={config['port']}",
        f"--user={config['user']}",
        f"--password={config['password']}",
        "--ssl-mode=DISABLED",
        config["database"],
    ]

    try:
        # Decompress and pipe to mysql
        with gzip.open(DUMP_FILE, "rb") as f:
            sql_content = f.read()

        result = subprocess.run(cmd, input=sql_content, capture_output=True, check=True)
        print("Restore complete!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: mysql restore failed: {e.stderr.decode()}")
        return False
    except FileNotFoundError:
        print("WARNING: mysql client not available")
        return False


def sync_schema(remote_conn, local_conn):
    """Sync table schema from remote to local database."""
    remote_cursor = remote_conn.cursor()
    local_cursor = local_conn.cursor()

    # Disable foreign key checks for dropping/creating tables
    local_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    # Get all tables from remote
    remote_cursor.execute("SHOW TABLES")
    tables = [row[0] for row in remote_cursor.fetchall()]

    print(f"Syncing schema for {len(tables)} tables...")

    for table in tables:
        # Get CREATE TABLE statement from remote
        remote_cursor.execute(f"SHOW CREATE TABLE {table}")
        create_stmt = remote_cursor.fetchone()[1]

        # Drop and recreate table locally
        local_cursor.execute(f"DROP TABLE IF EXISTS {table}")
        local_cursor.execute(create_stmt)
        print(f"  {table}: schema synced")

    # Re-enable foreign key checks
    local_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    local_conn.commit()
    remote_cursor.close()
    local_cursor.close()

    return tables


def copy_table_data(
    remote_conn,
    local_conn,
    table: str,
    query: str,
    batch_size: int = 500
):
    """Copy data from remote to local database."""
    remote_cursor = remote_conn.cursor()
    local_cursor = local_conn.cursor()

    # Get column names
    remote_cursor.execute(f"SHOW COLUMNS FROM {table}")
    columns = [row[0] for row in remote_cursor.fetchall()]
    cols_str = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))

    # Fetch and insert data in batches
    remote_cursor.execute(query)

    total = 0
    while True:
        rows = remote_cursor.fetchmany(batch_size)
        if not rows:
            break

        insert_query = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})"
        local_cursor.executemany(insert_query, rows)
        local_conn.commit()

        total += len(rows)
        print(f"  {table}: {total} rows copied", end="\r")

    print(f"  {table}: {total} rows copied")

    remote_cursor.close()
    local_cursor.close()

    return total


def main():
    parser = argparse.ArgumentParser(description="Seed local MySQL from AWS RDS")
    parser.add_argument(
        "--limit",
        type=int,
        default=5000,
        help="Maximum number of movies to seed (default: 5000)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-fetch from AWS RDS (updates local backup)"
    )
    args = parser.parse_args()

    # Load environment variables
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()

    print("=" * 60)
    print("Local Database Seeder")
    print("=" * 60)

    # Get configs
    local_config = get_db_config("local")
    remote_config = get_db_config("remote")

    # Wait for local database
    print(f"\nConnecting to local database: {local_config['host']}:{local_config['port']}")
    if not wait_for_db(local_config):
        print("ERROR: Could not connect to local database")
        sys.exit(1)
    print("Local database is ready.")

    # Check if seeding is needed
    local_count = get_movie_count(local_config)
    if local_count > 0 and not args.force:
        print(f"\nLocal database already has {local_count} movies.")
        print("Skipping seed. Use --force to re-seed.")
        sys.exit(0)

    # Strategy: Try local backup first (unless --force), then fall back to remote
    if not args.force and DUMP_FILE.exists():
        print(f"\nFound local backup: {DUMP_FILE}")
        if restore_from_dump(local_config):
            restored_count = get_movie_count(local_config)
            print(f"\n{'=' * 60}")
            print(f"Restored {restored_count} movies from local backup!")
            print("=" * 60)
            sys.exit(0)
        else:
            print("Local restore failed, falling back to remote...")

    # Validate remote config (only needed if we're fetching from remote)
    if not remote_config["host"]:
        print("\nREMOTE_SQL_HOST not set. Skipping seed.")
        print("(Set AWS RDS credentials in .env to enable auto-seeding)")
        sys.exit(0)

    # Connect to remote
    print(f"\nConnecting to remote database: {remote_config['host']}:{remote_config['port']}")
    try:
        remote_conn = pymysql.connect(**remote_config)
    except pymysql.Error as e:
        print(f"ERROR: Could not connect to remote database: {e}")
        sys.exit(1)
    print("Remote database connected.")

    # Get movie IDs to copy
    print(f"\nSelecting top {args.limit} movies by popularity...")
    remote_cursor = remote_conn.cursor()
    remote_cursor.execute(
        f"SELECT id FROM movies ORDER BY popularity DESC LIMIT {args.limit}"
    )
    movie_ids = [row[0] for row in remote_cursor.fetchall()]
    remote_cursor.close()

    if not movie_ids:
        print("ERROR: No movies found in remote database")
        sys.exit(1)

    movie_ids_str = ",".join(map(str, movie_ids))
    print(f"Selected {len(movie_ids)} movies")

    # Connect to local
    local_conn = pymysql.connect(**local_config)

    # Sync schema from remote (always, to pick up any changes)
    print("\nSyncing schema from remote...")
    sync_schema(remote_conn, local_conn)

    # Copy data
    print("\nCopying data from remote to local...")

    # Movies
    copy_table_data(
        remote_conn, local_conn, "movies",
        f"SELECT * FROM movies WHERE id IN ({movie_ids_str})"
    )

    # People (only those in credits)
    copy_table_data(
        remote_conn, local_conn, "people",
        f"""SELECT DISTINCT p.* FROM people p
            INNER JOIN credits c ON p.id = c.person_id
            WHERE c.movie_id IN ({movie_ids_str})"""
    )

    # Credits
    copy_table_data(
        remote_conn, local_conn, "credits",
        f"SELECT * FROM credits WHERE movie_id IN ({movie_ids_str})"
    )

    # Genres
    copy_table_data(
        remote_conn, local_conn, "genres",
        f"SELECT * FROM genres WHERE movie_id IN ({movie_ids_str})"
    )

    # Close connections
    remote_conn.close()
    local_conn.close()

    # Backup to local file for faster restores
    dump_database(local_config)

    print("\n" + "=" * 60)
    print("Seeding complete!")
    print(f"Local backup saved to: {DUMP_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
