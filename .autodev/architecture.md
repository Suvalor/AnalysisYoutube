# 架构设计文档

## 技术栈选型

| 组件 | 选型 | 理由 |
|------|------|------|
| Anthropic SDK | `anthropic` Python 包 | 官方 SDK，支持 async + streaming，与 OpenAI SDK 并行 |
| 数据库变更 | Alembic migration | 项目已有 Alembic，新增 protocol 列 |
| 前端协议选择 | Ant Design Select | 保持现有 UI 风格一致 |

## 模块结构图

```
改造前:
  ModelLibrary → (无 protocol) → LLMClientFactory → OpenAI SDK only
  ConfigCenter → 火山引擎 Tab (volcengine_api_key, endpoint_id, base_url, ...)

改造后:
  ModelLibrary → protocol (anthropic/openai) → LLMClientFactory
    ├── protocol=anthropic → Anthropic SDK (AsyncAnthropic)
    └── protocol=openai   → OpenAI SDK (AsyncOpenAI)
  ConfigCenter → 无火山引擎 Tab
```

## 数据结构 / API 接口设计

### 1. ModelLibrary 表变更

```sql
ALTER TABLE model_libraries ADD COLUMN protocol VARCHAR(16) NOT NULL DEFAULT 'anthropic'
  COMMENT 'LLM 协议: anthropic (默认) / openai';
```

### 2. LLMClientConfig 扩展

```python
@dataclass(frozen=True)
class LLMClientConfig:
    api_key: str
    base_url: str
    model_name: str | None = None
    protocol: str = "anthropic"  # 新增：anthropic / openai
```

### 3. LLMClientFactory 改造

```python
class LLMClientFactory:
    async def chat_completions_content(self, *, cfg: LLMClientConfig, messages, **kwargs) -> str:
        if cfg.protocol == "anthropic":
            return await self._anthropic_chat(cfg, messages, **kwargs)
        else:
            return await self._openai_chat(cfg, messages, **kwargs)

    async def stream_chat_completions_deltas(self, *, cfg: LLMClientConfig, messages, **kwargs) -> AsyncIterator[str]:
        if cfg.protocol == "anthropic":
            async for delta in self._anthropic_stream(cfg, messages, **kwargs):
                yield delta
        else:
            async for delta in self._openai_stream(cfg, messages, **kwargs):
                yield delta
```

### 4. API Schema 变更

- `ModelCreate` / `ModelUpdate` 新增 `protocol` 字段（默认 "anthropic"）
- `ModelRead` 新增 `protocol` 字段
- `IntegrationSettingsRead/Update` 移除 volcengine LLM 相关字段（保留 CV 字段）

### 5. 前端 API 变更

- `libraryApi.ts` 的 `ModelItem` 新增 `protocol` 字段
- `userApi.ts` 的 `IntegrationSettingsRead/UpdatePayload` 移除 volcengine LLM 字段

## 文件组织结构

### Sprint 1 — 后端改造

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/library.py` | 修改 | ModelLibrary 新增 protocol 列 |
| `backend/alembic/versions/xxx_add_protocol_to_model_libraries.py` | 新增 | Migration |
| `backend/app/schemas/library.py` | 修改 | ModelCreate/ModelUpdate/ModelRead 新增 protocol |
| `backend/app/services/llm_openai_factory.py` | 重构 | 双协议支持，删除火山专属逻辑 |
| `backend/app/services/config_manager.py` | 修改 | 删除 resolve_model_alias_for_volcengine、looks_like_volcengine_ark_base_url；ResolvedIntegrationConfig 删除 volcengine LLM 字段 |
| `backend/app/schemas/integration_settings.py` | 修改 | 删除 volcengine LLM 字段 |
| `backend/app/api/v1/integration_settings.py` | 修改 | 适配 schema 变更 |
| `backend/app/services/youtube_ai_service.py` | 修改 | 删除火山引用，改为从 ModelLibrary 读取 protocol |
| `backend/app/services/youtube_channel_enrich.py` | 修改 | 同上 |
| `backend/app/services/sop_ai_service.py` | 修改 | 同上 |
| `backend/app/services/competitor_ai_service.py` | 修改 | 同上 |
| `backend/app/services/radar_navigation_service.py` | 修改 | 同上 |
| `backend/app/services/radar_param_iteration_service.py` | 修改 | 同上 |
| `backend/app/services/video_board_ai_service.py` | 修改 | 同上 |
| `backend/app/services/seo_scoring_service.py` | 修改 | 同上 |
| `backend/requirements.txt` | 修改 | 新增 anthropic 依赖 |

### Sprint 2 — 前端改造

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/pages/settings/ConfigCenter.tsx` | 重构 | 删除火山 Tab，模型管理新增协议选择 |
| `frontend/src/pages/settings/AiModelSettings.tsx` | 删除 | 合并到 ConfigCenter |
| `frontend/src/components/Layout/TabbedShell.tsx` | 修改 | 删除 AiModelSettings 引用 |
| `frontend/src/services/libraryApi.ts` | 修改 | ModelItem 新增 protocol |
| `frontend/src/services/userApi.ts` | 修改 | 删除 volcengine LLM 字段 |

## Sprint规划

### Sprint 1：后端模型+协议层改造
- **范围**：ModelLibrary protocol 字段 + LLMClientFactory 双协议 + 删除火山 LLM 逻辑
- **交付物**：可运行的后端，所有 LLM 调用支持 anthropic/openai 双协议
- **验收标准**：AC-02, AC-03, AC-06, AC-08

### Sprint 2：前端 ConfigCenter 改造
- **范围**：ConfigCenter 模型管理改造 + 删除火山 Tab + 删除 AiModelSettings
- **交付物**：前端 ConfigCenter 支持协议选择，无火山 Tab，无 AiModelSettings
- **验收标准**：AC-01, AC-04, AC-05, AC-07

## 风险登记册

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| Anthropic SDK streaming API 与现有业务不兼容 | 低 | 高 | 先实现非流式，验证后再加流式 |
| 现有 OpenAI 兼容网关模型数据默认变 anthropic | 中 | 中 | migration 默认值 anthropic，但需在 PR 说明已有 openai 模型需手动更新 |
| 火山 CV 配置来源变更导致去水印中断 | 低 | 高 | CV 配置暂保留在 integration_settings，仅前端移除展示 |

## WBS 任务分解

### Sprint 1
1. ModelLibrary 新增 protocol 字段 + Alembic migration
2. LLMClientFactory 重构：双协议支持（Anthropic SDK + OpenAI SDK）
3. 删除火山专属逻辑（resolve_model_alias_for_volcengine, looks_like_volcengine_ark_base_url, Coding Plan 检测）
4. 各 AI service 适配新 LLMClientFactory 接口
5. integration_settings schema 删除 volcengine LLM 字段
6. requirements.txt 新增 anthropic

### Sprint 2
7. ConfigCenter 模型管理 Tab 新增协议选择
8. ConfigCenter 删除火山引擎 Tab
9. 删除 AiModelSettings 页面和路由
10. 前端 API 类型更新（libraryApi, userApi）
11. 清理前端火山相关引用
