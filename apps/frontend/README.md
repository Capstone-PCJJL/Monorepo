# Frontend

React web application for the movie recommendation site, built with Vite.

> **Setup & Running**: See the [root README](../../README.md) for docker-compose commands and environment variables.

## Quick Start (without Docker)

```bash
npm install
npm run dev
```

App runs at http://localhost:3000

## Available Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server with hot reload |
| `npm run build` | Build for production to `dist/` |
| `npm run preview` | Preview production build locally |

## Project Structure

```
frontend/
├── index.html        # Entry HTML (Vite serves from root)
├── vite.config.js    # Vite configuration (proxy to backend)
├── src/
│   ├── components/   # React components
│   └── index.js      # App entry point
├── public/           # Static assets
└── package.json
```

## Tech Stack

- React 19
- React Router 7
- Material UI 7
- Firebase Authentication
- Vite

## API Integration

The frontend proxies API requests to the backend via Vite's dev server. See [Backend API docs](../backend/api/README.md) for endpoints:

| Endpoint Group | Description |
|----------------|-------------|
| `/api/v1/movies` | Movie browsing and search |
| `/api/v1/users` | User management |
| `/api/v1/users/{id}/watchlist` | Watchlist management |
| `/api/v1/users/{id}/ratings` | Ratings and likes |
