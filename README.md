# YouTube Compass

**YouTube 出海决策工具 -- 30 秒告诉你做什么品类**

[English](./README_EN.md)

YouTube Compass 帮助你在创作前发现未被充分开发的 YouTube 市场机会。找到低订阅但高爆款系数的频道，跨地区对比市场，获取 AI 驱动的策略建议。

## 特性

| 功能 | 说明 |
|------|------|
| 蓝海雷达 | 发现低订阅但高爆款系数的频道 -- 未被开发机会的最强信号 |
| 品类机会报告 | 分析任意细分市场：头部频道增速、内容供给缺口、新入局者成功率 |
| 跨地区对比 | 同一关键词在 US/SEA/ME 等市场横向对比 |
| 出海导航 | 输入资源（语言、预算、形式）-> 推荐品类+地区组合 + Top 频道策略拆解 |
| 竞对洞察 | 对比 2-3 个频道的增长趋势、播放分布和互动指标，AI 生成竞争格局分析 |
| 频道管理 | 追踪和分析你关注的 YouTube 频道 |
| 视频看板 | 看板式视频数据管理 + AI 内容策略建议 |
| AI 参数自迭代 | 蓝海雷达参数自动复盘、持久化、回填，形成优化闭环 |

## 截图

<!-- TODO: 替换为真实截图 -->
> 截图占位：蓝海雷达主界面 / 竞对洞察对比页 / 视频看板

## 快速开始（Docker 一键部署）

**前置条件**：Docker & Docker Compose

```shell
# 1. 克隆仓库
git clone https://github.com/<owner>/youtube-compass.git
cd youtube-compass

# 2. 复制并编辑环境变量（必须填入 SECRET_KEY、DATABASE_URL）
cp .env.example .env

# 3. 启动服务
docker compose up -d

# 4. 执行数据库迁移
docker compose exec backend alembic upgrade head

# 5. 访问
#    前端：http://localhost:5173（需单独启动，见下方手动安装）
#    后端 API 文档：http://localhost:8000/docs
```

> 将 `<owner>` 替换为实际的 GitHub 用户名或组织名。

> Docker Compose 当前仅包含 MySQL + Backend。前端需手动启动或自行添加前端服务。

## 手动安装

### 后端

```shell
cd backend

# 创建虚拟环境
python -m venv .venv && source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

### 前端

```shell
cd frontend

# 安装依赖
npm install

# 启动开发服务器（:5173，自动代理 /api -> localhost:8000）
npm run dev

# 生产构建
npm run build
```

## 环境变量配置

复制 `.env.example` 为 `.env` 并填入实际值：

```shell
cp .env.example .env
```

### 最小配置（必须设置）

| 变量 | 说明 |
|------|------|
| `SECRET_KEY` | JWT 签名密钥，生产环境务必使用强随机字符串（>= 32 字符） |
| `DATABASE_URL` | MySQL 连接串，格式：`mysql+asyncmy://user:pass@host:3306/db` |

### 完整配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| **数据库** | | |
| `MYSQL_USER` | MySQL 用户名 | - |
| `MYSQL_PASSWORD` | MySQL 密码 | - |
| `MYSQL_HOST` | MySQL 主机 | localhost |
| `MYSQL_PORT` | MySQL 端口 | 3306 |
| `MYSQL_DB` | 数据库名 | creator_saas |
| `DATABASE_URL` | 完整连接串（优先于上面的单独字段） | - |
| **认证** | | |
| `SECRET_KEY` | JWT 签名密钥（必填） | - |
| `FIELD_ENCRYPTION_SECRET` | 字段加密盐（可选，未设置回退 SECRET_KEY） | - |
| `ALGORITHM` | JWT 算法 | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间（分钟） | 1440 |
| **CORS** | | |
| `BACKEND_CORS_ORIGINS` | 允许的前端地址，逗号分隔 | http://localhost:5173 |
| **对象存储** | | |
| `ACTIVE_STORAGE_PROVIDER` | 存储提供商：ALIYUN / TENCENT | TENCENT |
| `ALIYUN_ACCESS_KEY_ID` | 阿里云 AccessKey ID | - |
| `ALIYUN_ACCESS_KEY_SECRET` | 阿里云 AccessKey Secret | - |
| `ALIYUN_OSS_BUCKET_NAME` | OSS Bucket 名称 | - |
| `ALIYUN_OSS_ENDPOINT` | OSS Endpoint | - |
| `ALIYUN_CUSTOM_DOMAIN` | OSS 自定义域名 | - |
| `TENCENT_COS_SECRET_ID` | 腾讯云 SecretId | - |
| `TENCENT_COS_SECRET_KEY` | 腾讯云 SecretKey | - |
| `TENCENT_COS_REGION` | COS 区域 | ap-guangzhou |
| `TENCENT_COS_BUCKET` | COS Bucket 名称 | - |
| `TENCENT_CUSTOM_DOMAIN` | COS 自定义域名 | - |
| **邮件（可选）** | | |
| `SMTP_HOST` | SMTP 服务器 | - |
| `SMTP_PORT` | SMTP 端口 | 465 |
| `SMTP_USER` | SMTP 用户名 | - |
| `SMTP_PASSWORD` | SMTP 密码 | - |
| `SMTP_FROM_EMAIL` | 发件人地址 | - |
| `FRONTEND_BASE_URL` | 前端地址（用于生成重置链接） | http://localhost:5173 |
| **其他（可选）** | | |
| `DOWNLOAD_PROXY` | yt-dlp 下载代理 | - |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth 客户端 ID | - |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth 客户端密钥 | - |
| **火山引擎 CV（可选）** | | |
| `VOLC_CV_ACCESS_KEY_ID` | 火山引擎 CV AccessKey ID | - |
| `VOLC_CV_SECRET_ACCESS_KEY` | 火山引擎 CV SecretAccessKey | - |
| `VOLC_CV_REGION` | 火山引擎 CV 区域 | cn-north-1 |
| `VOLC_CV_HOST` | 火山引擎 CV Host | - |
| `VOLC_CV_INPAINT_REQ_KEY` | 火山引擎 CV Inpainting 请求 Key | i2i_inpainting |

### 前端环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 地址 | http://localhost:8000 |
| `VITE_FEATURE_INSPIRATION` | 启用灵感池模块 | false |
| `VITE_FEATURE_AI_CREATOR` | 启用 AI 脚本工坊 | false |
| `VITE_FEATURE_SOP` | 启用 SOP 工作流 | false |
| `VITE_FEATURE_ASSETS` | 启用素材库 | false |
| `VITE_FEATURE_KNOWLEDGE` | 启用知识库 | false |
| `VITE_FEATURE_FEISHU` | 启用飞书文档 | false |

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18, Vite, TypeScript, Ant Design, Tailwind CSS, Zustand |
| 后端 | FastAPI (Python 3.11), async SQLAlchemy, asyncmy, Alembic |
| 数据库 | MySQL 8.0 |
| AI/LLM | 火山引擎/Ark (OpenAI 兼容协议)，对话记忆 |
| 存储 | 阿里云 OSS + 腾讯云 COS（多云切换） |
| 外部 API | YouTube Data API v3（配额追踪） |
| 定时任务 | APScheduler |

## 项目结构

```
youtube-compass/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/           # 路由（领域分模块）
│   │   ├── core/             # 配置、安全、依赖注入
│   │   ├── crud/             # 数据库 CRUD 操作
│   │   ├── db/               # 数据库连接、基类
│   │   ├── models/           # SQLAlchemy 模型
│   │   ├── schemas/          # Pydantic 请求/响应模型
│   │   └── services/         # 业务逻辑层
│   ├── alembic/              # 数据库迁移
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── components/       # 通用组件
│   │   ├── config/           # Feature Flags 等配置
│   │   ├── hooks/            # 自定义 Hooks
│   │   ├── pages/            # 页面组件
│   │   ├── services/         # API 客户端
│   │   ├── store/            # Zustand 状态管理
│   │   └── themes/           # 主题系统
│   ├── Dockerfile
│   └── vite.config.ts
├── docker-compose.yml
├── .env.example
├── LICENSE
└── CONTRIBUTING.md
```

## License

本项目采用 [Business Source License 1.1](./LICENSE) 授权。

- 2028-05-08 前：允许非商用自部署（个人项目、教育、研究和内部业务使用），禁止作为第三方服务提供
- 2028-05-08 后：自动转为 GPLv3

## 贡献

欢迎贡献！请阅读 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解如何参与。
