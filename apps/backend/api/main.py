"""
FastAPI application for the TMDB Pipeline API.

Public read-only API for the movie frontend.
Admin operations (approve, import) are handled via CLI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.exceptions import APIError, api_error_handler

# Import routers
from api.routers import movies, people, genres, search, discover, users, watchlist, ratings, imports

# Create FastAPI app
app = FastAPI(
    title="TMDB Pipeline API",
    description="Public REST API for browsing movies",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Register exception handlers
app.add_exception_handler(APIError, api_error_handler)

# Add CORS middleware (must be done before app starts)
# In production, configure ALLOWED_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configured at runtime via env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount public routers
app.include_router(movies.router, prefix="/api/v1", tags=["Movies"])
app.include_router(people.router, prefix="/api/v1", tags=["People"])
app.include_router(genres.router, prefix="/api/v1", tags=["Genres"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(discover.router, prefix="/api/v1", tags=["Discovery"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])
app.include_router(watchlist.router, prefix="/api/v1", tags=["Watchlist"])
app.include_router(ratings.router, prefix="/api/v1", tags=["Ratings"])
app.include_router(imports.router, prefix="/api/v1", tags=["Import"])


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirects to docs."""
    return {
        "message": "TMDB Pipeline API",
        "docs": "/api/docs",
        "redoc": "/api/redoc",
    }


@app.get("/health", include_in_schema=False)
async def health():
    """Simple health check endpoint."""
    return {"status": "ok"}
