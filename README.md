# FreightAgent MVP

Minimal standalone MVP extracted from the main repo.

## Included
- `backend/`: FastAPI API for login, email parsing, persistent carrier management, quote history, and Excel generation
- `frontend/`: React + Vite client for login, parsing, and Excel download
- `.nvmrc`: recommended Node version (`22.12.0`)

## Not Included
- `outlook-mcp/`
- `node_modules/`
- `dist/`
- generated Excel files
- real `.env` files or secrets

## Quick Start

### Backend
```powershell
cd backend
Copy-Item .env.example .env
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### Frontend
```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Frontend expects the API at `http://localhost:8001`.

If `VITE_API_URL` is unset, the frontend uses same-origin requests. That works with the local Vite proxy and is also safe for tunneled local testing.

## Demo Login
- Username: `ADMIN`
- Password: `fuzzysheep`

## Notes
- Add a valid `ANTHROPIC_API_KEY` to `backend/.env` before testing parse flow.
- Backend defaults to port `8001`.
- Backend now persists carriers and generated quote records to a local SQLite database at `backend/freightagent.db` by default.
- Default CORS allows both `localhost` and `127.0.0.1` on the common frontend dev ports.
- The backend tolerates `DEBUG=release` in the parent shell by normalizing it to `False`.

## Deployment

### Recommended stack
- Backend: Render web service
- Database: Render Postgres
- Frontend: Vercel project with `frontend/` as the root directory

### Render
- This repo includes [render.yaml](/c:/Users/Curt/Desktop/FreightAgent-MVP/render.yaml) for the backend and database.
- The backend service runs from `backend/` and starts with `uvicorn`.
- `DATABASE_URL` is sourced from the Render Postgres instance.
- You must provide `ANTHROPIC_API_KEY` in Render.
- You must set `CORS_ORIGINS` in Render to your deployed Vercel URL, for example `https://your-project.vercel.app`.
- The backend accepts `CORS_ORIGINS` as either JSON array syntax or a comma-separated string.

### Vercel
- Set the Vercel project root to `frontend/`.
- [frontend/vercel.json](/c:/Users/Curt/Desktop/FreightAgent-MVP/frontend/vercel.json) adds SPA rewrites so direct route loads resolve to `index.html`.
- Set `VITE_API_URL` in Vercel to your Render backend URL, for example `https://freightagent-api.onrender.com`.

### Production caveats
- Generated Excel files are written to local server disk before being served. That is acceptable for test hosting, but not durable storage.
- For a more production-ready setup, move generated files to object storage instead of server-local disk.
