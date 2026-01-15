# Tests

Pytest test suite for the TMDB backend. Tests focus on user flows rather than isolated unit tests.

> **Note**: This is part of a monorepo. See the [root README](../../../README.md) for full project documentation.

## Running Tests

```bash
# Navigate to backend
cd apps/backend

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api_public.py

# Run specific test
pytest tests/test_pipeline_flows.py::TestSetupAndStatusFlow::test_setup_creates_tables
```

## Test Coverage

```bash
# Run with coverage report
pytest --cov=api --cov=tmdb_pipeline --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=api --cov=tmdb_pipeline --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and mocks
├── test_pipeline_flows.py   # Pipeline/CLI user flows (23 tests)
├── test_api_public.py       # Public API endpoints (23 tests)
└── README.md                # This file
```

### Test Files

| File | Tests | Description |
|------|-------|-------------|
| `test_pipeline_flows.py` | 23 | Pipeline operations: setup, ingestion, approval, duplicates, bulk ops |
| `test_api_public.py` | 23 | Public API: movies, people, genres, search, discover, errors |
| `test_api_users.py` | 18 | User API: users, watchlist, ratings, imports, recommendations |

**Total: 64 tests**

## What's Tested

### Pipeline Flows (`test_pipeline_flows.py`)

- **Setup & Status** - Table creation, status checks
- **Add & Approve** - Movies go to pending, approval moves to production
- **Search & Add** - Search TMDB, add results to pending
- **Duplicate Prevention** - Can't add movies already in production/pending
- **Bulk Operations** - Bulk approve/delete selected or all
- **TMDB Client** - Search, get movie details, connection test

### Public API (`test_api_public.py`)

- **Browse & Discover** - Genres, trending, top-rated, filtering, pagination
- **Movie Details** - Get movie, credits, similar movies
- **Search** - Unified search, movie search, people search
- **Person Flows** - Browse people, details, filmography
- **Discover Endpoints** - New releases, upcoming, by decade
- **Error Handling** - 404s, validation errors

### User API (`test_api_users.py`)

- **User Management** - Create/get user, consent, import status
- **Watchlist** - Get, add, remove, not-interested
- **Ratings & Likes** - Add rating, like movie
- **Import** - CSV import for ratings and likes
- **Recommendations** - Get recommended movies for user

## Test Fixtures (conftest.py)

### Mock Objects

| Fixture | Description |
|---------|-------------|
| `mock_db` | Empty in-memory database |
| `mock_db_with_data` | Database with 5 sample movies |
| `mock_tmdb_client` | Mock TMDB API client |

### API Testing

| Fixture | Description |
|---------|-------------|
| `api_client` | FastAPI TestClient with mocked dependencies |

### Sample Data

5 pre-loaded movies for testing:
- Fight Club (550)
- Inception (27205)
- The Dark Knight (155)
- Pulp Fiction (680)
- Interstellar (157336)

## Test Philosophy

Tests are designed to mimic real user flows rather than testing every function in isolation:

1. **Flow-based** - Tests follow what a user would actually do (e.g., search -> add -> approve)
2. **Not redundant** - Each test covers a distinct scenario
3. **Focused** - No exhaustive edge case testing for every function
4. **Fast** - Uses mocks instead of real database/API calls

## Adding New Tests

1. Add tests to the appropriate file based on what's being tested
2. Use existing fixtures from `conftest.py`
3. Follow the naming pattern: `test_<action>_<expected_result>`
4. Group related tests in classes: `class Test<Feature>Flow:`

Example:
```python
class TestNewFeatureFlow:
    """Flow: Description of what this tests"""

    def test_feature_does_something(self, api_client):
        """User does X and expects Y."""
        response = api_client.get("/api/v1/endpoint")
        assert response.status_code == 200
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`, run pytest from the backend directory:
```bash
cd apps/backend
pytest tests/
```

### Database State Issues

Tests use isolated mock databases. If tests interfere with each other, check that fixtures are properly scoped and mocks are being reset.
