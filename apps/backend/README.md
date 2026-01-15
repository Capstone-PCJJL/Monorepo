# Backend

Backend services for the movie recommendation website. Handles data ingestion from TMDB, provides a REST API for the frontend, and manages an approval workflow for new movies.

> **Note**: This is part of a monorepo. See the [root README](../../README.md) for full project documentation.

## Components

| Component | Description | Documentation |
|-----------|-------------|---------------|
| [TMDB Pipeline](tmdb_pipeline/README.md) | CLI for ingesting movie data from TMDB API | Full CLI reference |
| [REST API](api/README.md) | FastAPI server for frontend integration | Endpoints reference |
| [Tests](tests/README.md) | Pytest test suite | Coverage & test structure |

## Quick Start

```bash
# 1. Navigate to backend
cd apps/backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Setup database (reads .env from monorepo root automatically)
python -m tmdb_pipeline setup

# 5. Test connections
python -m tmdb_pipeline test

# 6. Run initial data ingestion (test with 5 movies first)
python -m tmdb_pipeline initial --test-limit 5

# 7. Approve the test movies
python -m tmdb_pipeline approve

# 8. Start the API server
uvicorn api.main:app --reload --port 8000
```

> **Note**: On EC2/Linux, use `python3` instead of `python`.

## Project Structure

```
apps/backend/
├── api/                    # REST API (FastAPI) - public read-only
│   ├── main.py             # App entry point
│   ├── routers/            # Endpoint handlers
│   └── schemas/            # Pydantic models
├── tmdb_pipeline/          # Data ingestion CLI
│   ├── cli.py              # Command-line interface
│   ├── client.py           # TMDB API client
│   ├── database.py         # Database operations
│   ├── pipeline.py         # Ingestion orchestrator
│   ├── scripts/            # Automation scripts
│   ├── sql/                # Table schemas
│   └── docs/               # Pipeline documentation
├── tests/                  # Test suite
│   ├── conftest.py         # Fixtures and mocks
│   ├── test_pipeline_flows.py
│   └── test_api_public.py
├── Dockerfile              # Container build
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Environment Variables

Create a `.env` file in this directory (`apps/backend/`).

### TMDB API (Required)

| Variable | Description |
|----------|-------------|
| `API_KEY` | TMDB API key (v3 auth) |
| `TMDB_BEARER_TOKEN` | TMDB Bearer token (v4 auth) |
| `BASE_URL` | TMDB API base URL (default: `https://api.themoviedb.org/3`) |

**How to get TMDB credentials:**
1. Create an account at [themoviedb.org](https://www.themoviedb.org/)
2. Go to **Settings > API**
3. Click **Create** or **Request an API Key**
4. Select **Developer** and accept the terms
5. Copy both:
   - **API Key (v3 auth)** -> `API_KEY`
   - **API Read Access Token (v4 auth)** -> `TMDB_BEARER_TOKEN`

---

### Database (Required)

Switch between local and remote databases by changing `DB_MODE`:

```env
DB_MODE=local   # Uses LOCAL_SQL_* variables
DB_MODE=remote  # Uses REMOTE_SQL_* variables
```

#### Local Docker Database (Development)

```env
DB_MODE=local
LOCAL_SQL_HOST=localhost
LOCAL_SQL_PORT=3306
LOCAL_SQL_USER=root
LOCAL_SQL_PASS=password
LOCAL_SQL_DB=tmdb
```

From the monorepo root:
```bash
docker-compose up db -d   # Auto-seeds ~10k movies on first run
```

#### AWS RDS (Production/Staging)

```env
DB_MODE=remote
REMOTE_SQL_HOST=your-rds-endpoint.region.rds.amazonaws.com
REMOTE_SQL_PORT=3306
REMOTE_SQL_USER=your_rds_username
REMOTE_SQL_PASS=your_rds_password
REMOTE_SQL_DB=tmdb
```

#### Quick Reference

| Mode | Command |
|------|---------|
| `DB_MODE=local` | `docker-compose up -d` |
| `DB_MODE=remote` | `docker-compose up backend frontend -d` |

#### Generating Seed Data

To update the local development seed data:
```bash
# Temporarily switch to remote to export from production
# Edit .env: DB_MODE=remote

# Export top 10,000 movies
python scripts/export_seed_data.py --limit 10000

# Switch back to local
# Edit .env: DB_MODE=local

# Commit the new seed file
git add ../../docker/mysql/init/02-seed.sql.gz
git commit -m "Update local dev seed data"
```

---

### API Server (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Host to bind |
| `API_PORT` | `8000` | Server port |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins |

---

### Example `.env` File

```env
# TMDB API
API_KEY=abc123def456
TMDB_BEARER_TOKEN=eyJhbGciOiJIUzI1NiJ9...
BASE_URL=https://api.themoviedb.org/3

# Database - switch mode: local or remote
DB_MODE=local

LOCAL_SQL_HOST=localhost
LOCAL_SQL_PORT=3306
LOCAL_SQL_USER=root
LOCAL_SQL_PASS=password
LOCAL_SQL_DB=tmdb

REMOTE_SQL_HOST=your-rds-endpoint.amazonaws.com
REMOTE_SQL_PORT=3306
REMOTE_SQL_USER=admin
REMOTE_SQL_PASS=your_password
REMOTE_SQL_DB=tmdb

# API Server (optional)
API_HOST=0.0.0.0
API_PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

## Running with Docker

```bash
# Build the image
docker build -t tmdb-backend .

# Run the pipeline CLI
docker run --env-file ../../.env tmdb-backend status
docker run --env-file ../../.env tmdb-backend initial --test-limit 5

# Run the API server
docker run --env-file ../../.env -p 8000:8000 tmdb-backend api

# Run tests
docker run tmdb-backend test
docker run tmdb-backend test -v
```

**With docker-compose** (from monorepo root):
```bash
docker-compose run --rm backend status
docker-compose run --rm backend approve
docker-compose run --rm backend api
```

See [tmdb_pipeline/README.md](tmdb_pipeline/README.md#docker-command-reference) for the complete Docker command reference.

## API Documentation

Once the API is running, visit:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

See [api/README.md](api/README.md) for endpoint reference.

## Pipeline Commands

```bash
# Setup & status
python -m tmdb_pipeline setup      # Create database tables
python -m tmdb_pipeline status     # Check database status
python -m tmdb_pipeline test       # Test connections

# Data ingestion
python -m tmdb_pipeline initial --test-limit 5   # Initial import
python -m tmdb_pipeline add-new                   # Add new releases
python -m tmdb_pipeline update                    # Update changed movies

# Approval workflow (CLI only)
python -m tmdb_pipeline approve                   # Interactive review
python -m tmdb_pipeline list-pending              # List pending movies
```

See [tmdb_pipeline/README.md](tmdb_pipeline/README.md) for full CLI reference.

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=api --cov=tmdb_pipeline --cov-report=term-missing

# Run specific test file
pytest tests/test_api_public.py
```

**Test suite:** 47 tests covering pipeline flows and public API.

See [tests/README.md](tests/README.md) for full test documentation.

## License

MIT License
