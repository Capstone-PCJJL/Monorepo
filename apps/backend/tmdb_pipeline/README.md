# TMDB Pipeline CLI

Command-line interface for ingesting and managing movie data from The Movie Database (TMDB) API.

> **Note**: This is part of a monorepo. See the [root README](../../../../README.md) for full project documentation.

## Features

- **Initial Ingestion** - Bulk import all movies from TMDB
- **Bulk Ingest from Export** - Import using TMDB daily exports (bypasses 10k limit)
- **Differential Updates** - Update only changed movies (14-day window)
- **Add New Movies** - Fetch movies released after your latest entry
- **Verification** - Compare database against TMDB exports
- **Backfill Missing** - Fetch missing movies by popularity
- **Search & Add** - Fuzzy search TMDB and add specific movies
- **Approval Workflow** - Review movies before going live (pending -> production)
- **Test Mode** - Run any operation with `--test-limit N`
- **Slow Mode** - Reduce API rate for large batch operations

## Configuration

See the [backend README](../../README.md#environment-variables) for all environment variables. The pipeline requires:
- TMDB credentials (`API_KEY`, `TMDB_BEARER_TOKEN`)
- Database credentials (`LOCAL_SQL_*` or `REMOTE_SQL_*`)

Note: `DB_MODE` is set automatically by `make up-local` or `make up-remote`.

## Quick Start

### Option 1: Local (venv)

```bash
# Navigate to backend
cd apps/backend

# Create virtual environment (if not exists)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Test connections
python -m tmdb_pipeline test

# Create database tables
python -m tmdb_pipeline setup

# Check status
python -m tmdb_pipeline status

# Test with 5 movies
python -m tmdb_pipeline initial --test-limit 5

# Approve test movies
python -m tmdb_pipeline approve
```

> **Note**: On EC2/Linux, use `python3` instead of `python`.

### Option 2: Docker

If running with `docker-compose up`, use `docker exec` for CLI commands:

```bash
# Run commands in the running backend container
docker exec -it monorepo-backend python -m tmdb_pipeline status
docker exec -it monorepo-backend python -m tmdb_pipeline list-pending
docker exec -it monorepo-backend python -m tmdb_pipeline approve
```

Or use `docker-compose run` for one-off commands (doesn't require containers to be running):

```bash
# Run CLI commands directly
docker-compose run --rm backend status
docker-compose run --rm backend list-pending
docker-compose run --rm backend approve
docker-compose run --rm backend search "Inception"
```

> **Note**: With `docker-compose run`, omit `python -m tmdb_pipeline` - just use the command name.

### Docker Command Reference

All CLI commands work with Docker. Here's the complete reference:

**Using `docker-compose run` (recommended):**
```bash
# Setup & Status
docker-compose run --rm backend setup
docker-compose run --rm backend status
docker-compose run --rm backend test

# Data Ingestion
docker-compose run --rm backend initial --test-limit 5
docker-compose run --rm backend add-new
docker-compose run --rm backend update --days-back 7

# Search & Add
docker-compose run --rm backend search "Inception"
docker-compose run --rm backend search --add 27205

# Approval Workflow
docker-compose run --rm backend list-pending
docker-compose run --rm backend approve
docker-compose run --rm backend approve --quick

# Verification & Backfill
docker-compose run --rm backend verify
docker-compose run --rm backend backfill --min-popularity 10 --to-production
docker-compose run --rm backend bulk-ingest --to-production

# Run API Server
docker-compose run --rm -p 8000:8000 backend api

# Run Tests
docker-compose run --rm backend test
```

**Using `docker exec` (when containers are running):**
```bash
# Any command while docker-compose up is running
docker exec -it monorepo-backend python -m tmdb_pipeline status
docker exec -it monorepo-backend python -m tmdb_pipeline approve
```

**Using standalone Docker:**
```bash
# Build the image
docker build -t tmdb-backend ./apps/backend

# Run commands (pass env file)
docker run --env-file .env tmdb-backend status
docker run --env-file .env tmdb-backend initial --test-limit 5
docker run --env-file .env -p 8000:8000 tmdb-backend api
```

## Commands Reference

### Setup & Status

```bash
python -m tmdb_pipeline setup     # Create missing tables
python -m tmdb_pipeline status    # Check database status
python -m tmdb_pipeline test      # Test API and database connections
python -m tmdb_pipeline drop      # Drop tables (requires confirmation)
```

### Initial Ingestion

For empty databases. Imports movies directly to production tables.

```bash
# Test with 5 movies
python -m tmdb_pipeline initial --test-limit 5

# Full ingestion
python -m tmdb_pipeline initial

# Specific year range
python -m tmdb_pipeline initial --start-year 2024 --end-year 2020

# Resume from specific year
python -m tmdb_pipeline initial --start-year 2002 --force
```

### Add New Movies

Fetches movies released after your latest entry. Goes to pending tables.

```bash
python -m tmdb_pipeline add-new --test-limit 5  # Test
python -m tmdb_pipeline add-new                  # All new movies
```

### Differential Updates

Updates movies that changed in TMDB (max 14-day window).

```bash
python -m tmdb_pipeline update              # Last 14 days
python -m tmdb_pipeline update --days-back 7  # Custom window
```

### Verification & Backfill

The TMDB discover API limits results to 10,000 per query. Use these to maximize coverage.

```bash
# Verify database completeness
python -m tmdb_pipeline verify
python -m tmdb_pipeline verify --by-popularity

# Backfill missing movies
python -m tmdb_pipeline backfill --min-popularity 10 --to-production
python -m tmdb_pipeline backfill --min-popularity 1 --to-production --slow-mode

# Bulk ingest from TMDB daily export
python -m tmdb_pipeline bulk-ingest --min-popularity 1 --to-production

# Re-ingest specific year (bypasses 10k limit)
python -m tmdb_pipeline reingest-year 2024 --to-production
```

**Recommended backfill order:**
```bash
python -m tmdb_pipeline backfill --min-popularity 10 --to-production   # High popularity
python -m tmdb_pipeline backfill --min-popularity 1 --to-production    # Medium
python -m tmdb_pipeline backfill --min-popularity 0.1 --to-production --slow-mode  # Low
```

### Search & Add

```bash
python -m tmdb_pipeline search "Inception"    # Search by title
python -m tmdb_pipeline search --add 27205    # Add by TMDB ID
```

### Approval Workflow

Movies added via `add-new` or `search` go to pending tables.

```bash
python -m tmdb_pipeline approve                # Interactive review
python -m tmdb_pipeline approve --limit 10     # Limit session
python -m tmdb_pipeline approve --search "matrix"  # Search & approve
python -m tmdb_pipeline approve --movie-id 27205   # Approve by ID
python -m tmdb_pipeline approve --quick        # Approve ALL (requires confirmation)
python -m tmdb_pipeline list-pending           # List pending movies
```

## Workflow Diagram

```
                    TMDB API
                        |
                        v
+-----------------------------------------------------+
|                   PIPELINE                          |
|  +---------+   +---------+   +-----------------+   |
|  | initial |   | add-new |   |     search      |   |
|  |(empty DB)|  |(new ones)|  |  (manual add)   |   |
|  +----+----+   +----+----+   +--------+--------+   |
|       |             |                  |            |
|       v             v                  v            |
|  +---------+   +--------------------------------+  |
|  |PRODUCTION|  |      PENDING TABLES            |  |
|  | TABLES  |   |  (awaiting approval)           |  |
|  +---------+   +--------------+-----------------+  |
|                               |                     |
|                               v                     |
|                         +---------+                 |
|                         | approve |                 |
|                         +----+----+                 |
|                              |                      |
|                              v                      |
|                        PRODUCTION                   |
+-----------------------------------------------------+
```

## Database Tables

| Production | Pending | Description |
|------------|---------|-------------|
| `movies` | `movies_pending` | Movie details |
| `credits` | `credits_pending` | Cast and crew |
| `genres` | `genres_pending` | Movie-genre links |
| `people` | `people_pending` | Actor/director info |

## Querying with FULLTEXT

The database includes FULLTEXT indexes for fast search:

```sql
-- Search movies by title
SELECT * FROM movies
WHERE MATCH(title) AGAINST('Star Wars' IN NATURAL LANGUAGE MODE);

-- Search by title or overview
SELECT * FROM movies
WHERE MATCH(title, overview) AGAINST('space adventure');

-- Search people
SELECT * FROM people
WHERE MATCH(name) AGAINST('Christopher Nolan');
```

## Guardrails

- **Initial ingestion protection** - Won't run on non-empty database without `--force`
- **Duplicate prevention** - Checks both pending and production before adding
- **Atomic transactions** - Approval moves all data or nothing
- **Safe exit** - `Ctrl+C` during approval saves progress
- **Confirmation prompts** - `approve --quick` and `drop` require explicit confirmation

## Troubleshooting

### Rate limiting (429 errors)
```bash
# Use slow mode (20 req/sec instead of 35)
python -m tmdb_pipeline backfill --slow-mode
```

### Missing movies after initial ingestion
Expected due to TMDB's 10k limit. Use `verify` and `backfill` to maximize coverage.

### "Production tables already contain data"
Use `--force` only if intentional, or use `add-new` instead.

## Architecture

```
tmdb_pipeline/
├── cli.py          # Command-line interface
├── config.py       # Environment configuration
├── models.py       # Data models
├── client.py       # TMDB API client with rate limiting
├── database.py     # Database operations
├── pipeline.py     # Main orchestrator
├── approval.py     # Approval workflow
├── exports.py      # TMDB daily export handler
├── verification.py # Database verification
├── utils.py        # Logging & helpers
├── scripts/        # Automation scripts
├── sql/            # Table schemas
└── logs/           # Log files
```
