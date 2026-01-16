# Backend

Python backend for the movie recommendation site: FastAPI REST API and TMDB data pipeline.

> **Full Project Setup**: See the [root README](../../README.md) for docker-compose commands and full environment variables.

## Components

| Component | Description |
|-----------|-------------|
| [REST API](api/README.md) | FastAPI endpoints for movies, users, watchlist, ratings |
| [TMDB Pipeline](tmdb_pipeline/README.md) | CLI for ingesting movie data from TMDB |
| [Tests](tests/README.md) | Pytest test suite |

## Project Structure

```
backend/
├── api/                # REST API (FastAPI)
│   ├── main.py         # App entry point
│   ├── routers/        # Endpoint handlers
│   └── schemas/        # Pydantic models
├── tmdb_pipeline/      # Data ingestion CLI
│   ├── cli.py          # Command-line interface
│   └── docs/           # Deployment guide
├── tests/              # Test suite
├── Dockerfile
└── requirements.txt
```

## Running with Python (without Docker)

### 1. Setup

```bash
cd apps/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` in the monorepo root with at minimum:

```env
# TMDB API (required for pipeline)
API_KEY=your_tmdb_api_key
TMDB_BEARER_TOKEN=your_bearer_token

# Database (set one pair)
DB_MODE=local  # or 'remote'

LOCAL_SQL_HOST=localhost
LOCAL_SQL_PORT=3306
LOCAL_SQL_USER=root
LOCAL_SQL_PASS=password
LOCAL_SQL_DB=tmdb

# Or for remote:
# REMOTE_SQL_HOST=your-rds-endpoint.amazonaws.com
# REMOTE_SQL_USER=admin
# REMOTE_SQL_PASS=your_password
# REMOTE_SQL_DB=tmdb
```

### 3. Run

```bash
# Start API server
uvicorn api.main:app --reload --port 8000

# Run pipeline commands
python -m tmdb_pipeline status
python -m tmdb_pipeline approve
```

## Pipeline Commands

### Setup & Status

```bash
python -m tmdb_pipeline setup     # Create database tables
python -m tmdb_pipeline status    # Check database status
python -m tmdb_pipeline test      # Test API and database connections
```

### Adding Movies

```bash
python -m tmdb_pipeline add-new                   # Fetch new releases → pending
python -m tmdb_pipeline search "Inception"        # Search TMDB
python -m tmdb_pipeline search --add 27205        # Add specific movie → pending
```

### Approval Workflow

Movies added via `add-new` or `search` go to pending tables. Approve them to make them live:

```bash
python -m tmdb_pipeline list-pending              # List all pending movies

# Approval modes:
python -m tmdb_pipeline approve                   # Interactive: review one by one (y/n/q)
python -m tmdb_pipeline approve --limit 10        # Review first 10 only
python -m tmdb_pipeline approve --quick           # Approve ALL pending (requires confirmation)
python -m tmdb_pipeline approve --movie-id 27205  # Approve specific movie by ID
python -m tmdb_pipeline approve --search "matrix" # Search pending and approve matches
```

### Running with Docker

```bash
# In running container
docker exec -it monorepo-backend python -m tmdb_pipeline status
docker exec -it monorepo-backend python -m tmdb_pipeline add-new
docker exec -it monorepo-backend python -m tmdb_pipeline approve

# One-off commands
docker-compose run --rm backend status
docker-compose run --rm backend add-new
docker-compose run --rm backend approve
docker-compose run --rm backend approve --quick

# Re-seed database (force re-download from AWS RDS)
docker-compose --profile local run --rm seeder seed --force
```

## Running Tests

```bash
pytest                                    # Run all tests
pytest -v                                 # Verbose output
pytest --cov=api --cov=tmdb_pipeline      # With coverage
pytest tests/test_api_public.py           # Single test file
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
