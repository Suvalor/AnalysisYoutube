# YouTube Compass

**YouTube Overseas Decision Tool — Find your niche in 30 seconds**

[中文](./README.md)

YouTube Compass helps you discover untapped YouTube market opportunities before you start creating. Find low-subscriber channels with viral outlier scores, compare markets across regions, and get AI-powered strategy recommendations.

### Features

| Feature | Description |
|---------|-------------|
| Blue Ocean Radar | Discover channels with low subscribers but high viral outlier scores |
| Category Opportunity Report | Analyze any niche: growth trends, content gaps, newcomer success rates |
| Cross-Region Compare | Compare the same keyword across US/SEA/ME markets side by side |
| Navigation Guide | Input your resources -> get category+region recommendations with strategy breakdowns |
| Competitor Insight | Compare 2-3 channels with AI-generated competitive landscape analysis |
| Channel Management | Track and analyze YouTube channels you follow |
| Video Board | Kanban-style video data management + AI content strategy |
| AI Parameter Self-Iteration | Automatic radar parameter retrospective and optimization loop |

### Screenshots

<!-- TODO: Replace with actual screenshots -->
> Screenshot placeholder: Blue Ocean Radar / Competitor Insight / Video Board

### Quick Start (Docker)

**Prerequisites**: Docker & Docker Compose

```shell
# 1. Clone the repo
git clone https://github.com/<owner>/youtube-compass.git
cd youtube-compass

# 2. Copy and edit environment variables (SECRET_KEY, DATABASE_URL, YOUTUBE_API_KEY are required)
cp .env.example .env

# 3. Start services
docker compose up -d

# 4. Run database migrations
docker compose exec backend alembic upgrade head

# 5. Access
#    Frontend: http://localhost:5173 (start separately, see Manual Install below)
#    Backend API docs: http://localhost:8000/docs
```

> Replace `<owner>` with the actual GitHub username or organization name.

> Docker Compose currently includes MySQL + Backend only. Start the frontend separately or add a frontend service.

### Manual Install

#### Backend

```shell
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```shell
cd frontend
npm install
npm run dev          # dev server on :5173, proxies /api -> localhost:8000
npm run build        # production build
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```shell
cp .env.example .env
```

#### Minimum Configuration (required)

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (strong random string >= 32 chars) |
| `DATABASE_URL` | MySQL connection string: `mysql+asyncmy://user:pass@host:3306/db` |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key |

#### Full Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| **Database** | | |
| `MYSQL_USER` | MySQL username | - |
| `MYSQL_PASSWORD` | MySQL password | - |
| `MYSQL_HOST` | MySQL host | localhost |
| `MYSQL_PORT` | MySQL port | 3306 |
| `MYSQL_DB` | Database name | creator_saas |
| `DATABASE_URL` | Full connection string (overrides individual fields) | - |
| **Auth** | | |
| `SECRET_KEY` | JWT signing key (required) | - |
| `FIELD_ENCRYPTION_SECRET` | Field encryption salt (optional, falls back to SECRET_KEY) | - |
| `ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry (minutes) | 1440 |
| **CORS** | | |
| `BACKEND_CORS_ORIGINS` | Allowed frontend origins, comma-separated | http://localhost:5173 |
| **YouTube** | | |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key | - |
| **Object Storage** | | |
| `ACTIVE_STORAGE_PROVIDER` | Storage provider: ALIYUN / TENCENT | TENCENT |
| `ALIYUN_ACCESS_KEY_ID` | Aliyun AccessKey ID | - |
| `ALIYUN_ACCESS_KEY_SECRET` | Aliyun AccessKey Secret | - |
| `ALIYUN_OSS_BUCKET_NAME` | OSS bucket name | - |
| `ALIYUN_OSS_ENDPOINT` | OSS endpoint | - |
| `ALIYUN_CUSTOM_DOMAIN` | OSS custom domain | - |
| `TENCENT_COS_SECRET_ID` | Tencent Cloud SecretId | - |
| `TENCENT_COS_SECRET_KEY` | Tencent Cloud SecretKey | - |
| `TENCENT_COS_REGION` | COS region | ap-guangzhou |
| `TENCENT_COS_BUCKET` | COS bucket name | - |
| `TENCENT_CUSTOM_DOMAIN` | COS custom domain | - |
| **Email (optional)** | | |
| `SMTP_HOST` | SMTP server | - |
| `SMTP_PORT` | SMTP port | 465 |
| `SMTP_USER` | SMTP username | - |
| `SMTP_PASSWORD` | SMTP password | - |
| `SMTP_FROM_EMAIL` | Sender address | - |
| `FRONTEND_BASE_URL` | Frontend URL (for password reset links) | http://localhost:5173 |
| **Other (optional)** | | |
| `DOWNLOAD_PROXY` | yt-dlp download proxy | - |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth client ID | - |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth client secret | - |
| **Volcengine CV (optional)** | | |
| `VOLC_CV_ACCESS_KEY_ID` | Volcengine CV AccessKey ID | - |
| `VOLC_CV_SECRET_ACCESS_KEY` | Volcengine CV SecretAccessKey | - |
| `VOLC_CV_REGION` | Volcengine CV region | cn-north-1 |
| `VOLC_CV_HOST` | Volcengine CV Host | - |
| `VOLC_CV_INPAINT_REQ_KEY` | Volcengine CV Inpainting request key | i2i_inpainting |

#### Frontend Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API address | http://localhost:8000 |
| `VITE_FEATURE_INSPIRATION` | Enable Inspiration module | false |
| `VITE_FEATURE_AI_CREATOR` | Enable AI Script Workshop | false |
| `VITE_FEATURE_SOP` | Enable SOP Workflow | false |
| `VITE_FEATURE_ASSETS` | Enable Asset Library | false |
| `VITE_FEATURE_KNOWLEDGE` | Enable Knowledge Base | false |
| `VITE_FEATURE_FEISHU` | Enable Feishu Docs | false |

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, TypeScript, Ant Design, Tailwind CSS, Zustand |
| Backend | FastAPI (Python 3.11), async SQLAlchemy, asyncmy, Alembic |
| Database | MySQL 8.0 |
| AI/LLM | Volcengine/Ark (OpenAI-compatible), conversation memory |
| Storage | Aliyun OSS + Tencent COS (multi-cloud) |
| External API | YouTube Data API v3 (quota-tracked) |
| Scheduler | APScheduler |

### Project Structure

```
youtube-compass/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/v1/           # Domain-routed API endpoints
│   │   ├── core/             # Config, security, dependencies
│   │   ├── crud/             # Database CRUD operations
│   │   ├── db/               # Database connection, base classes
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── services/         # Business logic layer
│   ├── alembic/              # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── components/       # Shared components
│   │   ├── config/           # Feature flags and config
│   │   ├── hooks/            # Custom hooks
│   │   ├── pages/            # Page components
│   │   ├── services/         # API client
│   │   ├── store/            # Zustand state management
│   │   └── themes/           # Theme system
│   ├── Dockerfile
│   └── vite.config.ts
├── docker-compose.yml
├── .env.example
├── LICENSE
└── CONTRIBUTING.md
```

### License

This project is licensed under the [Business Source License 1.1](./LICENSE).

- Before 2028-05-08: Non-commercial self-deployment allowed (personal projects, education, research, internal business use); providing as a third-party service is prohibited.
- After 2028-05-08: Automatically changes to GPLv3.

### Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) to get started.
