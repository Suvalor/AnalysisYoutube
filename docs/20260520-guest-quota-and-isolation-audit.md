# 游客配额 + 数据隔离审计报告

**日期**：2026-05-20  
**范围**：全量后端 API（`backend/app/api/v1/` 下 30 个路由文件）  
**触发**：`/api/seo/trending` 游客 400 + 同 IP 多次调用不受限 + 多用户数据隔离缺失  

---

## 一、问题一：游客访问 `/api/seo/trending` 返回 400

### 1.1 根因分析

路由代码（`seo.py` 317-364 行）执行顺序：

```
① 游客配额检查 + increment_usage()  ← 配额已消耗
② await db.commit()
③ get_cached_trend()                ← 命中缓存则直接返回
④ resolve_integration_config()
⑤ if not icfg.youtube_api_key:
       raise HTTPException(400, "未配置 YouTube API Key，请在设置中心配置")
```

**缺陷 A — 状态码语义错误**：400 表示"客户端发送了错误请求"，实际是服务端未配置 API Key，应为 503 Service Unavailable（服务端配置缺失导致不可用）。

**缺陷 B — 配额被错误消耗**：步骤 ① 已扣减游客配额、已 commit，步骤 ⑤ 才发现服务不可用。游客的一次配额被白白消耗，且不会退还。

**缺陷 C — 错误提示对游客无效**：错误消息"请在设置中心配置"仅对管理员有意义，游客看到此消息无法自助处理。

### 1.2 修复方案

| 位置 | 修改 |
|------|------|
| `seo.py` → `/trending` | 将配额 check+increment 移到 ④⑤ 之后（即确认 API Key 存在、缓存未命中后再计费） |
| `seo.py` → `/trending` | 状态码 400 → 503；消息区分管理员版（带"设置中心"引导）和游客版（"服务暂不可用"） |

**修复后执行顺序**：
```
① get_cached_trend()                ← 命中缓存 → 直接返回（不消耗配额）
② resolve_integration_config()
③ if not icfg.youtube_api_key:
       raise HTTPException(503, "...", 对游客说"请稍后重试"对管理员说"请配置")
④ 游客配额检查
⑤ if not allowed: raise 429
⑥ increment_usage() + commit
⑦ 调用 YouTube API
```

---

## 二、问题二：游客配额形同虚设——同 IP 可无限调用

### 2.1 根因分析

**配额系统纯 Cookie 绑定，IP 仅存储不参与限额**。

`guest_service.py identify_guest()` 逻辑：

```python
guest_id = request.cookies.get("guest_id")
if guest_id:
    existing = get_guest_session(session, guest_id)
    if existing:
        return GuestInfo(guest_id=guest_id, ...)  # ← 复用已有 session
    # Cookie 存在但 DB 无记录 → 用旧 guest_id 重建
    await create_guest_session(...)

# 无 Cookie → 生成全新 UUID，创建新 session（配额从 0 起）
new_guest_id = generate_guest_id()
await create_guest_session(session, guest_id=new_guest_id, ip_address=ip_address)
```

`check_quota()` / `increment_usage()` 只接受 `guest_id` 参数，从不查 IP。

**绕过场景**：
- 清除 Cookie → 新 UUID → 配额归零
- 隐身窗口 → 新 UUID → 配额归零
- curl/Postman 直接调用（无 Cookie）→ 每次新 UUID → 配额永远为 0
- 同一个 IP 的 5 台设备 → 各自独立 5 次，合计 25 次

### 2.2 修复方案

在 `identify_guest()` 中：无 Cookie 时先按 IP 查找当日已有 session，若找到则复用，否则才创建新 session。

**`guest_service.py` 改动**：

```python
async def identify_guest(request, session) -> GuestInfo:
    ip_address = _extract_client_ip(request)
    cookie_guest_id = request.cookies.get(_GUEST_COOKIE_NAME)

    # 1. Cookie 有效路径（不变）
    if cookie_guest_id:
        existing = await get_guest_session(session, cookie_guest_id)
        if existing:
            return GuestInfo(guest_id=cookie_guest_id, ip_address=ip_address, is_new=False)
        await create_guest_session(session, guest_id=cookie_guest_id, ip_address=ip_address)
        await session.commit()
        return GuestInfo(guest_id=cookie_guest_id, ip_address=ip_address, is_new=True)

    # 2. 无 Cookie：先按 IP 查找今日 session（新增）
    if ip_address:
        ip_session = await get_guest_session_by_ip(session, ip_address)
        if ip_session:
            return GuestInfo(guest_id=ip_session.guest_id, ip_address=ip_address, is_new=False)

    # 3. 未找到 → 创建新 session
    new_guest_id = generate_guest_id()
    await create_guest_session(session, guest_id=new_guest_id, ip_address=ip_address)
    await session.commit()
    return GuestInfo(guest_id=new_guest_id, ip_address=ip_address, is_new=True)
```

**`guest_session_crud.py` 新增函数**：

```python
async def get_guest_session_by_ip(
    session: AsyncSession,
    ip_address: str,
) -> GuestSession | None:
    """按 IP 查找今日游客 session（用于无 Cookie 时的配额关联）。"""
    today_str = date.today().isoformat()
    stmt = (
        select(GuestSession)
        .where(GuestSession.ip_address == ip_address)
        .order_by(GuestSession.last_active_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    # 仅复用当日记录
    quotas = row.daily_quotas or {}
    if quotas.get("date") != today_str:
        return None
    return row
```

**注意事项**：
- IP 查找只取 `last_active_at` 最新的一条，避免历史数据干扰
- 今日日期不匹配则视为过期，不复用
- IPv6 / 内网 IP（127.0.0.1）也能正常工作（每个 IP 一个 session）
- 代理/NAT 场景：同出口 IP 的多用户会共享一个游客配额，属于可接受的边界情形

---

## 三、问题三：数据隔离审计结果

### 总体结论

绝大多数业务资源均已通过 `user_id` 或 `org_id` 正确隔离，发现 4 个有效缺陷、2 个设计歧义点。

### 3.1 隔离合格列表（✅）

| 模块 | 隔离维度 | 说明 |
|------|----------|------|
| `prompt_library` | `user_id` | `list_by_user` + `get_by_user` 全覆盖 |
| `style_library` | `user_id` | 同上 |
| `model_library` | `user_id` | 同上 |
| `script_library` | `user_id` | 同上 |
| `inspiration` | `user_id` | list/get/create/delete 全带 `user_id` |
| `downloads` | `user_id` | `DownloadTask.user_id == current_user.id` |
| `video_projects` | `user_id` | 全量 user_id 隔离 |
| `asset_library` / `materials` | `user_id` | 全量 user_id 隔离 |
| `channel_growth` | `user_id` | `UserCompetitorPool.user_id` 过滤 |
| `channels` (监控池) | `user_id` | `UserCompetitorPool.user_id == current_user.id` |
| `youtube` 视频列表 | `user_id` | `query_videos` JOIN `UserCompetitorPool.user_id == user_id` |
| `seo` 评分历史 | `user_id` | `SeoScoreRecord.user_id == current_user.id` |
| `seo` 趋势历史 | `user_id` | `list_trend_history(db, user_id=current_user.id)` |
| `radar` 航行指南 | `user_id` | `NavigationGuideRecord.user_id == current_user.id` |
| `integration_settings` | `org_id` | 组织级共享，符合设计 |

---

### 3.2 缺陷一：`/api/keyword/keyword-history` 接口不存在（❌ 功能缺失）

**现象**：前端 `KeywordResearch.tsx` 调用 `keywordHistoryApi(10)` → `GET /api/keyword/keyword-history`，该路由在后端 `keyword.py` 中**从未定义**，返回 404。前端静默捕获异常，历史记录区块永远为空。

**影响**：「研究历史」功能完全失效，用户无法回溯历史关键词。

**修复方案**：

在 `keyword.py` 中新增路由：

```python
from app.api.deps import CurrentUserDep
from app.models.keyword_cache import KeywordCache
from app.schemas.keyword_cache import KeywordHistoryItem, KeywordHistoryListResponse

@router.get(
    "/keyword-history",
    response_model=KeywordHistoryListResponse,
    summary="关键词研究历史（需登录）",
)
async def keyword_history(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    limit: int = Query(10, ge=1, le=50),
) -> KeywordHistoryListResponse:
    """获取当前用户最近的关键词研究记录。"""
    stmt = (
        select(KeywordCache)
        .where(KeywordCache.user_id == current_user.id)
        .order_by(KeywordCache.updated_at.desc())
        .limit(limit)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return KeywordHistoryListResponse(
        items=[
            KeywordHistoryItem(
                id=r.id,
                keyword=r.keyword,
                region=r.region,
                language=r.language,
                cache_date=r.cache_date.strftime("%Y-%m-%d"),
            )
            for r in rows
        ]
    )
```

**前提**：`KeywordCache` 需新增 `user_id` 字段（目前无），或独立建 `keyword_history` 表。

---

### 3.3 缺陷二：`feishu_docs` 按 `org_id` 隔离，同 org 用户可互删（⚠️ 越权风险）

**现象**：
```python
# feishu_docs.py
async def delete_feishu_doc(db, org_id=current_user.org_id, doc_id=doc_id)
```
仅校验 `org_id`，不校验 `user_id`。同一 org 的任意用户可以**删除**其他人创建的飞书文档快照。

**影响**：多用户 org 场景下，用户 A 可删除用户 B 的飞书文档记录（越权删除）。

**修复方案**：在 feishu_docs CRUD 中增加 `user_id` 过滤；删除/归档操作改为 `org_id + user_id` 双重校验；列表查询保持 `org_id` 级（org 内可见）。

---

### 3.4 缺陷三：`jimeng` 模型库回退使用 `org_id`（⚠️ 横向访问风险）

**现象**：
```python
# jimeng.py _resolve_jimeng_config()
ml = await get_by_user(db, ModelLibrary, user_id, jimeng_library_id)
if ml is None:  # ← 回退逻辑
    ml = (select(ModelLibrary)
          .where(ModelLibrary.org_id == org_id,
                 ModelLibrary.library_kind == "jimeng")
          .limit(1))
```

当用户指定的 `model_library_id` 不属于自己时，系统会自动回退到 org 内任意用户的 Jimeng 模型库。用户 A 可以借助回退机制使用用户 B 的 API Key 调用即梦 AI。

**影响**：API Key 横向使用（同 org 内），LLM 费用可能跨用户承担。

**修复方案**：删除 org 级回退逻辑；若用户未配置 Jimeng 模型库，返回 `400 "请先在设置中心添加即梦 AI 模型库"` 而非静默使用他人配置。

---

### 3.5 缺陷四：`keyword_research` 游客调用无缓存命中时仍消耗配额（⚠️ 配额误扣）

**现象**：`keyword.py` 的配额 check+increment 在请求最开始执行，若后续 `resolve_integration_config` 发现无 API Key → 抛出异常，但配额已被扣减且已 commit。与问题一同一模式。

**修复方案**：将配额 increment 移到 `icfg.youtube_api_key` 校验通过且 `research_keyword()` 调用成功之后，仅在实际消耗 YouTube 配额时才扣减。

---

### 3.6 设计歧义（无需修复，需确认）

| 项 | 现状 | 是否符合预期 |
|----|------|-------------|
| `YouTubeChannel` 共享 | 全局共享频道数据；任意用户更新同一频道会影响所有人的展示数据 | 是（降低 API 调用，已知设计） |
| `VideoAnalysis` 按 `org_id` | 同 org 内分析结果共享；多用户 org 场景下无法区分谁分析的 | 待确认（若单用户 org 则无影响） |
| `trend_cache` 按 `region+category` 全局共享 | 1 小时内同一 region+category 共用缓存，不区分 org | 是（节省 YouTube 配额，已知设计） |
| `keyword_cache` 全局共享 | 关键词缓存不区分用户或 org | 是（同上） |

---

## 四、优先级与修复计划

| 优先级 | 缺陷 | 预估工作量 |
|--------|------|------------|
| P0 | 游客配额形同虚设（Cookie 绕过）| 后端 2 处改动，约 0.5 天 |
| P0 | `/trending` 配额先扣后失败（同 `/keyword/research`）| 后端重排顺序，约 0.5 天 |
| P1 | `/trending` 状态码 400→503 + 消息优化 | 后端 1 行改动 |
| P1 | `/keyword/keyword-history` 缺失 | 后端新增路由 + 可能需迁移加 `user_id` 字段 |
| P2 | `feishu_docs` 越权删除 | 后端 CRUD 加 `user_id` 过滤，约 1 天 |
| P2 | `jimeng` 模型库横向回退 | 删除回退逻辑 + 友好报错，约 0.5 天 |

---

## 五、受影响文件汇总

| 文件 | 改动类型 |
|------|----------|
| `backend/app/services/guest_service.py` | 无 Cookie 时按 IP 查找已有 session |
| `backend/app/crud/guest_session_crud.py` | 新增 `get_guest_session_by_ip()` |
| `backend/app/api/v1/seo.py` | 配额扣减顺序调整 + 状态码 400→503 |
| `backend/app/api/v1/keyword.py` | 配额扣减顺序调整；新增 `/keyword-history` 路由 |
| `backend/app/api/v1/feishu_docs.py` | 删除/归档加 `user_id` 校验 |
| `backend/app/api/v1/jimeng.py` | 删除 org 级模型库回退逻辑 |
| `backend/app/models/keyword_cache.py` | 可能新增 `user_id` 字段（需评估） |

---

## AutoDev 执行进度

- [x] Phase 1：需求对齐 / PRD
- [x] Phase 1.5：价值审查（PASS）
- [x] Phase 2：设计与架构
- [x] Phase 3：实现
- [x] Phase 4：代码审查
- [x] Phase 5：业务验收

### 最新状态
- 当前阶段：Phase 7 交付完成
- 最近更新时间：2026-05-20
- 变更文件：
  - 后端修改：app/services/guest_service.py, app/crud/guest_session_crud.py, app/models/guest_session.py, app/api/v1/seo.py, app/api/v1/keyword.py, app/api/v1/feishu_docs.py, app/api/v1/jimeng.py, app/core/config.py, app/db/base.py
  - 后端新增：app/models/keyword_history.py, app/schemas/keyword_history.py, app/crud/keyword_history.py, app/crud/feishu_doc.py (check_doc_ownership)
  - 后端修改：app/models/feishu_doc.py, app/schemas/feishu_doc.py
  - Alembic迁移：20260520_000003 (ip_address索引), 20260520_000004 (keyword_history表), 20260520_000005 (feishu_docs user_id), 20260520_000006 (keyword_history user_id索引)
  - 测试：backend/tests/test_guest_quota_audit.py (33 test cases)
- 验证命令：`cd backend && /workspace/backend/.venv/bin/python -m pytest tests/test_guest_quota_audit.py -v`
- 验证结果：33/33 测试通过，17/17 验收标准通过
- 阻塞项：无
- 假设与取舍：
  - keyword-history 采用独立表而非 KeywordCache 加 user_id（ADR-1：避免破坏缓存共享语义）
  - IP 竞态防护采用 SELECT FOR UPDATE 而非 DB 唯一约束（ADR-2：MySQL 不支持 partial unique index）
  - FeishuDoc user_id 采用 nullable 列 + 渐进式强制策略（ADR-3：历史行 NULL 允许任何人删除，不比修复前更差）
  - X-Forwarded-For 防护：新增 TRUSTED_PROXY_COUNT 配置项，默认 0 不信任代理头
  - 游客搜索不记录 keyword_history（仅已登录用户有历史）
  - jimeng 状态码 500→400（客户端配置缺失而非服务端内部错误）
  - 技术债：keyword_history CRUD 缺少 delete 操作、_extract_client_ip 缺少欺骗风险文档、check_doc_ownership 对历史文档过于宽松
