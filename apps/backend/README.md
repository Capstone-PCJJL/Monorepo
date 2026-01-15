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

| Variable | Default | Description |
|----------|---------|-------------|
| `SQL_HOST` | `localhost` | MySQL server hostname |
| `SQL_PORT` | `3306` | MySQL server port |
| `SQL_USER` | - | Database username |
| `SQL_PASS` | - | Database password |
| `SQL_DB` | - | Database name |

**Local development with Docker:**
```bash
docker run -d --name mysql \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=tmdb \
  -p 3306:3306 \
  mysql:8

# Then use:
# SQL_HOST=localhost
# SQL_USER=root
# SQL_PASS=password
# SQL_DB=tmdb
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

# Database
SQL_HOST=localhost
SQL_PORT=3306
SQL_USER=root
SQL_PASS=your_db_password
SQL_DB=tmdb_pipeline

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
