"""
FastAPI application for the TMDB Pipeline API.

Public read-only API for the movie frontend.
Admin operations (approve, import) are handled via CLI.
"""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.exceptions import APIError, api_error_handler
from api.logging_config import (
    logger,
    generate_request_id,
    set_request_id,
    get_request_id,
)

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


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all HTTP requests with timing and response status."""
    request_id = generate_request_id()
    set_request_id(request_id)

    # Skip logging for health checks and docs
    skip_paths = {"/health", "/", "/api/docs", "/api/redoc", "/api/openapi.json"}
    if request.url.path in skip_paths:
        return await call_next(request)

    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    logger.info(
        f"Request started: {request.method} {request.url.path} "
        f"from {client_ip}"
    )

    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        log_level = "info"
        if response.status_code >= 500:
            log_level = "error"
        elif response.status_code >= 400:
            log_level = "warning"

        log_msg = (
            f"Request completed: {request.method} {request.url.path} "
            f"status={response.status_code} duration={duration_ms:.2f}ms"
        )

        if log_level == "error":
            logger.error(log_msg)
        elif log_level == "warning":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        # Add request ID to response headers for debugging
        response.headers["X-Request-ID"] = request_id
        return response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Request failed: {request.method} {request.url.path} "
            f"duration={duration_ms:.2f}ms error={str(e)}"
        )
        raise


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
