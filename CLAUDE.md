# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Compass — a YouTube overseas decision tool. Helps users discover untapped market opportunities before creating content. Bilingual codebase (Chinese primary, English secondary).

## Architecture

**Frontend** (`frontend/`): React 18 + Vite + TypeScript + Ant Design + Tailwind CSS. State via Zustand. Browser-like tabbed shell (`TabbedShell`) with sidebar navigation; tabs managed in `useTabStore`. Path alias `@/` → `src/`. API calls go through `src/services/apiClient.ts` (axios with JWT interceptor, 120s timeout).

**Backend** (`backend/`): FastAPI (Python 3.11) under `/api` prefix. Async SQLAlchemy + asyncmy (MySQL). Alembic for migrations. Domain-driven router split in `app/api/v1/`. Service layer in `app/services/`; CRUD in `app/crud/`; Pydantic schemas in `app/schemas/`. Auth: JWT (OAuth2PasswordBearer) with `CurrentUserDep` dependency injection. Settings from env vars via pydantic-settings (`app/core/config.py`).

**Database**: MySQL 8.0. All models inherit `Base` from `app/db/base_class.py`. Sessions via async `get_session()` dependency.

**External APIs**: YouTube Data API v3 (quota-tracked in `quota_service.py`), Volcengine/Ark LLM (OpenAI-compatible), Aliyun OSS + Tencent COS (multi-cloud storage), Volcengine CV (image inpainting).

## Key Commands

### Backend (local dev)
```shell
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (local dev)
```shell
cd frontend
npm install
npm run dev          # Vite dev server on :5173, proxies /api → localhost:8000
npm run build        # production build
```

### Docker
```shell
docker compose up -d mysql backend          # start MySQL + backend
docker compose up --build -d                # full rebuild
docker compose exec backend alembic upgrade head   # run migrations
docker compose exec backend alembic revision --autogenerate -m "desc"  # new migration
```

### Database migrations
```shell
cd backend
alembic upgrade head                         # apply all
alembic revision --autogenerate -m "desc"    # generate from model changes
```

## Important Patterns

- **API prefix**: All backend routes are under `/api`. Frontend `apiClient` base URL should NOT end with `/api` (it strips it automatically). `VITE_API_BASE_URL` points to backend origin only.
- **Data isolation**: Users belong to an `org_id`; integration configs (YouTube, cloud storage) are org-level. Business resources use `current_user.id` for row-level isolation.
- **Feature Flags**: `frontend/src/config/features.ts` controls module visibility. Core modules always on; creator modules (Inspiration, AI Script, SOP, Assets, Knowledge, Feishu) default off, toggled via `VITE_FEATURE_*` env vars. Navigation in `TabbedShell.tsx` filters `navDefs` through `isFeatureEnabled()`.
- **Default landing page**: `/blue-ocean-radar` (not `/dashboard`).
- **Radar API family** (`/api/radar/`): `/scan` (deep scan), `/ai-retrospective` (AI parameter review), `/category-opportunity` (niche opportunity report), `/cross-region-compare` (multi-region comparison), `/export-report` (Markdown report generation), `/navigation-guide` (resource-based category+region recommendations).
- **YouTube quota**: Each `search.list` call costs ~100 quota units. Tracked per-request in `quota_service.py`.
- **LLM conversation memory**: `llm_conversation` table stores per-entity conversation history. Service layer in `llm_conversation_service.py` with auto-truncation (DEFAULT_MAX_CHARS=8000) and auto-pruning (DEFAULT_MAX_TURNS=20). Entity types: `script`, `ai_script`, `channel_ai`, `radar_retro`, `sop_split`.
- **Multi-cloud storage**: Active provider set via `ACTIVE_STORAGE_PROVIDER` env var (ALIYUN or TENCENT). New uploads default to Tencent COS.
- **Frontend tab system**: `TabbedShell` renders a browser-like tab bar. Each nav item opens a tab via `useTabStore`. Dynamic tabs (channel detail, feishu viewer) matched by URL pattern.
- **No linter configured**: Frontend `npm run lint` is a no-op echo. No backend linter config found.
 - **LLM 集成规则**：本项目已集成 LLM（Volcengine/Ark OpenAI 兼容协议），所有 LLM
    调用必须通过配置中心（`model_libraries` 表）获取 API Key、Base URL
    和模型配置，禁止硬编码或绕过配置中心。调用流程：`resolve_integration_config(db,
    org_id)` 获取组织级配置 → `get_by_user(db, ModelLibrary, user_id,                 
    model_library_id)` 获取模型库配置 → `try_decrypt(ml.api_key_encrypted)` 解密 API
    Key → `LLMClientFactory().chat_completions_content(cfg=LLMClientConfig(...))`     
    发起调用。协议感知由 `llm_openai_factory.py` 自动处理（Coding Plan URL
    自动注入默认模型等）。



## Environment Variables

Backend reads from `.env` (see `backend/.env.example`). Critical ones:
- `DATABASE_URL` or `MYSQL_*` group for DB connection
- `YOUTUBE_API_KEY` — YouTube Data API v3
- `VOLCENGINE_API_KEY`, `VOLCENGINE_ENDPOINT_ID` — LLM (Ark platform)
- `ALIYUN_*` — Aliyun OSS storage
- `TENCENT_COS_*` — Tencent COS storage
- `SECRET_KEY` — JWT signing (default empty, must be set in production)

Frontend: `VITE_API_BASE_URL` (defaults to `http://localhost:8000`), `VITE_FEATURE_*` flags for creator modules.