# 项目需求文档（PRD）

## 项目概述

对 Creator SaaS 平台进行全面质量提升，涵盖三个方向：Python 后端安全漏洞修复、前端 UI 交互缺陷修复、LLM 对话记忆机制实现。

## 目标用户与使用场景

- **用户**：平台运营人员与内容创作者
- **场景**：日常使用 AI 功能（脚本工坊、频道分析、雷达复盘等）时，期望 LLM 能记住上下文；同时系统需无安全漏洞、UI 交互流畅无缺陷

## 核心功能列表

### P0 — Python 安全漏洞修复

| # | 漏洞 | 严重度 | 位置 | 描述 |
|---|------|--------|------|------|
| S1 | docker-compose.yml 硬编码密钥 | **Critical** | `docker-compose.yml:47-57` | YouTube API Key、火山引擎 Key、阿里云 AK/SK/ARN 全部明文写在 compose 文件中，推入 git 后任何有仓库读权限的人可获取 |
| S2 | config.py 默认密码 "password" | **High** | `app/core/config.py:13` | `mysql_password` 默认值为 "password"，若未覆盖则使用弱密码连接数据库 |
| S3 | config.py SECRET_KEY 默认 "change_me" | **High** | `app/core/config.py:19` | JWT 签名密钥默认值极弱，若生产未覆盖则可被伪造 token |
| S4 | AI 分析异常信息泄露 | **Medium** | `app/api/v1/youtube.py:692` | `detail=f"AI 分析失败: {exc}"` 将完整异常堆栈暴露给客户端 |
| S5 | SSE 错误信息泄露 | **Medium** | `app/api/v1/ai.py:69`, `scripts.py:141` | SSE error 事件将 `str(exc)` 直接发送给前端，可能包含内部 URL/密钥片段 |
| S6 | AI 返回原始片段泄露 | **Medium** | `app/services/youtube_ai_service.py:195,629` | `detail` 中包含 `raw_content[:500]`，可能泄露 LLM 内部响应中的敏感信息 |
| S7 | OAuth token 兑换失败信息泄露 | **Medium** | `app/api/v1/youtube.py:865` | `detail=f"OAuth token 兑换失败: {token_resp.text}"` 泄露 OAuth 服务端响应体 |
| S8 | httpx 默认 trust_env | **Medium** | `app/services/youtube_service.py` 多处 | 部分 httpx.AsyncClient 未设置 `trust_env=False`，可能通过 HTTP_PROXY 环境变量被 SSRF |
| S9 | STS 异常信息泄露 | **Low** | `app/api/v1/oss.py:46` | `detail=f"阿里云 STS 调用失败: {exc}"` 暴露 SDK 异常细节 |
| S10 | 注册接口无速率限制 | **Medium** | `app/api/v1/auth.py:22` | `/auth/register` 无 rate limiting，可被暴力枚举或批量注册 |

### P0 — UI 交互缺陷修复

| # | 缺陷 | 严重度 | 位置 | 描述 |
|---|------|--------|------|------|
| U1 | 频道移除无确认弹窗 | **High** | `ChannelList.tsx:424-428` | 点击"移除"按钮直接调用删除 API，无 Popconfirm/Modal.confirm 确认 |
| U2 | 素材删除无确认弹窗 | **High** | `AssetLibrary.tsx:437` | 删除按钮直接调用 `onDelete`，无确认 |
| U3 | SOP 片段删除无确认 | **Medium** | `ScriptWorkflowSOP.tsx:390` | 冗余片段直接删除无确认 |
| U4 | 多处 catch 吞错误 | **Medium** | 17+ 处 `catch {}` | 空 catch 块不向用户反馈错误，如 `BlueOceanRadar.tsx:178`、`AICreator.tsx:42` 等 |
| U5 | Dashboard 配额加载静默失败 | **Low** | `Dashboard.tsx:16` | `.catch(() => undefined)` 静默吞错，用户不知道配额数据加载失败 |
| U6 | 飞书文档删除无确认 | **Medium** | `FeishuDocList.tsx:165` | 直接调用 `deleteFeishuDocApi` 无确认 |

### P1 — LLM 对话记忆机制

| # | 功能点 | 当前状态 | 期望状态 |
|---|--------|----------|----------|
| L1 | AI 脚本工坊（scripts/generate） | 单轮：system + user，无历史 | 按脚本项目隔离，保留最近 N 轮对话 |
| L2 | AI 脚本工坊（ai/generate-script-stream） | 单轮：system + user，无历史 | 按频道/主题隔离，保留最近 N 轮对话 |
| L3 | 频道 AI 深度洞察（youtube/channels/{id}/ai-analyze） | 单轮：每次全量分析 | 按频道隔离，保留分析历史供追问 |
| L4 | 蓝海雷达 AI 复盘（radar/ai-retrospective） | 单轮：每次独立复盘 | 按用户+雷达隔离，保留复盘历史供追问 |
| L5 | SOP 大纲拆解（sop_ai_service） | 单轮：每次独立拆解 | 按 SOP 脚本隔离，保留拆解历史 |

**记忆隔离维度**：按业务实体（channel_id / script_id / sop_id / radar_session）隔离，不同实体间不共享上下文。

## 功能边界（明确不做的事）

- 不做跨功能点的全局 LLM 记忆共享
- 不做 LLM 记忆的 UI 管理界面（查看/删除历史）— 本期仅实现后端存储与自动注入
- 不做 LLM 记忆的 token 用量统计与限制（后续迭代）
- 不重构现有 LLM 调用为 Agent 框架

## 技术约束与交付形式

- 后端：Python / FastAPI / SQLAlchemy / MySQL，新增 `llm_conversation` 表
- 前端：本次不涉及前端改动（记忆对前端透明，仅 API 请求可选传 conversation_id）
- 交付形式：先产出扫描报告（本文档），确认后逐项修复代码

## 验收标准

### 安全漏洞
- AC-S1：docker-compose.yml 中所有密钥替换为 `${ENV_VAR}` 引用，实际值仅存于 .env
- AC-S2：config.py 中敏感字段默认值改为空字符串，启动时校验必填
- AC-S3：所有 `detail=f"...{exc}"` 改为日志记录 + 通用错误消息
- AC-S4：所有 httpx 客户端显式设置 `trust_env=False`
- AC-S5：注册接口增加基础速率限制

### UI 缺陷
- AC-U1：所有删除/移除操作增加 Popconfirm 确认
- AC-U2：所有空 catch 块增加 `message.error()` 用户反馈

### LLM 记忆
- AC-L1：新增 `llm_conversation` 表，存储按实体隔离的对话历史
- AC-L2：各 LLM 调用点自动加载历史消息并注入，返回 conversation_id
- AC-L3：历史消息超过 token 预算时自动截断（保留最近 N 轮）
- AC-L4：每个实体最多保留最近 20 轮对话，超限自动淘汰最早轮次

## 风险识别

1. **LLM 记忆注入可能增加 token 消耗** — 需设置合理截断策略
2. **docker-compose 密钥外移可能影响现有部署** — 需同步更新部署文档
3. **速率限制实现需选方案** — 建议使用 slowapi 或中间件，避免引入重依赖
