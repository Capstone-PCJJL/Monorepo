# TMDB Pipeline CLI

Command-line interface for ingesting movie data from The Movie Database (TMDB) API.

> **Full Project Setup**: See the [root README](../../../../README.md) for docker-compose commands and all environment variables.

## Features

- Initial bulk import from TMDB
- Differential updates (changed movies)
- Add new releases
- Verification against TMDB exports
- Backfill missing movies
- Search & add specific movies
- Approval workflow (pending → production)

## Setup (without Docker)

```bash
cd apps/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables

Create `.env` in the monorepo root:

```env
# TMDB API (required)
API_KEY=your_tmdb_api_key
TMDB_BEARER_TOKEN=your_bearer_token

# Database
DB_MODE=local  # or 'remote'

LOCAL_SQL_HOST=localhost
LOCAL_SQL_PORT=3306
LOCAL_SQL_USER=root
LOCAL_SQL_PASS=password
LOCAL_SQL_DB=tmdb
```

### Test Connection

```bash
python -m tmdb_pipeline test      # Test API and database
python -m tmdb_pipeline status    # Check database status
```

## Running Commands

**With Python:**
```bash
cd apps/backend
source venv/bin/activate
python -m tmdb_pipeline status
python -m tmdb_pipeline approve
```

**With Docker:**
```bash
docker-compose run --rm backend status
docker-compose run --rm backend add-new
docker-compose run --rm backend approve
docker-compose run --rm backend approve --quick
docker-compose run --rm backend search "Inception"
```

## Commands Reference

### Setup & Status

```bash
python -m tmdb_pipeline setup     # Create database tables
python -m tmdb_pipeline status    # Check database status
python -m tmdb_pipeline test      # Test API and database connections
```

### Data Ingestion

```bash
# Initial import (empty database)
python -m tmdb_pipeline initial --test-limit 5   # Test with 5 movies
python -m tmdb_pipeline initial                   # Full import

# Ongoing updates
python -m tmdb_pipeline add-new                   # Fetch new releases
python -m tmdb_pipeline update --days-back 7      # Update changed movies
```

### Search & Add

```bash
python -m tmdb_pipeline search "Inception"    # Search by title
python -m tmdb_pipeline search --add 27205    # Add by TMDB ID
```

### Approval Workflow

Movies from `add-new` or `search` go to pending tables first. Approve them to make them live.

```bash
python -m tmdb_pipeline list-pending              # List all pending movies
```

**Approval modes:**

```bash
# Interactive - review one by one (y/n/q to quit)
python -m tmdb_pipeline approve

# Limit how many to review
python -m tmdb_pipeline approve --limit 10

# Approve ALL pending at once (requires confirmation)
python -m tmdb_pipeline approve --quick

# Approve a specific movie by ID
python -m tmdb_pipeline approve --movie-id 27205

# Search pending movies and approve matches
python -m tmdb_pipeline approve --search "matrix"
```

### Verification & Backfill

```bash
python -m tmdb_pipeline verify                                    # Check completeness
python -m tmdb_pipeline backfill --min-popularity 10 --to-production  # Fill gaps
```

## Workflow

```
TMDB API
    │
    ▼
┌─────────────────────────────────────┐
│  initial    add-new    search       │
│  (empty DB) (new ones) (manual)     │
│      │          │          │        │
│      ▼          ▼          ▼        │
│  PRODUCTION    PENDING TABLES       │
│   TABLES      (awaiting approval)   │
│                    │                │
│                    ▼                │
│                 approve             │
│                    │                │
│                    ▼                │
│               PRODUCTION            │
└─────────────────────────────────────┘
```

## Database Tables

| Production | Pending | Description |
|------------|---------|-------------|
| `movies` | `movies_pending` | Movie details |
| `credits` | `credits_pending` | Cast and crew |
| `genres` | `genres_pending` | Movie-genre links |
| `people` | `people_pending` | Actor/director info |

## Troubleshooting

**Rate limiting (429 errors):**
```bash
python -m tmdb_pipeline backfill --slow-mode
```

**Missing movies after initial ingestion:**
Expected due to TMDB's 10k API limit. Use `verify` and `backfill`.

## Deployment

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for cloud deployment (EC2, RDS, cron jobs).
