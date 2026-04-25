# 项目需求文档（PRD）

## 项目概述
重构 LLM 管理体系：将当前以火山引擎为核心的 LLM 配置方式，改为基于协议感知的统一管理。支持 Anthropic（默认）和 OpenAI 两种协议，所有 LLM 调用通过 ModelLibrary 统一调度。去除火山引擎专属配置入口和说明。

## 目标用户与使用场景
- **目标用户**：YouTube Compass 平台管理员/运营人员
- **使用场景**：在 ConfigCenter 配置 LLM 模型，选择协议类型（Anthropic/OpenAI），填写对应的 API Key 和 Base URL，业务代码自动根据协议选择 SDK 调用

## 核心功能列表

### P0（必须完成）
1. **ModelLibrary 新增 protocol 字段**：`anthropic`（默认）/ `openai`，区分 LLM 协议类型
2. **LLMClientFactory 协议感知改造**：根据 protocol 字段选择 Anthropic SDK 或 OpenAI SDK 调用
3. **前端 ConfigCenter 模型管理改造**：新增模型时可选协议类型，默认 Anthropic
4. **删除火山引擎 Tab**：ConfigCenter integration 子 Tab 中移除"火山引擎（LLM / 视觉）"
5. **删除 AiModelSettings 页面**：合并到 ConfigCenter，统一入口
6. **后端去除火山引擎 LLM 专属逻辑**：删除 `resolve_model_alias_for_volcengine`、`looks_like_volcengine_ark_base_url`、Coding Plan 协议检测等

### P1（重要但可延后）
7. **火山 CV 保留但降级**：CV 图像修补功能保留，但不再在 ConfigCenter 有独立配置入口，改为通过模型管理中 `image_inpaint` 类型的条目配置
8. **后端 volcengine 环境变量字段保留**：作为回退，但不再从前端传入

### P2（可选优化）
9. **模型管理 UI 增强**：协议类型切换时，动态调整表单提示（Anthropic 提示填写 Claude API Key，OpenAI 提示填写兼容网关地址）

## 功能边界（明确不做的事）
- 不引入 litellm/one-api 等第三方网关服务
- 不修改火山 CV SDK 的调用逻辑（仅改配置来源）
- 不做 LLM 调用性能优化
- 不做模型负载均衡/故障转移

## 技术约束与交付形式
- **前端**：React + Ant Design + TypeScript，保持现有 UI 风格
- **后端**：FastAPI + SQLAlchemy + Alembic migration
- **新增依赖**：`anthropic` Python SDK（pip install anthropic）
- **数据库变更**：model_libraries 表新增 protocol 列（VARCHAR(16)，默认 'anthropic'）

## 验收标准（AC列表）
1. AC-01：新增模型时可选协议类型（anthropic/openai），默认为 anthropic
2. AC-02：protocol=anthropic 的模型，后端使用 Anthropic SDK 调用 Claude API
3. AC-03：protocol=openai 的模型，后端使用 OpenAI SDK 调用（兼容网关）
4. AC-04：ConfigCenter 无"火山引擎"Tab，无火山专属字段展示
5. AC-05：AiModelSettings 页面已删除，路由已移除
6. AC-06：后端无 `resolve_model_alias_for_volcengine`、`looks_like_volcengine_ark_base_url`、`VOLCENGINE_CODING_*` 等火山专属逻辑
7. AC-07：现有 LLM 调用流程（脚本工坊、雷达、频道分析等）不受影响，正常工作
8. AC-08：Alembic migration 可正确执行，protocol 字段默认值为 'anthropic'

## Sprint规划建议

### Sprint 1（后端改造）
- ModelLibrary 新增 protocol 字段 + Alembic migration
- LLMClientFactory 协议感知改造（Anthropic SDK + OpenAI SDK 双通道）
- 删除火山引擎 LLM 专属逻辑
- 保留火山 CV 配置但改为从模型管理读取

### Sprint 2（前端改造）
- ConfigCenter 模型管理 Tab 改造（protocol 选择）
- 删除火山引擎 Tab
- 删除 AiModelSettings 页面和路由
- 清理前端火山相关引用

## 风险识别
1. **Anthropic SDK 兼容性**：需确认 anthropic SDK 的 async streaming API 与现有业务代码的适配
2. **数据迁移**：现有 model_libraries 数据默认 protocol='anthropic'，需确认现有 OpenAI 兼容网关的模型是否需要手动改为 openai
3. **火山 CV 配置来源变更**：CV 配置从集成配置移到模型管理，需确保不中断现有去水印功能