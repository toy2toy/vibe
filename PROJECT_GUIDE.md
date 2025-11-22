# Project Guide (Codex Rebuild Reference)

## Stack & Layout
- Backend: FastAPI (`backend/main.py`), SQLite (`backend/app.db`), SQLAlchemy models `Category` and `Item`.
- Frontend: static HTML/CSS/JS in `frontend/`, served via `python -m http.server`.
- Assets: per-category folders under `frontend/assets/<category-slug>/`; AI-generated item icons saved as `icon_ai_<item_id>.png`. Default fallback at `frontend/assets/default/icon.svg`.
- Project root: `codex/<project_name>/` containing `backend/`, `frontend/`, `requirements.txt`, `PROJECT_GUIDE.md`, `kickstart_vibe/`.

## Environment & Logging
- Set `AI_TOKEN` or `OPENAI_API_KEY` for OpenAI access. Optional `SEED_TOKEN` gates `POST /seed/ai` via `X-Seed-Token`.
- Logging format: `%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s` (applied in backend and seeder).

## Running
```bash
cd /Users/bytedance/codex
source codex_venv/bin/activate
python -m uvicorn backend.main:app --reload --port 8000
cd frontend && python -m http.server 4173
# open http://localhost:4173 (frontend expects API at http://localhost:8000)
```

## Seeding Data
- One-off script: `cd backend && OPENAI_API_KEY="$AI_TOKEN" python seed_ai.py`
- API trigger: `OPENAI_API_KEY="$AI_TOKEN" curl -X POST http://localhost:8000/seed/ai` (add `-H "X-Seed-Token: $SEED_TOKEN"` if set).
- Behavior: clears categories/items, asks ChatGPT for 5 categories and 4 items each, generates an icon per item via DALL·E 3. Icons saved to `frontend/assets/<category-slug>/icon_ai_<item_id>.png`.
- Notes: seeder throttles 120s before each image call to avoid rate limits. If quota/permission errors occur, icons fall back to the default placeholder.

## Frontend Behavior
- Tabs are built from `GET /categories`; items fetched from `GET /items` (optional `category_id` filter).
- Images load from `assets/<slug>/icon_ai_<item_id>.png`; on error they fall back to `assets/default/icon.svg`.
- Search filters client-side by item name.

## Rebuild Checklist
- Install deps in venv: `pip install -r requirements.txt`.
- Ensure env vars set (`AI_TOKEN`/`OPENAI_API_KEY`, optional `SEED_TOKEN`).
- Start backend, seed data, serve frontend, then refresh browser.
