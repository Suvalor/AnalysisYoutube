# 架构设计文档 — 出海导航模块全面重构升级

## 技术栈选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 前端表单 | Ant Design Select/Input/Steps | 项目标准 UI，Steps 增加引导感 |
| 前端卡片 | Ant Design Card/Timeline/Progress/Tag | 匹配度进度条、行动路线图 Timeline |
| LLM 调用 | LLMClientFactory (火山引擎) | 已集成，OpenAI 兼容接口 |
| JSON 约束 | System Prompt + json.loads + 重试3次 | 无需额外 JSON Schema 库 |
| 多轮对话 | llm_conversation_service.py | 复用现有对话记忆，entity_type="nav_guide" |
| 频道分析 | YouTube channels.list API | 已有封装，新增1次调用 |

## 模块结构图

```
用户输入表单 (8字段)
    │
    ▼
┌─────────────────────────────────────┐
│  POST /api/radar/navigation-guide   │
│  ┌───────────────────────────────┐  │
│  │ 1. 配额前置检查               │  │
│  │ 2. 频道信息获取(可选)         │  │
│  │ 3. LLM 深度推荐(核心)        │  │
│  │    ├─ System Prompt           │  │
│  │    ├─ User Prompt (含频道信息) │  │
│  │    ├─ JSON 解析+校验+重试     │  │
│  │    └─ 返回3个推荐+1个避坑     │  │
│  │ 4. YouTube API 数据补充       │  │
│  │ 5. 配额消耗记录               │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
    │
    ▼
前端渲染推荐卡片+避坑卡片+追问区
    │
    ▼ (用户追问)
┌─────────────────────────────────────┐
│  POST /api/radar/navigation-chat    │
│  ┌───────────────────────────────┐  │
│  │ 1. 加载对话历史               │  │
│  │ 2. 构建追问上下文             │  │
│  │ 3. LLM 回答                   │  │
│  │ 4. 保存对话轮次               │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## 数据结构 / API 接口设计

### NavigationGuideRequest 扩展

```python
class NavigationGuideRequest(BaseModel):
    # 原有字段
    languages: list[str]           # 必填
    content_format: list[str]      # 必填
    budget_level: Literal["zero", "low", "medium", "high"]
    core_skills: list[str]         # 必填, max_length=3
    monetization_goal: str | None
    model_library_id: int | None
    llm_model_name: str | None
    agent_id: int | None
    # 新增字段
    existing_channel_url: str | None  # 可选，已有频道URL
    target_regions: list[str]         # 多选，目标地区
    weekly_hours: str | None          # 每周投入时间
```

### LLM 输出 JSON Schema (升级版)

```json
{
  "recommendations": [
    {
      "niche_title": "科技评测 - 英语 → 美国",
      "match_score": 95,
      "market_heat_stars": 4,
      "market_heat_desc": "头部频道增速 +15%/月",
      "competition_stars": 3,
      "competition_desc": "近半年新入局者成功率 23%",
      "content_gap": "长视频饱和，Shorts评测供给不足",
      "cold_start_period": "3-6个月",
      "target_channel_example": "@TechShorts（8万粉，月增2万）",
      "action_advice": "建议从 Shorts 评测切入...",
      "action_roadmap": [
        {"day_range": "1-7", "task": "注册频道+确定内容定位", "expected_result": "频道上线，发布3条Shorts"},
        {"day_range": "8-14", "task": "建立发布节奏", "expected_result": "日更Shorts，积累初始播放"},
        {"day_range": "15-30", "task": "优化标题+封面+发布时间", "expected_result": "单条播放突破1万"}
      ],
      "estimated_monthly_income": "$200-800"
    }
  ],
  "avoid_niche": {
    "niche_title": "美食Vlog - 英语 → 美国",
    "reason": "极度饱和，头部集中度CR4=72%"
  }
}
```

### NavigationGuideResponse 扩展

```python
class RoadmapStep(BaseModel):
    day_range: str
    task: str
    expected_result: str

class NicheRecommendation(BaseModel):
    niche_title: str
    match_score: int          # 1-100
    market_heat_stars: int    # 1-5
    market_heat_desc: str
    competition_stars: int    # 1-5
    competition_desc: str
    content_gap: str
    cold_start_period: str
    target_channel_example: str
    action_advice: str
    action_roadmap: list[RoadmapStep] = []        # 新增
    estimated_monthly_income: str | None = None    # 新增

class AvoidNiche(BaseModel):
    niche_title: str
    reason: str

class NavigationGuideResponse(BaseModel):
    recommendations: list[NicheRecommendation]
    avoid_niche: AvoidNiche | None = None
    ai_summary: str | None = None
    quota_usage: NavigationQuotaUsage | None = None
    quota_check: QuotaCheckInfo | None = None
    conversation_id: str | None = None  # 新增，用于多轮对话
    channel_info: dict | None = None    # 新增，频道分析结果摘要
```

### 新增：多轮对话 API

```python
class NavigationChatRequest(BaseModel):
    conversation_id: str       # 对话ID
    user_message: str          # 用户追问内容
    model_library_id: int | None = None
    llm_model_name: str | None = None
    agent_id: int | None = None

class NavigationChatResponse(BaseModel):
    assistant_message: str
    conversation_id: str
```

## 文件组织结构

```
backend/app/
├── schemas/radar.py                    # 修改：扩展 Request/Response schema
├── services/radar_navigation_service.py # 修改：升级 LLM Prompt + 新增频道分析 + 多轮对话
├── api/v1/radar.py                     # 修改：新增 navigation-chat 路由
frontend/src/
├── services/authApi.ts                 # 修改：扩展类型定义 + 新增 chat API
├── pages/radar/NavigationGuide.tsx     # 修改：表单+报告UI+追问区全面重构
```

## 风险登记册

| 风险 | 概率 | 影响 | 应对方案 |
|------|------|------|----------|
| LLM JSON 格式不稳定 | 高 | 中 | 重试3次 + 正则兜底提取 |
| 多轮对话上下文过长 | 中 | 中 | 复用 auto-truncation (8000字符) |
| 新增频道URL解析失败 | 低 | 低 | 可选字段，失败不影响主流程 |
| YouTube API 配额不足 | 中 | 高 | 前置检查 + 友好提示 |

## WBS 任务分解

- **WBS-1**：后端 schema 扩展（新增字段 + RoadmapStep + NavigationChatRequest/Response）
- **WBS-2**：后端 LLM Prompt 升级（3个推荐 + action_roadmap + estimated_monthly_income + 频道信息上下文）
- **WBS-3**：后端频道信息获取函数（解析URL → channels.list → 摘要）
- **WBS-4**：后端多轮对话函数 + 路由
- **WBS-5**：前端 authApi.ts 类型扩展 + chat API
- **WBS-6**：前端 NavigationGuide.tsx 表单增强（3个新字段）
- **WBS-7**：前端 NavigationGuide.tsx UI 重构（推荐卡片 + 避坑卡片 + 追问区）
- **WBS-8**：测试用例
