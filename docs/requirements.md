# 项目需求文档（PRD）— 用户分层与权限体系重构（更简方案）

## 项目概述

YouTube Compass 当前所有注册用户权限一致，无法区分游客、免费用户和付费用户，也无法对 API 配额做分层管控。本需求在现有 FastAPI + React 技术栈上，以最小改动建立四层用户体系（游客 → 普通用户 → 付费订阅用户 → 管理员），实现 API 分层限额管控，管理员邀请注册，以及基础订阅管理。

**更简方案核心**：砍掉 Redis/浏览器指纹依赖，用 Cookie + IP + MySQL 降级存储实现游客识别；订阅管理界面延后到 Phase 2；Feature Flag 迁移延后；2 个 migration（非 5 个）；~15 个文件（非 ~30 个）。

## 目标用户与使用场景

| 用户层 | 角色标识 | 典型场景 | 核心诉求 |
|--------|---------|---------|---------|
| 游客 | `guest` | 首次访问，未注册 | 免费体验关键词研究/趋势/SEO，每日有限配额 |
| 普通用户 | `user` | 自行注册 | 基础功能使用，配额高于游客 |
| 付费订阅用户 | `subscriber` | 管理员分配套餐后升级 | 更高 API 配额，解锁高级功能 |
| 管理员 | `admin` | 通过专属邀请链接注册 | 管理订阅套餐、分配配额、邀请其他管理员 |

## 核心功能列表

### P0 — 必须交付

1. **用户分层模型**
   - users 表新增 `role` 字段（枚举：guest/user/subscriber/admin，默认 user）
   - 新增 `subscription_plans` 表（id, name, description, quotas_json, price_monthly, is_active, created_at, updated_at）
   - 新增 `user_subscriptions` 表（id, user_id, plan_id, started_at, expires_at, is_active）
   - 用户注册时默认 role=user；管理员通过邀请链接注册时 role=admin

2. **API 分层限额管控**
   - 三类 API 限额：YouTube Data API / LLM API / CV API
   - 限额配置存储在 subscription_plans.quotas_json（JSON 字段）
   - 默认配额表：
     | 角色 | YouTube API/日 | LLM API/日 | CV API/日 |
     |------|---------------|-----------|----------|
     | guest | 5 | 0 | 0 |
     | user | 20 | 10 | 5 |
     | subscriber | 100 | 50 | 20 |
     | admin | 无限 | 无限 | 无限 |
   - FastAPI 中间件：每次 API 调用前检查用户角色 + 当日已用配额
   - 配额计数存储：MySQL（guest_sessions 表记录游客当日使用量）

3. **游客识别与体验**
   - Cookie 生成唯一 guest_id（UUID，有效期 30 天）
   - IP 地址作为辅助标识（同一 IP 多设备场景）
   - 无 Redis 依赖，游客配额数据存 MySQL guest_sessions 表
   - 游客可访问：关键词研究、趋势分析、SEO 工具（受限配额）
   - 游客不可访问：蓝海雷达深度扫描、AI 脚本、SOP、知识库

4. **管理员邀请注册**
   - 新增 `admin_invitations` 表（id, code, created_by, used_by, used_at, expires_at, is_active）
   - 管理员可生成邀请码（6位随机字符串，有效期 7 天）
   - 通过邀请链接注册的用户自动获得 admin 角色
   - API：POST /api/auth/admin-invite（生成邀请码）、GET /api/auth/admin-invite/verify?code=xxx（验证邀请码）

5. **导航权限守卫**
   - 前端根据用户角色动态显示/隐藏导航项
   - 路由守卫：未授权角色访问受保护页面时重定向到升级提示页
   - 现有 Feature Flag 机制保持不变，角色检查作为额外层叠加

### P1 — 延后到 Phase 2

6. **订阅管理界面**（完整 CRUD 页面）
7. **浏览器指纹识别**（增强游客识别精度）
8. **Redis 缓存层**（提升配额检查性能）
9. **Feature Flag 迁移**（编译时 → 运行时）
10. **订阅到期自动降级**（Celery 定时任务）

### P2 — 未来考虑

11. **支付集成**（仅展示价格页面）
12. **游客数据持久化与迁移**（注册时自动迁移游客数据）
13. **配额使用统计仪表盘**

## 功能边界（明确不做的事 + 延后到 Phase 2 的事）

### 本次不做
- 支付集成（Stripe/支付宝等）
- 浏览器指纹识别
- Redis 缓存依赖
- Feature Flag 从编译时迁移到运行时
- 订阅到期自动降级定时任务
- 全站品牌重设计

### 延后到 Phase 2
- 订阅管理界面（完整 CRUD 页面）
- 配额使用统计仪表盘
- 游客数据迁移到注册用户

## 技术约束与交付形式

### 后端
- FastAPI + SQLAlchemy + Alembic 迁移
- 2 个 migration 文件（非 5 个）
- 新增中间件：RateLimitMiddleware（IP + 角色配额检查）
- 新增路由：/api/auth/admin-invite, /api/subscriptions/*
- 新增服务：quota_service（扩展现有）, subscription_service, guest_service
- 新增 CRUD：subscription_crud, admin_invitation_crud

### 前端
- React + Zustand + Ant Design + Tailwind
- 扩展 authStore：新增 role 字段
- 新增权限守卫组件：RoleGuard
- 新增页面：升级提示页、管理员邀请注册页
- 导航栏根据角色动态渲染

### 游客识别
- Cookie（guest_id UUID）+ IP 地址
- MySQL guest_sessions 表存储游客配额使用情况
- 无 Redis 依赖

### 数据库
- MySQL 8.0
- 新增表：subscription_plans, user_subscriptions, admin_invitations, guest_sessions
- 修改表：users（新增 role 字段）

## 验收标准（可量化的 AC 列表）

### AC-1：用户分层
- [ ] users 表包含 role 字段，枚举值为 guest/user/subscriber/admin
- [ ] 新注册用户默认 role=user
- [ ] 管理员邀请链接注册的用户 role=admin
- [ ] 用户角色可通过管理员 API 修改

### AC-2：API 限额管控
- [ ] 游客每日 YouTube API 调用上限 5 次，超出返回 429
- [ ] 普通用户每日 YouTube API 调用上限 20 次，超出返回 429
- [ ] 付费用户每日 YouTube API 调用上限 100 次
- [ ] 管理员无配额限制
- [ ] 配额每日 0 点自动重置
- [ ] LLM/CV API 同理按角色限额

### AC-3：游客体验
- [ ] 未登录用户首次访问自动生成 guest_id Cookie
- [ ] 游客可访问关键词研究、趋势分析、SEO 工具页面
- [ ] 游客不可访问蓝海雷达深度扫描、AI 脚本、SOP、知识库
- [ ] 游客配额用完后显示升级提示

### AC-4：管理员邀请注册
- [ ] 管理员可生成邀请码，有效期 7 天
- [ ] 通过邀请链接注册的用户自动获得 admin 角色
- [ ] 过期邀请码无法使用
- [ ] 已使用的邀请码标记为已使用

### AC-5：导航权限守卫
- [ ] 游客导航栏只显示允许访问的模块
- [ ] 普通用户导航栏显示基础模块
- [ ] 付费用户导航栏显示所有模块
- [ ] 管理员导航栏显示所有模块 + 管理入口
- [ ] 直接访问未授权页面时重定向到升级提示页

### AC-6：订阅管理 API
- [ ] 管理员可创建/编辑/停用订阅套餐
- [ ] 管理员可为用户分配订阅套餐
- [ ] 用户可查看自己的订阅状态和配额使用情况
- [ ] 订阅到期后用户角色自动回退到 user

## Sprint 规划建议

### Sprint 1：数据模型 + 后端 API + 权限中间件（5-7 天）
- 数据库迁移（2 个 migration）
- 用户模型扩展（role 字段）
- 订阅套餐 CRUD
- 管理员邀请注册 API
- 限额管控中间件
- 游客识别服务（Cookie + IP + MySQL）
- 配额检查与计数服务

### Sprint 2：前端页面 + 游客体验 + 集成测试（5-7 天）
- authStore 扩展（role 字段）
- RoleGuard 权限守卫组件
- 导航栏动态渲染
- 升级提示页面
- 管理员邀请注册页面
- 游客体验流程
- 集成测试

## 风险识别

1. **游客识别精度**：Cookie + IP 方案在公共网络/隐私模式下可能误判。缓解：Phase 2 引入浏览器指纹。
2. **配额计数性能**：MySQL 存储游客配额在高并发下可能成为瓶颈。缓解：Phase 2 引入 Redis 缓存层。
3. **现有用户迁移**：已有用户 role 默认为 user，不影响现有功能。管理员需手动升级。
4. **Feature Flag 与角色权限叠加**：两层权限机制可能产生混淆。缓解：角色检查优先于 Feature Flag 检查。
5. **订阅到期处理**：Phase 1 不做自动降级，需管理员手动处理。缓解：Phase 2 引入定时任务。

## value_review_ref: docs/cognition/value-review.md