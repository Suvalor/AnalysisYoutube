# YouTube Compass

**YouTube出海决策工具 — 30秒告诉你做什么品类**

YouTube Compass helps you discover untapped YouTube market opportunities before you start creating. Find low-subscriber channels with viral content, compare markets across regions, and get AI-powered strategy recommendations.

## Core Features

| Feature | Description |
|---------|-------------|
| **Blue Ocean Radar** | Discover channels with low subscribers but high viral outlier scores — the strongest signal of untapped opportunity |
| **Category Opportunity Report** | Analyze any niche: top channel growth trends, content supply gaps, newcomer success rates |
| **Cross-Region Compare** | Compare the same keyword across US/SEA/ME markets side by side |
| **Navigation Guide** | Input your resources (languages, budget, format) → get recommended category+region combos with Top channel strategy breakdowns |
| **Competitor Analysis** | Compare 2-3 channels' growth trends, view distributions, and engagement metrics |
| **Channel Management** | Track and analyze YouTube channels you follow |
| **Video Board** | Kanban-style video data dashboard |

## Quick Start

### Prerequisites
- Node.js 18+, Python 3.11+, MySQL 8.0
- YouTube Data API v3 key

### Backend
```shell
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```shell
cd frontend
npm install
npm run dev    # Vite dev server on :5173, proxies /api → localhost:8000
```

### Docker
```shell
docker compose up -d mysql backend
docker compose exec backend alembic upgrade head   # run migrations
```

## Feature Flags

Creator modules (Inspiration Pool, AI Script Workshop, SOP Workflow, Asset Library, Knowledge Base, Feishu Docs) are hidden by default. Enable them via environment variables:

```
VITE_FEATURE_INSPIRATION=true
VITE_FEATURE_AI_CREATOR=true
VITE_FEATURE_SOP=true
VITE_FEATURE_ASSETS=true
VITE_FEATURE_KNOWLEDGE=true
VITE_FEATURE_FEISHU=true
```

## Tech Stack

- **Frontend**: React 18 · Vite · TypeScript · Ant Design · Tailwind CSS · Zustand
- **Backend**: FastAPI · async SQLAlchemy · asyncmy (MySQL) · Alembic
- **AI**: Volcengine/Ark LLM (OpenAI-compatible) with conversation memory
- **Storage**: Aliyun OSS + Tencent COS (multi-cloud)
- **API**: YouTube Data API v3 with quota tracking

## License

Proprietary
