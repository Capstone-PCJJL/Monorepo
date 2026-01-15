# REST API

FastAPI server providing both public movie endpoints and user-specific endpoints for the frontend. Admin operations (approve, import) are handled via CLI.

> **Note**: This is part of a monorepo. See the [root README](../../../README.md) for full project documentation.

## Running the API

```bash
# Development (with auto-reload)
cd apps/backend
uvicorn api.main:app --reload --port 8000

# Production
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Documentation

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Configuration

See the [backend README](../README.md#environment-variables) for all environment variables. The API requires:
- Database credentials (`SQL_HOST`, `SQL_USER`, `SQL_PASS`, `SQL_DB`)

## Endpoints

### Movies

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/movies` | Browse movies with filtering & pagination |
| GET | `/api/v1/movies/{id}` | Get movie details |
| GET | `/api/v1/movies/{id}/credits` | Get cast & crew |
| GET | `/api/v1/movies/{id}/similar` | Get similar movies |
| GET | `/api/v1/movies/recommended/{user_id}` | Get recommended movies for user |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/users/firebase` | Get or create user by Firebase ID |
| GET | `/api/v1/users/{id}/consent` | Check user consent status |
| PUT | `/api/v1/users/{id}/consent` | Set user consent to true |
| GET | `/api/v1/users/{id}/import-status` | Check if user imported data |
| PUT | `/api/v1/users/{id}/import-status` | Set import status to true |

### Watchlist

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/{id}/watchlist` | Get user's watchlist |
| POST | `/api/v1/users/{id}/watchlist` | Add movie to watchlist |
| DELETE | `/api/v1/users/{id}/watchlist/{movie_id}` | Remove from watchlist |
| POST | `/api/v1/users/{id}/not-interested` | Mark movie as not interested |

### Ratings & Likes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/users/{id}/ratings` | Add a rating for a movie |
| POST | `/api/v1/users/{id}/likes` | Like a movie |

### Import

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/users/{id}/import` | Import ratings/likes from CSV |

### People

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/people` | Browse people |
| GET | `/api/v1/people/{id}` | Get person details with filmography |
| GET | `/api/v1/people/{id}/movies` | Get person's movies (paginated) |

### Genres

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/genres` | List all genres with counts |
| GET | `/api/v1/genres/{name}/movies` | Get movies by genre |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/search` | Unified search (movies + people) |
| GET | `/api/v1/search/movies` | Search movies with filters |
| GET | `/api/v1/search/people` | Search people |

### Discovery

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/discover/trending` | Trending movies |
| GET | `/api/v1/discover/top-rated` | Highest rated movies |
| GET | `/api/v1/discover/new-releases` | Recent releases |
| GET | `/api/v1/discover/upcoming` | Coming soon |
| GET | `/api/v1/discover/by-decade` | Movies by decade |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

## Example Requests

```bash
# Get movies with pagination
curl "http://localhost:8000/api/v1/movies?page=1&per_page=10"

# Get movie details
curl "http://localhost:8000/api/v1/movies/550"

# Search movies
curl "http://localhost:8000/api/v1/search/movies?q=inception"

# Get trending movies
curl "http://localhost:8000/api/v1/discover/trending"

# Get movies by genre
curl "http://localhost:8000/api/v1/genres/Action/movies"
```

## Project Structure

```
api/
├── main.py              # FastAPI app & router mounting
├── dependencies.py      # DI: get_db, get_config
├── exceptions.py        # Custom error handlers
├── routers/
│   ├── movies.py        # /movies endpoints
│   ├── people.py        # /people endpoints
│   ├── genres.py        # /genres endpoints
│   ├── search.py        # /search endpoints
│   ├── discover.py      # /discover endpoints
│   ├── users.py         # /users endpoints
│   ├── watchlist.py     # /users/{id}/watchlist endpoints
│   ├── ratings.py       # /users/{id}/ratings & likes endpoints
│   └── imports.py       # /users/{id}/import endpoint
├── schemas/             # Pydantic request/response models
│   ├── common.py        # Shared schemas
│   ├── movie.py         # Movie schemas
│   ├── user.py          # User schemas
│   ├── watchlist.py     # Watchlist schemas
│   └── rating.py        # Rating schemas
└── services/            # Business logic
    └── fuzzy_match.py   # CSV import fuzzy matching
```

## Admin Operations

Admin operations (approving movies, importing from TMDB) are handled via the CLI pipeline, not the API:

```bash
# Approve pending movies
python -m tmdb_pipeline approve

# Import movies from TMDB
python -m tmdb_pipeline search "Movie Title"
python -m tmdb_pipeline add-new
```

See [tmdb_pipeline/README.md](../tmdb_pipeline/README.md) for full CLI reference.

## Adding New Routes

Follow these steps to add a new API endpoint:

### 1. Create Pydantic Schemas

Create request/response models in `schemas/`:

```python
# api/schemas/example.py
from pydantic import BaseModel, Field

class ExampleRequest(BaseModel):
    """Request to create an example."""
    name: str = Field(..., description="Example name")
    value: int = Field(default=0, ge=0)

class ExampleResponse(BaseModel):
    """Response with example data."""
    id: int
    name: str
    success: bool = True
```

### 2. Create the Router

Create a new router file in `routers/`:

```python
# api/routers/example.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from api.dependencies import get_db
from api.schemas.example import ExampleRequest, ExampleResponse
from tmdb_pipeline.database import DatabaseManager

router = APIRouter()

@router.post("/examples", response_model=ExampleResponse, status_code=status.HTTP_201_CREATED)
async def create_example(
    request: ExampleRequest,
    db: DatabaseManager = Depends(get_db),
):
    """Create a new example."""
    with db.engine.connect() as conn:
        result = conn.execute(
            text("INSERT INTO examples (name, value) VALUES (:name, :value)"),
            {"name": request.name, "value": request.value}
        )
        conn.commit()

        result = conn.execute(text("SELECT LAST_INSERT_ID()"))
        insert_id = result.fetchone()[0]

        return ExampleResponse(id=insert_id, name=request.name)

@router.get("/examples/{example_id}", response_model=ExampleResponse)
async def get_example(
    example_id: int,
    db: DatabaseManager = Depends(get_db),
):
    """Get an example by ID."""
    with db.engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, name FROM examples WHERE id = :id"),
            {"id": example_id}
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Example not found"
            )

        return ExampleResponse(id=row[0], name=row[1])
```

### 3. Register the Router

Add the router to `main.py`:

```python
# api/main.py
from api.routers import example  # Add import

# In create_app():
app.include_router(example.router, prefix="/api/v1", tags=["examples"])
```

### 4. Test the Endpoint

```bash
# Start the server
uvicorn api.main:app --reload --port 8000

# Test the endpoint
curl -X POST http://localhost:8000/api/v1/examples \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "value": 42}'
```

### Key Patterns

- **Dependency Injection**: Use `db: DatabaseManager = Depends(get_db)` to get the database
- **Raw SQL**: Use `text()` from SQLAlchemy for raw SQL queries
- **Transactions**: Use `conn.commit()` after INSERT/UPDATE/DELETE operations
- **Error Handling**: Raise `HTTPException` with appropriate status codes
- **Response Models**: Always specify `response_model` for automatic validation
