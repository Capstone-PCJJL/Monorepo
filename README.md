# Movie Recommendation Site

A full-stack movie recommendation application with a React frontend and Python backend, featuring TMDB data ingestion and a REST API.

## Project Structure

```
Monorepo/
├── apps/
│   ├── frontend/          # React.js web application (Vite)
│   │   ├── src/           # React components and pages
│   │   ├── index.html     # Entry HTML file
│   │   └── README.md      # Frontend documentation
│   └── backend/           # Python API & Data Pipeline
│       ├── api/           # FastAPI REST API (movies + users)
│       ├── tmdb_pipeline/ # TMDB data ingestion CLI
│       ├── tests/         # Pytest test suite
│       └── README.md      # Backend documentation
├── docker-compose.yml     # Full stack orchestration
├── .env.example           # Environment template
└── README.md              # This file
```

## Quick Start

### Prerequisites

- Node.js 18+ (frontend)
- Python 3.11+ (backend)
- MySQL 8+ (database)
- Docker & Docker Compose (optional)

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd Monorepo

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials (see Environment Variables below)

# With external database (AWS RDS, etc.)
docker-compose up backend frontend

# Or with local MySQL container (starts all services)
docker-compose up

# Access:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000/api/docs
```

### Option 2: Manual Setup

#### Database

```bash
# Using Docker
docker run -d --name mysql \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=tmdb \
  -p 3306:3306 \
  mysql:8
```

#### Backend

```bash
cd apps/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database (reads .env from monorepo root automatically)
python -m tmdb_pipeline setup

# Run initial data import (test with 5 movies)
python -m tmdb_pipeline initial --test-limit 5
python -m tmdb_pipeline approve

# Start API server
uvicorn api.main:app --reload --port 8000
```

#### Frontend

```bash
cd apps/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Environment Variables

See [.env.example](.env.example) for the complete template with inline instructions.

### TMDB API (Backend)

| Variable | How to Get |
|----------|------------|
| `API_KEY` | 1. Create account at [themoviedb.org](https://www.themoviedb.org/signup)<br>2. Go to **Settings > API**<br>3. Click **Create** > **Developer** > Accept terms<br>4. Copy **API Key (v3 auth)** |
| `TMDB_BEARER_TOKEN` | Same page as above, copy **API Read Access Token (v4 auth)** |

### MySQL Database

| Variable | Description |
|----------|-------------|
| `SQL_HOST` | `localhost` (local), `db` (docker-compose), or RDS endpoint |
| `SQL_PORT` | Default: `3306` |
| `SQL_USER` | Your database username |
| `SQL_PASS` | Your database password |
| `SQL_DB` | Database name (create with `CREATE DATABASE tmdb;`) |

### Firebase Authentication (Frontend)

| Variable | How to Get |
|----------|------------|
| `VITE_FIREBASE_API_KEY` | 1. Go to [Firebase Console](https://console.firebase.google.com/)<br>2. Select project > **Project Settings**<br>3. Scroll to **Your apps** > Web app<br>4. Copy `apiKey` from config |
| `VITE_FIREBASE_AUTH_DOMAIN` | Same config, copy `authDomain` |
| `VITE_FIREBASE_PROJECT_ID` | Same config, copy `projectId` |
| `VITE_FIREBASE_STORAGE_BUCKET` | Same config, copy `storageBucket` |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | Same config, copy `messagingSenderId` |
| `VITE_FIREBASE_APP_ID` | Same config, copy `appId` |
| `VITE_FIREBASE_MEASUREMENT_ID` | Same config, copy `measurementId` (for Google Analytics) |

### API Configuration

| Variable | Description |
|----------|-------------|
| `API_HOST` | `0.0.0.0` (Docker) or `127.0.0.1` (local) |
| `API_PORT` | Default: `8000` |
| `ALLOWED_ORIGINS` | Frontend URLs for CORS (comma-separated) |
| `VITE_API_URL` | Backend URL for frontend (default: `http://localhost:8000`) |

## Documentation

| Component | Documentation |
|-----------|---------------|
| Frontend | [apps/frontend/README.md](apps/frontend/README.md) |
| Backend | [apps/backend/README.md](apps/backend/README.md) |
| REST API | [apps/backend/api/README.md](apps/backend/api/README.md) |
| TMDB Pipeline | [apps/backend/tmdb_pipeline/README.md](apps/backend/tmdb_pipeline/README.md) |
| Deployment | [apps/backend/tmdb_pipeline/docs/DEPLOYMENT.md](apps/backend/tmdb_pipeline/docs/DEPLOYMENT.md) |
| Tests | [apps/backend/tests/README.md](apps/backend/tests/README.md) |

## Development Workflow

### Running Tests (Backend)

```bash
cd apps/backend
pytest                                    # Run all tests
pytest -v                                 # Verbose output
pytest --cov=api --cov=tmdb_pipeline      # With coverage
```

### Running Frontend

```bash
cd apps/frontend
npm run dev      # Development server
npm run build    # Production build
```

### API Documentation

Once the backend is running:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Architecture

```
┌─────────────┐                    ┌─────────────┐
│   Frontend  │───────────────────▶│   FastAPI   │──────┐
│   (React)   │   proxy:8000       │  Port 8000  │      │
│  Port 3000  │                    │  (all APIs) │      │
└─────────────┘                    └─────────────┘      │
                                          ▲             │
                                          │             ▼
                                    TMDB Pipeline  ┌────────┐
                                   (data ingestion)│ MySQL  │
                                                   │  DB    │
                                                   └────────┘
```

The FastAPI backend handles all endpoints: movies, users, watchlist, ratings, and imports.

## License

MIT License
