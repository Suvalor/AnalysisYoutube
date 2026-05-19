# 需求变更文档：用户分层与权限体系重构

> 文档类型：范围变更 PRD
> 日期：2026-05-19
> 状态：待评审
> 附属文件：[UI 设计文档](./20260519-subscription-ui-design.md)

---

## 一、背景与目标

### 1.1 现状问题

| 维度 | 现状 | 问题 |
|------|------|------|
| 用户层级 | 只有「已注册用户」一种，无等级区分 | 无法差异化运营 |
| 调用限额 | `ApiQuotaUsage` 仅按日期汇总 YouTube 配额消耗，不区分用户 | 无法控制单用户消耗 |
| 权限控制 | 所有功能模块对所有已登录用户全开放 | 无法做付费功能墙 |
| 游客访问 | 全部路由需要 JWT，未登录用户无任何体验 | 漏斗第一层缺失 |
| 管理员注册 | 与普通用户共用注册流程，无管理后台入口 | 安全风险 + 无法管理订阅 |
| Feature Flag | 编译时环境变量控制，无运行时动态权限 | 无法按用户等级动态开关 |

### 1.2 目标

1. 建立四层用户体系：游客 → 普通用户 → 付费订阅用户 → 管理员
2. 实现三类 API（YouTube / LLM / CV）的分层限额管控
3. 游客通过 Cookie + IP + 浏览器指纹三重识别，实现无注册体验
4. 管理员通过专属邀请链接注册，保留组织（Org）概念
5. 新增订阅套餐管理功能，管理员可管理付费用户

---

## 二、用户层级定义

```
游客（Guest）← 普通用户（User）← 付费订阅用户（Subscriber）← 管理员（Admin）
```

| 层级 | 标识 | 认证方式 | 说明 |
|------|------|--------|------|
| **游客** | `guest` | 无需登录，Cookie/IP/指纹识别 | 轻度体验，日限最严格 |
| **普通用户** | `user` | 邮箱注册 + 密码登录 | 注册即获得，核心功能受限 |
| **付费订阅用户** | `subscriber` | 普通用户基础上激活订阅套餐 | 管理员分配套餐后升级 |
| **管理员** | `admin` | 专属邀请链接注册 | 无调用限制，可管理订阅 |

---

## 三、API 调用限额矩阵

> 限额按**自然日（UTC+8 00:00 重置）**计算，以**用户账户**为维度（游客以指纹标识为维度）。

### 3.1 限额表（定价套餐权限表）

| 层级 | YouTube API 调用/天 | LLM 调用/天 | 智能视觉 CV/天 |
|------|:-----------------:|:-----------:|:-------------:|
| 游客 | 1 | 1 | 1 |
| 普通用户 | 1 | 3 | 3 |
| 订阅等级 1（基础版） | 10 | 20 | 10 |
| 管理员 | 无限制 | 无限制 | 无限制 |

> **扩展说明**：订阅等级 2、3 预留，套餐具体配额由管理员在后台配置，不硬编码。

### 3.2 计数范围定义

| 服务类型 | 计数触发场景 | 后端入口 |
|---------|------------|---------|
| **YouTube API** | 调用 `/radar/scan`、`/channels/add-by-channel-id`、`/youtube/channels/batch-update`、`/radar/category-opportunity`、`/radar/cross-region-compare`、`/radar/navigation-guide` 中任一 YouTube Data API search.list 或 channels.list 时 | `quota_service.py` + 新增 `user_rate_limit_service.py` |
| **LLM** | 调用 `llm_openai_factory.chat_completions_content()` 或 `stream_chat_completions_deltas()` 时 | `llm_openai_factory.py` 调用前拦截 |
| **智能视觉 CV** | 调用 `watermark_inpaint_client.inpaint_bgr_with_runtime_config_or_none()` 时 | `watermark_inpaint_client.py` 调用前拦截 |

---

## 四、游客（Guest）限制机制

### 4.1 识别策略

游客通过以下三个维度中的**任一项**匹配即视为「同一游客」：

| 维度 | 实现方式 | 有效期 |
|------|--------|-------|
| **Cookie** | 服务端写入 `_ytc_gid`（UUID v4），HttpOnly + SameSite=Strict | 30天 |
| **IP 地址** | 取 `X-Forwarded-For` 首个合法 IP（反代场景）或 `request.client.host` | 当日有效 |
| **浏览器指纹** | 前端 FingerprintJS 生成，随请求头 `X-Client-Fingerprint` 上报 | 当日有效 |

**匹配规则**：三项中「满足任一条件」即命中同一游客，防止用户通过清 Cookie 绕限。

### 4.2 存储方案

使用 Redis（或 MySQL 的 `guest_rate_limits` 表作为降级方案）：

```
Redis key: guest_rate:{dimension}:{date}:{service}
示例:
  guest_rate:ip:2026-05-19:youtube    → 1（已用次数）
  guest_rate:fp:abc123:2026-05-19:llm → 1
  guest_rate:cookie:uuid123:2026-05-19:cv → 0

TTL: 86400s（当日 + 缓冲）
```

### 4.3 游客可访问的前端页面

游客可访问以下页面（无需登录），但调用后端 API 受限额约束：

- 【关键词研究】`/keyword-research`
- 【热门趋势】`/trend-discovery`
- 【SEO 评分】`/seo-scoring`
- 登录页 `/login`、注册页 `/register`

访问其他功能页面时，前端重定向到登录页并提示「该功能需要登录」。

### 4.4 超限行为

游客超出每日限额后，接口返回：

```json
HTTP 429 Too Many Requests
{
  "code": "GUEST_QUOTA_EXCEEDED",
  "message": "今日免费次数已用完，注册账户可获得更多次数",
  "action": "register"
}
```

前端弹出引导注册的 Modal。

---

## 五、管理员专属注册机制

### 5.1 需求说明

- 管理员不通过公开注册页面注册
- 由系统生成一次性「管理员邀请链接」，包含签名 Token
- 邀请链接访问管理员专属注册页，注册后角色直接为 `admin`
- 保留 `org_id` 概念：管理员注册时可指定/新建组织

### 5.2 邀请链接机制

**生成方式**：

```
管理员邀请链接格式：
https://{frontend_base_url}/admin-register?invite={invite_token}

invite_token = JWT，payload:
{
  "sub": "admin_invite",
  "org_id": 1,          // 目标组织 ID（可选，默认1）
  "exp": <24h后>         // 有效期 24 小时，单次使用
}
```

**首次启动生成**：后端 `startup` 事件检测是否存在 `admin` 用户，若不存在则自动生成并打印到日志：

```
[STARTUP] No admin user found. Admin invite link (valid 24h):
https://your-domain.com/admin-register?invite=eyJhbGc...
```

**后续管理员**：现有管理员可在「订阅管理」后台生成新的邀请链接（生成后显示一次，不可查看历史）。

### 5.3 管理员注册页面

路由：`/admin-register?invite={token}`（不在导航栏中，仅邀请链接访问）

表单字段：
- 邮箱（必填）
- 密码（必填，≥12 位）
- 邮箱验证码（必填）
- 组织名称（可选，默认「默认组织」）

校验：Token 有效性 → 邮箱 → 注册 → 标记为 `admin` + `is_used=True`

---

## 六、功能模块权限矩阵

### 6.1 导航模块访问权限

| 模块 | 路径 | 游客 | 普通用户 | 付费订阅 | 管理员 |
|------|------|:----:|:------:|:------:|:----:|
| 关键词研究 | `/keyword-research` | ✅ | ✅ | ✅ | ✅ |
| 热门趋势 | `/trend-discovery` | ✅ | ✅ | ✅ | ✅ |
| SEO 评分 | `/seo-scoring` | ✅ | ✅ | ✅ | ✅ |
| 蓝海雷达 | `/blue-ocean-radar` | ❌ | ✅ | ✅ | ✅ |
| 出海导航 | `/navigation-guide` | ❌ | ✅ | ✅ | ✅ |
| 竞对洞察 | `/competitor-analysis` | ❌ | ✅ | ✅ | ✅ |
| 频道增长 | `/channel-growth` | ❌ | ✅ | ✅ | ✅ |
| 频道管理 | `/youtube/channels` | ❌ | ✅ | ✅ | ✅ |
| 全局视频 | `/youtube/videos` | ❌ | ✅ | ✅ | ✅ |
| 视频看板 | `/video-board` | ❌ | ✅ | ✅ | ✅ |
| 下载管理 | `/downloads` | ❌ | ✅ | ✅ | ✅ |
| 设置中心 | `/config-center` | ❌ | ✅（受限）| ✅（受限）| ✅（全部）|
| 仪表盘 | `/dashboard` | ❌ | ❌ | ❌ | ✅ |
| 订阅管理 | `/subscription-admin` | ❌ | ❌ | ❌ | ✅ |

### 6.2 设置中心子模块权限

| 子模块 | 普通用户 | 付费订阅 | 管理员 |
|--------|:------:|:------:|:----:|
| 智能体管理（Prompts Tab） | ✅ | ✅ | ✅ |
| 风格管理（Styles Tab） | ✅ | ✅ | ✅ |
| 模型管理（Models Tab） | ❌ | ❌ | ✅ |
| 云存储与外部 API（Integration Tab） | ❌ | ❌ | ✅ |

### 6.3 特殊功能模块（原 VITE_FEATURE_* 迁移为角色控制）

以下模块从编译时环境变量控制，改为运行时角色控制（仅管理员可见）：

| 模块 | 原变量 | 新控制方式 |
|------|------|---------|
| 灵感库 | `VITE_FEATURE_INSPIRATION` | `role === 'admin'` |
| AI 创作 | `VITE_FEATURE_AI_CREATOR` | `role === 'admin'` |
| SOP 工作流 | `VITE_FEATURE_SOP` | `role === 'admin'` |
| 素材库 | `VITE_FEATURE_ASSETS` | `role === 'admin'` |
| 知识库 | `VITE_FEATURE_KNOWLEDGE` | `role === 'admin'` |
| 飞书集成 | `VITE_FEATURE_FEISHU` | `role === 'admin'` |

> **迁移说明**：`VITE_FEATURE_*` 环境变量保留作为「全局开关」（false 时即使管理员也不展示），角色控制在此基础上叠加。

---

## 七、订阅管理功能（管理员）

### 7.1 功能概述

管理员在「订阅管理」(`/subscription-admin`) 后台可以：

1. **套餐管理**：创建 / 编辑 / 删除订阅套餐（名称、配额、价格）
2. **用户订阅管理**：为用户手动分配套餐、设置有效期、撤销订阅
3. **用户列表**：查看所有用户，按角色/订阅状态筛选
4. **邀请管理员**：生成管理员邀请链接

### 7.2 订阅套餐数据结构

```
SubscriptionPlan（订阅套餐表）：
  id            INT PK
  name          VARCHAR(64)      套餐名称（如「基础版」「专业版」）
  tier          INT              等级序号（1=基础，2=专业，以此类推）
  youtube_quota INT              YouTube API 每日调用上限
  llm_quota     INT              LLM 每日调用上限
  cv_quota      INT              CV 每日调用上限
  price_monthly DECIMAL(10,2)    月费（仅展示用，不含支付集成）
  is_active     BOOLEAN          是否可用于新增订阅
  created_at    DATETIME
  updated_at    DATETIME
```

```
UserSubscription（用户订阅记录表）：
  id            INT PK
  user_id       INT FK → users.id
  plan_id       INT FK → subscription_plans.id
  started_at    DATETIME         订阅开始时间
  expires_at    DATETIME | NULL  过期时间（NULL=永久）
  is_active     BOOLEAN          是否当前有效
  granted_by    INT FK → users.id   操作管理员 ID
  created_at    DATETIME
  updated_at    DATETIME
```

### 7.3 用户每日限额追踪表

```
UserDailyQuota（用户每日配额使用表）：
  id              INT PK
  user_id         INT FK → users.id
  record_date     DATE             自然日（UTC+8）
  youtube_used    INT DEFAULT 0    YouTube API 已用次数
  llm_used        INT DEFAULT 0    LLM 已用次数
  cv_used         INT DEFAULT 0    CV 已用次数
  UNIQUE KEY (user_id, record_date)
```

### 7.4 用户角色字段扩展

在 `users` 表新增：

```sql
role VARCHAR(20) DEFAULT 'user'  -- 枚举: guest, user, subscriber, admin
```

> `guest` 不存储于数据库，通过 Redis 识别。

---

## 八、后端改造要点

### 8.1 新增/改造的核心模块

| 模块 | 文件位置 | 改造内容 |
|------|--------|--------|
| 用户模型 | `backend/app/models/user.py` | 新增 `role` 字段（枚举） |
| 套餐模型 | `backend/app/models/subscription.py` | 新建 `SubscriptionPlan` + `UserSubscription` |
| 限额模型 | `backend/app/models/user_quota.py` | 新建 `UserDailyQuota` |
| 限额中间件 | `backend/app/services/rate_limit_service.py` | 新建：检查 + 扣减配额，支持游客/用户两路 |
| 依赖注入 | `backend/app/api/deps.py` | 新增 `AdminDep`、`SubscriberDep`、`GuestOrUserDep` |
| Auth 路由 | `backend/app/api/v1/auth.py` | 新增管理员邀请链接生成 + 管理员注册端点 |
| 订阅路由 | `backend/app/api/v1/subscription.py` | 新建：套餐 CRUD + 用户订阅管理 |
| 用户信息返回 | `backend/app/schemas/auth.py` | `UserRead` 新增 `role`、`subscription_tier` 字段 |
| 启动事件 | `backend/app/main.py` | 检测 admin 不存在时打印邀请链接 |

### 8.2 限额拦截注入点

在以下服务调用前注入限额检查（抛出 HTTP 429 则中止）：

```python
# 1. YouTube API 调用前（quota_service.py 修改）
async def check_and_record_youtube_quota(user_id: int | None, guest_id: str | None):
    # 获取用户层级 → 查套餐限额 → 查今日使用量 → 超限则 raise 429

# 2. LLM 调用前（llm_openai_factory.py 修改）
async def check_and_record_llm_quota(user_id: int | None, guest_id: str | None):
    # 同上逻辑

# 3. CV 调用前（watermark_inpaint_client.py 修改）
async def check_and_record_cv_quota(user_id: int | None, guest_id: str | None):
    # 同上逻辑
```

### 8.3 游客 API 路由扩展

以下三个路由需支持未登录访问（改为可选认证）：

```python
# 现在：
@router.post("/research")
async def keyword_research(current_user: CurrentUserDep, ...):

# 改后：
@router.post("/research")
async def keyword_research(
    current_user: OptionalUserDep,  # 新增：可为 None
    guest_info: GuestInfoDep,       # 新增：Cookie/IP/Fingerprint
    ...
):
```

涉及路由：
- `POST /keyword/research`
- `GET /trend/trending`（或 `POST /trend/discover`）
- `POST /seo/scoring`

---

## 九、前端改造要点

### 9.1 认证状态扩展

`authStore.tsx` 从只存 `token` 改为同时存储用户信息：

```typescript
type AuthState = {
  token: string | null;
  user: {
    id: number;
    email: string;
    role: 'guest' | 'user' | 'subscriber' | 'admin';
    subscriptionTier: number | null;  // 1, 2, ... 或 null
  } | null;
};
```

登录成功后，前端调用 `GET /users/me` 拉取用户信息并存储。

### 9.2 导航权限守卫

`TabbedShell.tsx` 的 `navDefs` 新增 `minRole` 字段：

```typescript
type NavDef = {
  path: string;
  labelKey: string;
  icon: typeof Home;
  type: TabType;
  tabId: string;
  featureKey?: FeatureKey;
  minRole?: 'guest' | 'user' | 'subscriber' | 'admin';  // 新增
};

// 过滤逻辑：
navDefs.filter(def => 
  (!def.featureKey || isFeatureEnabled(def.featureKey)) &&
  (!def.minRole || hasRole(currentUser?.role, def.minRole))
)

// 角色层级函数：
function hasRole(userRole: string | undefined, required: string): boolean {
  const HIERARCHY = { guest: 0, user: 1, subscriber: 2, admin: 3 };
  return (HIERARCHY[userRole ?? 'guest'] ?? 0) >= (HIERARCHY[required] ?? 0);
}
```

### 9.3 路由守卫（页面级）

在 App.tsx 的路由配置中为每个页面添加 `RequireRole` 组件：

```tsx
<RequireRole minRole="user" fallback={<LoginPrompt />}>
  <BlueOceanRadar />
</RequireRole>
```

游客访问受限页面时，展示「登录后解锁」提示并引导跳转。

### 9.4 新增页面

| 页面 | 路径 | 说明 |
|------|------|------|
| 管理员注册 | `/admin-register` | 仅邀请链接访问 |
| 订阅管理 | `/subscription-admin` | 管理员专属 |
| 升级订阅引导 | `/pricing` | 普通用户可访问，展示套餐对比 |

---

## 十、数据库迁移计划

### 新增迁移文件列表

```
alembic/versions/
├── 20260519_000001_add_role_to_users.py
│   ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL;
│   CREATE INDEX idx_users_role ON users(role);
│
├── 20260519_000002_create_subscription_plans.py
│   CREATE TABLE subscription_plans (...);
│   INSERT INTO subscription_plans VALUES (1, '基础版', 1, 10, 20, 10, 9.90, 1, ...);
│
├── 20260519_000003_create_user_subscriptions.py
│   CREATE TABLE user_subscriptions (...);
│
├── 20260519_000004_create_user_daily_quota.py
│   CREATE TABLE user_daily_quotas (...);
│
└── 20260519_000005_create_admin_invites.py
    CREATE TABLE admin_invites (
      id INT PK,
      token_hash VARCHAR(64) UNIQUE,  -- SHA256 of invite token
      org_id INT,
      created_by INT,                 -- NULL for system-generated
      is_used BOOLEAN DEFAULT FALSE,
      used_at DATETIME,
      expires_at DATETIME,
      created_at DATETIME
    );
```

### 初始数据种子

```sql
-- 默认套餐（基础版）
INSERT INTO subscription_plans (name, tier, youtube_quota, llm_quota, cv_quota, price_monthly, is_active)
VALUES ('基础版', 1, 10, 20, 10, 9.90, TRUE);

-- 用户角色枚举说明（不创建 ENUM，用 VARCHAR + 应用层约束）
-- 允许值: 'user', 'subscriber', 'admin'
-- guest 不存入数据库
```

---

## 十一、API 接口变更清单

### 新增接口

| 方法 | 路径 | 认证 | 功能 |
|------|------|------|------|
| POST | `/auth/admin-invite` | Admin JWT | 生成管理员邀请链接 |
| POST | `/auth/admin-register` | invite token | 管理员专属注册 |
| GET | `/users/me` | JWT | 返回含 role + subscription 的用户信息 |
| GET | `/subscription/plans` | Admin JWT | 获取套餐列表 |
| POST | `/subscription/plans` | Admin JWT | 创建套餐 |
| PUT | `/subscription/plans/{id}` | Admin JWT | 更新套餐 |
| DELETE | `/subscription/plans/{id}` | Admin JWT | 删除套餐 |
| GET | `/subscription/users` | Admin JWT | 用户订阅列表（分页） |
| POST | `/subscription/users/{user_id}/assign` | Admin JWT | 为用户分配套餐 |
| DELETE | `/subscription/users/{user_id}/revoke` | Admin JWT | 撤销用户订阅 |
| GET | `/quota/me` | JWT / Optional | 获取当前用户今日配额使用情况 |

### 改造接口

| 方法 | 路径 | 改造点 |
|------|------|------|
| POST | `/keyword/research` | 支持游客访问，新增限额检查 |
| GET/POST | `/trend/*` | 支持游客访问，新增限额检查 |
| POST | `/seo/scoring` | 支持游客访问，新增限额检查 |
| POST | `/radar/scan` | 新增 YouTube API 限额检查 |
| POST | `/radar/navigation-guide` | 新增 LLM + YouTube 限额检查 |
| POST | `/ai/*`（LLM 相关） | 新增 LLM 限额检查 |
| POST | `/jimeng/*`（CV 相关） | 新增 CV 限额检查 |

### 登录响应扩展

```json
// 现在
{ "access_token": "eyJ...", "token_type": "bearer" }

// 改后
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "role": "user",
    "subscription_tier": null
  }
}
```

---

## 十二、风险与注意事项

| 风险 | 说明 | 缓解措施 |
|------|------|--------|
| Redis 依赖 | 游客限额依赖 Redis；若 Redis 不可用，游客限额失效 | 提供 MySQL 降级实现；Redis 异常时降级为「放行但记录」 |
| 历史数据迁移 | 现有用户的 `role` 字段默认为 `user` | 迁移脚本设 DEFAULT 'user'，无需人工操作 |
| 管理员无法自注册 | 首次部署时需看日志获取邀请链接 | 完善启动文档；支持 CLI 命令生成邀请链接 |
| Feature Flag 迁移 | 现有 `VITE_FEATURE_*=true` 部署会与新角色控制双重生效 | 文档说明；`VITE_FEATURE_*` 改为默认 `false`，仅保留全局开关语义 |
| 限额绕过 | 用户切换 IP / 清 Cookie 可能绕过游客限额 | 三重指纹「满足任一」即命中，降低绕过概率；注册引导更重要 |

---

## 十三、交付范围

### Phase 1：基础分层（核心）
- [ ] User.role 字段 + 迁移
- [ ] `GET /users/me` 返回 role 信息
- [ ] 前端 authStore 存储 role
- [ ] 前端导航 minRole 过滤
- [ ] 设置中心子模块权限拆分
- [ ] VITE_FEATURE_* 改为 admin 角色控制

### Phase 2：限额管控
- [ ] `UserDailyQuota` 表 + 迁移
- [ ] `rate_limit_service.py` 限额检查服务
- [ ] YouTube / LLM / CV 三个注入点
- [ ] 限额相关 429 响应格式统一

### Phase 3：游客体验
- [ ] 游客识别（Cookie + IP + Fingerprint）
- [ ] Redis 游客限额计数器
- [ ] 关键词 / 趋势 / SEO 路由支持 Optional 认证
- [ ] 前端游客态路由守卫 + 引导 Modal

### Phase 4：管理员 + 订阅管理
- [ ] `SubscriptionPlan` + `UserSubscription` + `AdminInvite` 表
- [ ] 管理员邀请链接生成 + 注册路由
- [ ] 订阅管理后台 API
- [ ] 订阅管理前端页面（见 UI 设计文档）
- [ ] 套餐价格展示页 `/pricing`

---

*附属 UI 设计文档见：[20260519-subscription-ui-design.md](./20260519-subscription-ui-design.md)*
