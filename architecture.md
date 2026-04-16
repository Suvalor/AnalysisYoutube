# 架构设计文档

## 技术栈选型（含理由）

| 组件 | 选型 | 理由 |
|------|------|------|
| 速率限制 | slowapi | FastAPI 生态最成熟的限流库，基于 limits + fixed-window，轻量无重依赖 |
| LLM 记忆存储 | MySQL 新表 `llm_conversation` | 复用现有 SQLAlchemy + asyncmy，无需引入 Redis；对话历史量可控 |
| 对话截断 | 后端 Python 实现 | 按 token 估算（字符数/4）截断，无需引入 tiktoken |

## 模块结构图

```
backend/app/
├── api/v1/
│   ├── ai.py              ← 修改：注入对话历史
│   ├── scripts.py          ← 修改：注入对话历史
│   ├── youtube.py          ← 修改：注入对话历史、修复信息泄露
│   ├── radar.py            ← 修改：注入对话历史
│   ├── auth.py             ← 修改：增加速率限制
│   └── oss.py              ← 修改：修复信息泄露
├── models/
│   └── llm_conversation.py ← 新增：对话历史模型
├── schemas/
│   └── llm_conversation.py ← 新增：对话历史 schema
├── crud/
│   └── llm_conversation.py ← 新增：对话历史 CRUD
├── services/
│   ├── llm_conversation_service.py ← 新增：对话加载/截断/保存
│   ├── youtube_service.py  ← 修改：httpx trust_env=False
│   └── youtube_ai_service.py ← 修改：修复信息泄露
└── core/
    ├── config.py           ← 修改：移除弱默认值
    └── rate_limit.py       ← 新增：slowapi 限流实例

frontend/src/
├── pages/youtube/ChannelList.tsx    ← 修改：增加删除确认
├── pages/knowledge/AssetLibrary.tsx ← 修改：增加删除确认
├── pages/sop/ScriptWorkflowSOP.tsx  ← 修改：增加删除确认
├── pages/feishu/FeishuDocList.tsx   ← 修改：增加删除确认
└── pages/radar/BlueOceanRadar.tsx   ← 修改：catch 错误反馈
```

## 数据结构设计

### 新增表：llm_conversation

```sql
CREATE TABLE llm_conversation (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,                    -- 所属用户
    entity_type   VARCHAR(32) NOT NULL,            -- 业务实体类型：channel / script / sop / radar
    entity_id     VARCHAR(64) NOT NULL,            -- 业务实体 ID（字符串以兼容多种 ID 格式）
    role          ENUM('system','user','assistant') NOT NULL,
    content       TEXT NOT NULL,                    -- 消息内容
    turn          INT NOT NULL DEFAULT 0,           -- 对话轮次（0=系统提示，1=首轮 user+assistant）
    model_name    VARCHAR(128) DEFAULT NULL,        -- 使用的模型名（可选）
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_entity (user_id, entity_type, entity_id),
    INDEX idx_entity_turn (entity_type, entity_id, turn)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### API 接口变更

**现有接口增加可选参数**（向后兼容）：

| 接口 | 新增请求参数 | 新增响应字段 |
|------|-------------|-------------|
| `POST /api/v1/scripts/generate` | `conversation_id?: string` | `conversation_id: string` |
| `POST /api/ai/generate-script-stream` | `conversation_id?: string` | SSE 事件增加 `conversation_id` |
| `POST /api/youtube/channels/{id}/ai-analyze` | `conversation_id?: string` | `conversation_id: string` |
| `POST /api/radar/ai-retrospective` | `conversation_id?: string` | `conversation_id: string` |

**conversation_id 规则**：
- 首次调用不传 → 自动生成 `{entity_type}:{entity_id}` 作为 conversation_id
- 后续调用传入 → 加载该 conversation 的历史消息

### 对话历史服务接口

```python
class LLMConversationService:
    async def load_messages(
        session, user_id, entity_type, entity_id,
        max_turns: int = 20, max_chars: int = 8000
    ) -> list[dict[str, str]]
    """加载对话历史，自动截断超长消息"""

    async def save_message(
        session, user_id, entity_type, entity_id,
        role, content, turn, model_name=None
    ) -> LLMConversation
    """保存单条消息"""

    async def save_turn(
        session, user_id, entity_type, entity_id,
        user_content, assistant_content, turn, model_name=None
    ) -> None
    """保存一轮对话（user + assistant）"""

    async def prune_old_turns(
        session, user_id, entity_type, entity_id,
        keep_turns: int = 20
    ) -> int
    """淘汰最早轮次，返回删除行数"""
```

## 文件组织结构

新增文件：
1. `backend/app/models/llm_conversation.py` — SQLAlchemy 模型
2. `backend/app/schemas/llm_conversation.py` — Pydantic schema
3. `backend/app/crud/llm_conversation.py` — CRUD 操作
4. `backend/app/services/llm_conversation_service.py` — 业务逻辑（加载/截断/保存/淘汰）
5. `backend/app/core/rate_limit.py` — slowapi 限流实例
6. `backend/alembic/versions/xxxx_add_llm_conversation_table.py` — 数据库迁移

修改文件（安全修复）：
1. `docker-compose.yml` — 密钥外移至 .env
2. `backend/app/core/config.py` — 移除弱默认值，增加启动校验
3. `backend/app/api/v1/youtube.py` — 信息泄露修复
4. `backend/app/api/v1/ai.py` — 信息泄露修复
5. `backend/app/api/v1/scripts.py` — 信息泄露修复
6. `backend/app/api/v1/oss.py` — 信息泄露修复
7. `backend/app/api/v1/auth.py` — 速率限制
8. `backend/app/services/youtube_service.py` — httpx trust_env
9. `backend/app/services/youtube_ai_service.py` — 信息泄露修复

修改文件（UI 修复）：
1. `frontend/src/pages/youtube/ChannelList.tsx` — 删除确认
2. `frontend/src/pages/knowledge/AssetLibrary.tsx` — 删除确认
3. `frontend/src/pages/sop/ScriptWorkflowSOP.tsx` — 删除确认
4. `frontend/src/pages/feishu/FeishuDocList.tsx` — 删除确认
5. 多个页面 — catch 块错误反馈

## 风险登记册

| 风险 | 影响 | 概率 | 应对 |
|------|------|------|------|
| slowapi 与 FastAPI lifespan 冲突 | 中 | 低 | slowapi 使用 FastAPI state 存储，不依赖 lifespan |
| LLM 记忆增加 token 消耗导致成本上升 | 中 | 中 | 默认 max_chars=8000 截断，可配置 |
| docker-compose 密钥外移影响现有部署 | 高 | 中 | 同步更新 README 和 .env.example，提供迁移说明 |
| 对话历史表数据量增长 | 低 | 中 | 按用户+实体隔离 + 自动淘汰 20 轮上限 |

## WBS 任务分解

### WBS-1：安全漏洞修复（P0）
- WBS-1.1：docker-compose.yml 密钥外移
- WBS-1.2：config.py 弱默认值修复 + 启动校验
- WBS-1.3：后端信息泄露修复（6 处 detail 泄露）
- WBS-1.4：httpx trust_env=False 统一修复
- WBS-1.5：注册接口速率限制

### WBS-2：UI 交互缺陷修复（P0）
- WBS-2.1：删除操作增加确认弹窗（4 处）
- WBS-2.2：catch 块增加错误反馈（17+ 处）

### WBS-3：LLM 对话记忆（P1）
- WBS-3.1：数据模型 + 迁移（llm_conversation 表）
- WBS-3.2：CRUD + Service 层实现
- WBS-3.3：scripts/generate 接入记忆
- WBS-3.4：ai/generate-script-stream 接入记忆
- WBS-3.5：youtube/channels/{id}/ai-analyze 接入记忆
- WBS-3.6：radar/ai-retrospective 接入记忆
- WBS-3.7：sop 大纲拆解接入记忆
