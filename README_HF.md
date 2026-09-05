---
title: InnovaHack Backend
emoji: 🧠
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
app_port: 7860
---

# InnovaHack — Enterprise Compliance Intelligence Backend

Multi-Modal Knowledge Graph RAG backend built with FastAPI + GraphRAG.

## Environment Variables

Set these as **Secrets** in your HuggingFace Space settings:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key for LLM + Vision |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `SUPABASE_JWT_SECRET` | Supabase JWT secret |
| `ALLOWED_ORIGINS` | Comma-separated frontend URLs (e.g. `https://your-app.vercel.app`) |
| `LLM_API_KEY` | Same as OPENAI_API_KEY |
| `MM_API_KEY` | Same as OPENAI_API_KEY |

## API

Health check: `GET /health`  
Docs: `GET /docs`
