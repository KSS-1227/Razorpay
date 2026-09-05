Deployment checklist
====================

This document lists the steps and required env vars to deploy the frontend to Vercel and the backend to Render.

Frontend (Vercel)
------------------
- Project: `frontend/`
- Build command: `npm run build`
- Output directory: `frontend/dist` (Vite produces `dist` at project root during build)
  - Vercel auto-detects Vite projects. Set Root to `frontend` in Vercel project settings.
- Environment variables to set in Vercel:
  - `VITE_API_BASE` -> backend public URL (e.g., `https://your-backend.onrender.com`)
  - `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` if using Supabase (already used by frontend)
- Recommended: set `NODE_ENV=production`.

Backend (Render)
-----------------
- Service type: Web Service (Python)
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT --workers 1` (Linux deployment)
- Environment variables to set in Render (minimum):
  - `COCKROACH_DATABASE_URL` (CockroachDB Cloud TLS connection string; apply the repository migration before the first upload)
  - `LLM_API_KEY` (OpenAI API key)
  - `MM_API_KEY` (OpenAI or same key)
  - `MM_API_BASE` (optional, defaults to `https://api.openai.com/v1`)
  - `ALLOWED_ORIGINS` (comma-separated list; include the Vercel frontend origin e.g. `https://your-app.vercel.app`)
  - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` (if using auth)
  - `OPENAI_API_KEY` (for Whisper/transcription usage) or rely on `LLM_API_KEY`
  - `DOCUMENT_STORAGE_BACKEND=local` (default) or `s3` for durable AWS S3 document copies
  - When using S3: `AWS_REGION`, `S3_DOCUMENT_BUCKET`, and a least-privilege IAM credential
- Attach a persistent disk for processing artefacts. With S3 enabled, raw uploads are mirrored to a private bucket; GraphML/cache files still use the disk.

CockroachDB setup
-----------------
1. Rotate the CockroachDB user password if it has ever been shared and create a new connection string.
2. Set `COCKROACH_DATABASE_URL` only in Render/local secret stores, never in a frontend `VITE_` variable.
3. Apply `backend/storage/migrations/001_cockroachdb_schema.sql` through the CockroachDB Cloud SQL shell or `psql` before ingestion.
4. Confirm the single intended vector index is `entity_embeddings_vector_idx`; inspect any other vector index in the Cloud console before removing it.

CORS and API base
------------------
- Ensure `ALLOWED_ORIGINS` includes the Vercel frontend domain, otherwise backend will refuse to start (startup guard).
- Set `VITE_API_BASE` in Vercel to the Render service URL so frontend fetches reach backend.

Other considerations
--------------------
- Secrets: add as Render environment variables (do not commit `.env`).
- Static assets: frontend build will create `dist/`; Vercel serves it.
- MinerU, YOLO weights, and other heavy binaries: these are not installed on Render by default. If you require MinerU, either:
  - bundle it into a Docker image and deploy to Render as a Docker service, or
  - configure Render to run setup commands to install MinerU on start (advanced).

Quick test (local)
------------------
1. Start backend locally:
```powershell
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m backend.api.run
```
2. Start frontend locally (from `frontend/`):
```bash
npm install
npm run dev
```
3. Set `VITE_API_BASE=http://localhost:8000` for the frontend dev server or rely on proxy in `vite.config.ts`.

If you want, I can:
- Create a minimal `render.yaml` for Render (Docker vs native), or
- Convert the backend into a Docker-based service to allow MinerU and custom system packages on Render.

*** End of document
