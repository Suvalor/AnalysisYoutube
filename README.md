# YouTube Compass

**YouTube 出海决策工具 — 30 秒告诉你做什么品类**

[English](./README_EN.md)

YouTube Compass 帮助你在创作前发现未被充分开发的 YouTube 市场机会。找到低订阅但高爆款系数的频道，跨地区对比市场，获取 AI 驱动的策略建议。

## 核心功能

| 功能 | 说明 |
|------|------|
| **蓝海雷达** | 发现低订阅但高爆款系数的频道 — 未被开发机会的最强信号 |
| **品类机会报告** | 分析任意细分市场：头部频道增速、内容供给缺口、新入局者成功率 |
| **跨地区对比** | 同一关键词在 US/SEA/ME 等市场横向对比 |
| **出海导航** | 输入你的资源（语言、预算、形式）→ 推荐品类+地区组合 + Top 频道策略拆解 |
| **竞对洞察** | 对比 2-3 个频道的增长趋势、播放分布和互动指标，AI 生成竞争格局分析 |
| **频道管理** | 追踪和分析你关注的 YouTube 频道 |
| **视频看板** | 看板式视频数据管理 + AI 内容策略建议 |
| **AI 参数自迭代** | 蓝海雷达参数自动复盘、持久化、回填，形成优化闭环 |

## 快速开始

### 前置条件
- Node.js 18+、Python 3.11+、MySQL 8.0
- YouTube Data API v3 密钥

### 后端
```shell
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端
```shell
cd frontend
npm install
npm run dev    # Vite 开发服务器 :5173，代理 /api → localhost:8000
```

### Docker
```shell
docker compose up -d mysql backend
docker compose exec backend alembic upgrade head   # 执行数据库迁移
```

## Feature Flags

创作者模块（灵感池、AI 脚本工坊、SOP 工作流、素材库、知识库、飞书文档）默认隐藏，通过环境变量启用：

```
VITE_FEATURE_INSPIRATION=true
VITE_FEATURE_AI_CREATOR=true
VITE_FEATURE_SOP=true
VITE_FEATURE_ASSETS=true
VITE_FEATURE_KNOWLEDGE=true
VITE_FEATURE_FEISHU=true
```

## 技术栈

- **前端**：React 18 · Vite · TypeScript · Ant Design · Tailwind CSS · Zustand
- **后端**：FastAPI · async SQLAlchemy · asyncmy (MySQL) · Alembic
- **AI**：火山引擎/Ark LLM（OpenAI 兼容）+ 对话记忆
- **存储**：阿里云 OSS + 腾讯云 COS（多云）
- **API**：YouTube Data API v3 + 配额追踪
- **定时任务**：APScheduler（频道同步 + 雷达自动复盘）

## License

Proprietary
