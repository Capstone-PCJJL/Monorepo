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

- Docker & Docker Compose
- Node.js 18+ (for local frontend development without Docker)
- Python 3.11+ (for local backend development without Docker)

### Option 1: Local Docker Database (Recommended for Development)

The fastest way to get started. Docker automatically seeds ~5k movies from AWS RDS on first run.

```bash
# Clone and configure
git clone <repository-url>
cd Monorepo
cp .env.example .env
# Edit .env: Add all credentials (Firebase, TMDB API, AWS RDS)

# Start everything - runs interactively (Ctrl+C to stop)
DB_MODE=local docker-compose --profile local up
```

Services run at:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **MySQL**: localhost:3306

> **Note**: First run pulls ~5k movies from AWS RDS and saves a local backup (`apps/backend/data/seed_backup.sql.gz`). Subsequent runs restore from this backup instantly.

> **How it works**: The `db` and `seeder` services use Docker Compose profiles. `--profile local` activates them. Omitting the profile starts only backend + frontend.

**Daily development:**
```bash
# Start (local DB) - interactive, logs stream to terminal
DB_MODE=local docker-compose --profile local up

# Start (remote DB) - connects to AWS RDS
DB_MODE=remote docker-compose up backend frontend

# Rebuild after code changes (local)
DB_MODE=local docker-compose --profile local up --build

# Rebuild after code changes (remote)
DB_MODE=remote docker-compose up backend frontend --build

# Stop (or just Ctrl+C)
docker-compose --profile local down   # local
docker-compose down                   # remote

# Stop + delete volumes (forces fresh seed on next start)
docker-compose --profile local down -v
```

**View logs:**
```bash
docker-compose logs -f backend    # Follow backend logs
docker-compose logs -f            # Follow all service logs
docker-compose logs seeder        # Check seeder output (local profile only)
```

**Re-seed database** (if backup is missing or you need fresh data):
```bash
# Force re-download from AWS RDS
docker-compose --profile local run --rm seeder seed --force

# Check if backup exists
ls -la apps/backend/data/
```

> **Note**: The seeder downloads ~5k movies from AWS RDS and saves to `apps/backend/data/seed_backup.sql.gz`. If this file is missing, run the force command above.

**Clear Docker cache:**
```bash
docker system prune -a    # Remove ALL unused images, containers, networks (frees disk space)
docker volume prune       # Remove unused volumes
docker builder prune      # Clear build cache
```

### Option 2: AWS RDS Database (Production/Staging)

Connect to your AWS RDS instance instead of local Docker MySQL.

```bash
# Clone and configure
git clone <repository-url>
cd Monorepo
cp .env.example .env

# Edit .env with your AWS RDS credentials:
#   REMOTE_SQL_HOST=your-rds-endpoint.region.rds.amazonaws.com
#   REMOTE_SQL_USER=your_rds_username
#   REMOTE_SQL_PASS=your_rds_password

# Start without local database - runs interactively (Ctrl+C to stop)
DB_MODE=remote docker-compose up backend frontend
```

**Local URLs:**
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/api/docs |

### Option 3: Manual Setup (No Docker)

For development without Docker.

#### Database (choose one)

```bash
# Local Docker MySQL (requires seed file - see Option 1)
docker run -d --name mysql \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=tmdb \
  -p 3306:3306 \
  -v $(pwd)/docker/mysql/init:/docker-entrypoint-initdb.d:ro \
  mysql:8

# Or use AWS RDS (see Option 2)
```

#### Backend

```bash
cd apps/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

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

### Switching Databases

Set `DB_MODE` when running docker-compose:

| Command | Database | Best For |
|---------|----------|----------|
| `DB_MODE=local docker-compose --profile local up` | Docker MySQL (LOCAL_SQL_*) | Development |
| `DB_MODE=remote docker-compose up backend frontend` | AWS RDS (REMOTE_SQL_*) | Production |

## Environment Variables

See [.env.example](.env.example) for the complete template with inline instructions.

### TMDB API (Backend)

| Variable | How to Get |
|----------|------------|
| `API_KEY` | 1. Create account at [themoviedb.org](https://www.themoviedb.org/signup)<br>2. Go to **Settings > API**<br>3. Click **Create** > **Developer** > Accept terms<br>4. Copy **API Key (v3 auth)** |
| `TMDB_BEARER_TOKEN` | Same page as above, copy **API Read Access Token (v4 auth)** |

### MySQL Database

Set `DB_MODE=local` or `DB_MODE=remote` when running docker-compose.

| Variable | Description |
|----------|-------------|
| `LOCAL_SQL_*` | Local Docker database credentials (used with `DB_MODE=local`) |
| `REMOTE_SQL_*` | AWS RDS credentials (used with `DB_MODE=remote`) |

See [.env.example](.env.example) for all database variables.

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
