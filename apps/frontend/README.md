# Frontend

React.js web application for the movie recommendation site, built with Vite.

> **Note**: This is part of a monorepo. See the [root README](../../README.md) for full project documentation.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app runs at http://localhost:3000

## Available Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server with hot reload |
| `npm run build` | Build for production to `dist/` |
| `npm run preview` | Preview production build locally |

## Environment Variables

See the root [.env.example](../../.env.example) for configuration options. Vite uses `VITE_` prefix for environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API URL |

Access in code via `import.meta.env.VITE_*`.

## Project Structure

```
frontend/
├── index.html        # Entry HTML (Vite serves from root)
├── vite.config.js    # Vite configuration
├── src/
│   ├── components/   # React components
│   └── index.js      # App entry point
├── public/           # Static assets (favicon, etc.)
└── package.json
```

## Connecting to Backend

The frontend proxies API requests to the backend via Vite's dev server (configured in `vite.config.js`).

### Development

```bash
# Terminal 1: Start backend
cd ../backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: Start frontend
cd ../frontend
npm run dev
```

### Docker Compose

From the monorepo root:

```bash
make up-local   # Local development with Docker MySQL (uses --profile local)
make up-remote  # Production with AWS RDS (backend + frontend only)
```

> **Note**: `make up-local` activates the `local` profile which starts `db` and `seeder` services. `make up-remote` skips these.

This starts services and displays URLs:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/api/docs

## Tech Stack

- React 19
- React Router 7
- Material UI 7
- Firebase (authentication)
- Vite (build tool)

## Related Documentation

- [Backend API](../backend/api/README.md) - REST API endpoints and adding new routes
- [Root README](../../README.md) - Full project setup

## API Integration

The frontend communicates with the FastAPI backend through the following endpoint groups:

| Endpoint Group | Description |
|----------------|-------------|
| `/api/v1/users` | User management (Firebase auth, consent, import status) |
| `/api/v1/movies` | Movie browsing and recommendations |
| `/api/v1/users/{id}/watchlist` | User watchlist management |
| `/api/v1/users/{id}/ratings` | User ratings and likes |
| `/api/v1/users/{id}/import` | CSV import from Letterboxd |

See the [Backend API README](../backend/api/README.md) for full endpoint documentation and a guide on adding new routes.
