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

# Start everything (first run seeds from AWS RDS, ~1-2 minutes)
make up-local
```

This outputs:
```
=========================================
  Services are starting...
=========================================

  Frontend:   http://localhost:3000
  Backend:    http://localhost:8000
  API Docs:   http://localhost:8000/api/docs
  MySQL:      localhost:3306

=========================================
```

> **Note**: First run automatically pulls ~5k movies from AWS RDS. Subsequent runs are instant since data persists in Docker volume.

> **How it works**: The `db` and `seeder` services use Docker Compose profiles. `make up-local` activates the `local` profile, starting all services. `make up-remote` skips the profile, starting only backend + frontend.

**Re-seed database** (after schema changes or to get fresh data):
```bash
docker-compose --profile local run --rm seeder --force    # Re-seed with fresh data from AWS
```

**Daily development (local DB):**
```bash
make up-local       # Start all services with local MySQL
make down-local     # Stop all services (data persists)
make restart-local  # Restart all services
make clean-local    # Stop + delete volumes + prune
make logs           # Follow container logs
```

**Daily development (remote DB):**
```bash
make up-remote       # Start frontend + backend only (uses AWS RDS)
make down-remote     # Stop frontend + backend
make restart-remote  # Restart frontend + backend
make clean-remote    # Stop + remove frontend + backend containers
```

**View logs:**
```bash
docker-compose --profile local logs seeder   # Seeder output (local profile only)
docker-compose logs backend                  # API logs
docker-compose logs -f backend               # Follow logs in real-time
```

**Clear Docker cache:**
```bash
docker system prune       # Remove unused containers, networks, images
docker system prune -a    # Remove ALL unused images (reclaim disk space)
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

# Edit .env:
#   DB_MODE=remote
#   REMOTE_SQL_HOST=your-rds-endpoint.region.rds.amazonaws.com
#   REMOTE_SQL_USER=your_rds_username
#   REMOTE_SQL_PASS=your_rds_password

# Start without local database
make up-remote
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

# Or use AWS RDS (set DB_MODE=remote in .env)
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

Just change `DB_MODE` in `.env`:

```env
DB_MODE=local   # Uses LOCAL_SQL_* variables (Docker MySQL)
DB_MODE=remote  # Uses REMOTE_SQL_* variables (AWS RDS)
```

| Mode | Command | Best For |
|------|---------|----------|
| `DB_MODE=local` | `make up-local` | Development |
| `DB_MODE=remote` | `make up-remote` | Production |

## Environment Variables

See [.env.example](.env.example) for the complete template with inline instructions.

### TMDB API (Backend)

| Variable | How to Get |
|----------|------------|
| `API_KEY` | 1. Create account at [themoviedb.org](https://www.themoviedb.org/signup)<br>2. Go to **Settings > API**<br>3. Click **Create** > **Developer** > Accept terms<br>4. Copy **API Key (v3 auth)** |
| `TMDB_BEARER_TOKEN` | Same page as above, copy **API Read Access Token (v4 auth)** |

### MySQL Database

Use `DB_MODE` to switch between local Docker and AWS RDS:

| Variable | Description |
|----------|-------------|
| `DB_MODE` | `local` (Docker MySQL) or `remote` (AWS RDS) |
| `LOCAL_SQL_*` | Local Docker database credentials (used when `DB_MODE=local`) |
| `REMOTE_SQL_*` | AWS RDS credentials (used when `DB_MODE=remote`) |

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
