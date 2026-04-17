# 架构设计文档

## 技术栈选型（含理由）

| 组件 | 选型 | 理由 |
|------|------|------|
| 定时任务 | APScheduler (已有依赖 3.10.4) | 项目已集成 scheduler_service.py，无需引入新依赖 |
| LLM 调用 | LLMClientFactory + 配置中心 | 复用现有体系，支持模型/智能体选择 |
| 数据库迁移 | Alembic | 项目标准迁移工具 |
| 前端状态 | Zustand | 项目标准状态管理 |
| 前端 UI | Ant Design + Tailwind | 项目标准 UI 框架 |

## 模块结构图

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                       │
├──────────────┬──────────────┬──────────────┬──────────────┤
│ Navigation   │ Competitor   │ Video Board  │ Blue Ocean   │
│ Guide        │ Insight      │              │ Radar       │
│ +关注按钮    │ +AI洞察     │ +AI建议     │ +参数闭环   │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                       │
├──────────────┬──────────────┬──────────────┬──────────────┤
│ /api/radar/  │ /api/        │ /api/        │ /api/radar/  │
│ navigation-  │ competitors/ │ video-       │ param-       │
│ guide        │ ai-insight   │ projects/    │ iteration    │
│ +follow      │              │ ai-suggest   │              │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────┐
│                    Service Layer                           │
├──────────────┬──────────────┬──────────────┬──────────────┤
│ youtube_     │ competitor_  │ video_board_ │ radar_param_ │
│ service      │ ai_service   │ ai_service   │ iteration_   │
│              │              │              │ service      │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────┐
│  MySQL (radar_param_iterations, llm_conversation, etc.)   │
└─────────────────────────────────────────────────────────┘
```

## 数据结构 / API 接口设计

### 1. radar_param_iterations 表（新增）

```sql
CREATE TABLE radar_param_iterations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    org_id VARCHAR(36) NOT NULL,
    iteration_type VARCHAR(20) NOT NULL DEFAULT 'auto',  -- auto/manual
    scan_params JSON NOT NULL,          -- 扫描参数快照
    recommended_params JSON,            -- AI推荐参数
    scan_result_summary JSON,           -- 扫描结果摘要
    iteration_effect JSON,              -- 迭代效果对比
    is_applied BOOLEAN DEFAULT FALSE,   -- 是否已应用到下次扫描
    applied_at DATETIME,                -- 应用时间
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 2. API 接口设计

#### 出海导航一键关注
- **POST** `/api/radar/navigation-guide/follow` — 关注推荐频道
  - 入参: `{ channel_id, channel_title, thumbnail }`
  - 出参: `{ success: bool, message: str, already_followed: bool }`
  - 逻辑: 调用 analyzeYouTubeBatchApi 入库，检查是否已关注

#### 蓝海雷达参数迭代
- **GET** `/api/radar/param-iterations/latest` — 获取最新推荐参数
  - 入参: 无（从 current_user 获取）
  - 出参: `{ recommended_params: dict, iteration_count: int, last_iteration_at: str }`

- **POST** `/api/radar/param-iterations` — 保存迭代记录
  - 入参: `{ scan_params, recommended_params, scan_result_summary }`
  - 出参: `{ id, created_at }`

- **GET** `/api/radar/param-iterations` — 查询迭代历史
  - 入参: `?limit=20&offset=0`
  - 出参: `{ items: [...], total: int }`

- **POST** `/api/radar/param-iterations/apply/{id}` — 应用某次迭代参数
  - 入参: 无
  - 出参: `{ success: bool }`

- **POST** `/api/radar/param-iterations/auto-retro` — 手动触发自动复盘
  - 入参: `{ force: bool }` (force=True 忽略周期限制)
  - 出参: `{ iteration_id, recommended_params }`

#### 竞对洞察 AI 洞察
- **POST** `/api/competitors/ai-insight` — 生成 AI 竞争分析
  - 入参: `{ channel_ids: list[str], model_config_id?: str, agent_id?: str }`
  - 出参: `{ insight: str, conversation_id: str }`

#### 视频看板 AI 建议
- **POST** `/api/video-projects/ai-suggest` — 生成 AI 策略建议
  - 入参: `{ project_ids?: list[str], model_config_id?: str, agent_id?: str }`
  - 出参: `{ suggestion: str, conversation_id: str }`

## 文件组织结构

### Backend 新增/修改文件

```
backend/
├── app/
│   ├── models/
│   │   └── radar_param_iteration.py      # 新增：参数迭代模型
│   ├── schemas/
│   │   └── radar_param_iteration.py      # 新增：参数迭代 Pydantic schemas
│   ├── services/
│   │   ├── radar_param_iteration_service.py  # 新增：参数迭代服务
│   │   ├── competitor_ai_service.py      # 新增：竞对AI洞察服务
│   │   └── video_board_ai_service.py     # 新增：视频看板AI建议服务
│   ├── api/v1/
│   │   ├── radar.py                      # 修改：新增参数迭代路由
│   │   ├── youtube.py                    # 修改：新增竞对AI洞察路由
│   │   └── video_projects.py             # 修改：新增AI建议路由
│   └── services/
│       └── scheduler_service.py          # 修改：新增定时复盘任务
├── alembic/versions/
│   └── xxx_add_radar_param_iterations.py  # 新增：数据库迁移
```

### Frontend 新增/修改文件

```
frontend/src/
├── pages/
│   ├── radar/
│   │   ├── NavigationGuide.tsx           # 修改：ChannelBreakdownCard 加关注按钮
│   │   ├── BlueOceanRadar.tsx            # 修改：参数自动回填+迭代历史
│   │   └── RadarParamIteration.tsx        # 新增：迭代历史面板
│   ├── youtube/
│   │   └── CompetitorAnalysis.tsx         # 修改：加AI洞察按钮
│   └── board/
│       └── VideoBoard.tsx                 # 修改：加AI建议区域
├── services/
│   └── authApi.ts                        # 修改：新增API调用方法
└── store/
    └── useRadarParamStore.ts              # 新增：参数迭代状态管理
```

### README 文件

```
README.md          # 中文版（重写）
README_EN.md       # 英文版（新增）
```

## 风险登记册（技术层面）

| # | 风险 | 影响 | 应对方案 |
|---|------|------|----------|
| R1 | APScheduler 定时任务在多 worker 下重复执行 | 失败扫描/重复 LLM 调用 | 使用 MySQL 行锁确保单实例执行 |
| R2 | LLM 调用失败导致迭代中断 | 参数无法自动更新 | 异常捕获 + 失败重试 + 降级（使用上次参数） |
| R3 | 参数自动回填覆盖用户手动调整 | 用户体验差 | 优先级：用户手动 > 自动推荐；回填前检查用户是否手动修改过 |
| R4 | YouTube API 配额耗尽 | 定时复盘扫描失败 | 配额检查前置，配额不足时跳过扫描并通知用户 |

## WBS 任务分解

### WBS-1：出海导航一键关注（P0）
- WBS-1.1：后端 — 新增 `/api/radar/navigation-guide/follow` 接口
- WBS-1.2：前端 — ChannelBreakdownCard 加关注按钮 + 状态管理
- WBS-1.3：前端 — 已关注频道按钮置灰逻辑

### WBS-2：蓝海雷达 AI 参数全自动闭环（P0）
- WBS-2.1：数据库 — 新建 radar_param_iterations 表 + Alembic 迁移
- WBS-2.2：后端 — 参数迭代 CRUD 服务 + API 路由
- WBS-2.3：后端 — 复盘推荐参数自动持久化逻辑
- WBS-2.4：后端 — 扫描接口自动回填最新推荐参数
- WBS-2.5：后端 — 定时复盘任务（APScheduler 集成）
- WBS-2.6：前端 — 扫描页面参数自动加载
- WBS-2.7：前端 — 迭代历史面板

### WBS-3：README 中英双版（P0）
- WBS-3.1：重写 README.md 为中文版
- WBS-3.2：新建 README_EN.md 英文版

### WBS-4：竞对洞察 AI 洞察（P1）
- WBS-4.1：后端 — 新增 competitor_ai_service + API 路由
- WBS-4.2：前端 — 竞对洞察页面加 AI 洞察按钮 + 结果展示

### WBS-5：视频看板 AI 建议（P1）
- WBS-5.1：后端 — 新增 video_board_ai_service + API 路由
- WBS-5.2：前端 — 视频看板页面加 AI 建议区域
