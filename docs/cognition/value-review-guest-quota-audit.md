# 深度认知报告：游客配额 + 数据隔离审计修复

**日期**：2026-05-20
**来源文档**：`docs/20260520-guest-quota-and-isolation-audit.md`
**审查阶段**：Phase 1.5 价值审查（硬门禁）
**审查结论**：PASS（附 3 项设计建议）

---

## 一、本质解构 (First Principles)

剥离所有框架和术语，6 个缺陷的物理形态如下：

| 缺陷 | 物理形态 | 严重程度 |
|------|----------|----------|
| 1. Cookie 绕过配额 | **身份标识符是客户端自陈的** —— 标识符（UUID Cookie）完全由调用方控制，可随时丢弃重取。等同于门禁刷卡但访客可以自己印卡。| P0 — 安全绕过 |
| 2. 配额先扣后失败 | **资源借方的记账时间早于服务可用的确认时间** —— 先扣钱、后看店门是否开着。| P0 — 资源错误消耗 |
| 3. 状态码 400→503 | **HTTP 协议语义颠倒** —— 400 = "你的请求有问题"，503 = "服务端暂不可用"。当前把服务端配置缺失说成客户端错误，阻断了客户端的正确重试/降级路径。| P1 — 协议违规 |
| 4. keyword-history 缺失 | **API 契约空洞** —— 前端调用的端点在后端从未注册，相当于对外挂了一块"此处有门"的牌子，但墙后是实心。| P1 — 功能缺失 |
| 5. feishu_docs 越权删除 | **鉴权粒度不足** —— 只有"属于这个公司"的校验，没有"是你创建的"校验。类比：公司里任何同事可以删除你的工位。| P2 — 越权风险 |
| 6. jimeng 横向回退 | **便利性回退创造了横向通道** —— fallback 本意是"用户忘了配置时帮他找一个"，但回退到 org 级而非 user 级，就变成了"用户 A 可以消费用户 B 的 API Key"。| P2 — 凭证泄露 |

**本质判断**：6 个缺陷中有 2 个是**安全漏洞**（缺陷 1、缺陷 6），2 个是**资源完整性 bug**（缺陷 2、缺陷 5），1 个是**协议/UX 错误**（缺陷 3），1 个是**功能缺口**（缺陷 4）。无一个是"可有可无的优化"——每一个都对应可验证的危害。

---

## 二、代码级验证结果

已逐文件读取并交叉验证审计报告中的每一项指控。验证结果：

| 文件 | 审计指控 | 代码证据 | 判定 |
|------|----------|----------|------|
| `guest_service.py:52-69` | Cookie 绕过 | 无 Cookie 分支（L65-69）直接 `generate_guest_id()` 建新 UUID，无 IP 查找 | **确认** |
| `guest_session_crud.py` | 缺 IP 查询函数 | 全文仅有 `get_guest_session(guest_id=)`，无 `by_ip` 变体 | **确认** |
| `seo.py:318-365` | 配额先于配置校验 | L318-337 执行 check_quota + increment_usage + commit，L360-364 才检查 `icfg.youtube_api_key` 并可能抛 400 | **确认** |
| `seo.py:362` | 状态码 400 | `HTTP_400_BAD_REQUEST` | **确认** |
| `keyword.py:44-63` | 配额先于服务调用 | L44-63 执行 check_quota + increment_usage + commit，L67 才 resolve_integration_config，L69 才调用 research_keyword | **确认** |
| `keyword.py` 全文 | 缺 /keyword-history | `grep -rn keyword.history` 零结果 | **确认** |
| `keyword_cache.py:1-22` | 无 user_id | 模型仅有 id/cache_date/keyword/region/language/data/updated_at | **确认** |
| `feishu_docs.py:65-75` | 删除仅按 org_id | `delete_feishu_doc(db, org_id=..., doc_id=...)` | **确认** |
| `feishu_doc.py:1-71` | CRUD 无 user_id | 全文无 `user_id` 参数 | **确认** |
| `feishu_doc.py:11-23` | 模型无 user_id | 仅有 id/org_id/title/url/created_at/archive_* | **确认** |
| `jimeng.py:39-49` | org 级回退 | `select(ModelLibrary).where(ModelLibrary.org_id == org_id, ModelLibrary.library_kind == "jimeng")` | **确认** |

**验证结论**：审计报告对代码现状的描述 100% 准确，无一处误判。

---

## 三、核心矛盾 (Materialist Dialectics)

每个修复方案中隐藏的取舍与矛盾：

### 缺陷 1：IP 关联 vs 匿名性

| 维度 | 修复前 | 修复后（IP 关联） |
|------|--------|------------------|
| 防护效果 | 零（Cookie 可清） | 中等（同 IP 受限） |
| 隐私代价 | 高（无 IP 追踪） | 中（记录 IP + session） |
| 绕过难度 | 极低（curl 即绕） | 需换 IP（代理/VPN） |
| NAT/企业网场景 | 独立配额（多设备） | 共享配额（同出口 IP） |

**辩证结论**：这里牺牲的是"绝对匿名性"，换取的是"有效的频率限制"。在 NAT/企业网边界场景（多用户共享出口 IP），一个用户用完配额会导致其他人也被 429。这是可接受的边界条件——因为真正需要高频调用的用户应该登录，游客配额本身就是"试吃"而非"正餐"。

### 缺陷 4：keyword-history 设计方案之争（核心决策）

审计报告提出在 `KeywordCache` 上加 `user_id` 列，但这与第 3.6 节的设计意图直接矛盾——`keyword_cache` 被明确定义为"全局共享"以节省 YouTube 配额。这里存在一个**隐性冲突**：审计报告自己既说 keyword_cache 全局共享"符合预期"（3.6 节），又要求按 user_id 过滤历史（3.2 节）。

**两种路径的取舍**：

| 方案 | 优点 | 缺点 |
|------|------|------|
| A：KeywordCache 加 user_id 列 | 改动最小（一个 migration + 一条路由） | 破坏现有缓存共享语义；已有 NULL user_id 的行需回填或丢弃；未来缓存命中逻辑需考虑 user_id |
| B：新建 keyword_history 表 | 不碰 KeywordCache；语义清晰；可选择性记录 | 多一张表 + migration；前端需对接新端点 |
| C：不登录也能看、返回全局缓存 | 零后端改动（仅加路由读取全局 cache） | 无用户隔离；所有用户看同一份历史；与前端预期"我的历史"不符 |

**推荐**：方案 B（独立 keyword_history 表）。理由：(1) 缓存和历史的生命周期不同——缓存可 TTL 过期，历史需长久保留；(2) 不动现有缓存逻辑，降低回归风险；(3) 与 seo 的 `trend_history` 模式一致（seo 已有 `SeoScoreRecord` 独立表）。

### 缺陷 6：便利性 vs 安全性

删除 jimeng 的 org 级回退，意味着**未配置 jimeng 模型库的用户会直接看到 400 错误**，而不是"之前悄悄能用现在突然不能用了"。这会产生一个**可感知的 UX 倒退**：原来"碰巧能工作"的用户会认为新版本引入了 bug。

**缓解措施**：错误消息必须明确引导（"请先在设置中心的模型管理中配置即梦 AI"），并与前端联动——若前端检测到 400 + 特定错误码，可弹出配置引导 UI，把负面体验转化为 onboarding 机会。

---

## 四、系统影响 (Systems Thinking)

修复之间的连锁反应与二阶效应：

### 影响链 A：缺陷 1（IP 关联）的涟漪

```
guest_service.identify_guest() 行为变更
  └→ guest_session_crud.py 新增 get_guest_session_by_ip()
       └→ GuestSession 表：需确认 ip_address 列是否有索引（查询性能）
       └→ 竞态风险：同一 IP 两个并发请求同时进入"无 Cookie + 无 IP session"分支
            → 各自 create_guest_session() → 同一 IP 产生 2 条记录
            → quota 被分散到两条记录中，实际可用配额翻倍
            → 缓解：在 GuestSession 上加 partial unique index (ip_address, date_trunc('day', created_at))
                  OR 在 identify_guest 中使用 SELECT ... FOR UPDATE 加锁
       └→ daily_quotas JSON 日期解析：quotas.get("date") vs None vs corrupt JSON
            → 当前代码 guest_session_crud.py:88 已处理 None 情况
            → 但 JSON blob 可能在写入时部分失败导致格式错误
            → 建议：get_guest_session_by_ip() 加 try/except JSONDecodeError
```

### 影响链 B：缺陷 2+3（配额重排序）与缺陷 1 的交叠

```
quota check 移到 API key 校验之后
  → 对游客请求：identify_guest()（新 IP 逻辑）→ resolve_integration_config()→ check_quota()（新位置）
  → 但 resolve_integration_config 本身也可能消耗 DB 连接 + 时间
  → 如果 org 有很多未配置 YouTube API Key 的集成配置，每次游客请求都会走完整流程但不消耗配额
  → 这不是本次修复引入的，是现有行为，但重排序后更明显
```

### 影响链 C：缺陷 5（feishu_docs）的 model breaking change

```
FeishuDoc 加 user_id 列 + NOT NULL
  → 现有 feishu_docs 行的 user_id 为 NULL/0 → migration 需回填
  → 谁创建了历史文档？无法追溯 → 回填策略：(a) 设为 org creator 的 user_id (b) 设为 NULL 且仅在删除时校验
  → 推荐：(b) 设 allow_null=True，仅对删除/归档操作校验 user_id == current_user.id
  → 但这意味着历史文档"谁都能删" —— 不理想但已是现有行为的上限
  → 折中：migration 设 default=0，新文档写真实的 user_id，删除时校验 user_id > 0 AND user_id == current_user.id
```

### 影响链 D：缺陷 4（keyword-history）的前端耦合

```
前端 KeywordResearch.tsx 调用 keywordHistoryApi(10)
  → 目前静默捕获 404 → 历史区块永久空
  → 修好后：路由返回 200 + items → 前端终于显示数据
  → 需要确认前端 key 匹配（id 字段是否存在）
  → 需要确认 schema 字段名（keyword/region/language/cache_date）与前端预期一致
```

---

## 五、潜在风险与缓解建议

| 风险 | 等级 | 来源 | 缓解 |
|------|------|------|------|
| IP-based session 竞态创建重复记录 | **MEDIUM** | 缺陷 1 | 加 DB 唯一约束或 SELECT FOR UPDATE；建议在 guest_session 表上加 `(ip_address, DATE(created_at))` 的部分唯一索引 |
| guest_session JSON 字段损坏导致 DateParse | **LOW** | 缺陷 1 | `get_guest_session_by_ip` 中对 `daily_quotas` 的 `date` 字段做 try/except |
| keyword-history 方案与 cache 语义冲突 | **MEDIUM** | 缺陷 4 | 采用独立 keyword_history 表（见第三节方案 B），不动 keyword_cache |
| feishu_docs migration 回填策略不当 | **MEDIUM** | 缺陷 5 | 新 user_id 列设 nullable，仅对新写入数据强制非空；历史行在删除时跳过 user 校验或记录 audit log |
| jimeng fallback 删除后的 UX 倒退 | **LOW** | 缺陷 6 | 错误消息明确引导 + 建议前端联动弹出配置 UI |
| keyword.py 与 seo.py 的配额重排后事务一致性 | **LOW** | 缺陷 2 | `check_quota + increment_usage + db.commit()` 需要在一次短事务内完成；确认没有长轮询穿插在 check 和 increment 之间 |
| 全局回退模式未被全面审计 | **LOW** | 缺陷 6 | 建议交叉审计其他 model library consumer（LLM 相关路由），确认是否存在同类 org 级回退逻辑 |

---

## 六、工作量审视

审计报告的估计（总计约 3.5 天）基本合理，但需要修正：

| 缺陷 | 审计估计 | 修正估计 | 修正理由 |
|------|----------|----------|----------|
| 缺陷 1（IP 关联）| 0.5 天 | 0.5-1 天 | 正确。但需加竞态防护（+2h）和索引（+1h），取上限 1 天 |
| 缺陷 2（配额重排 seo+keyword）| 0.5 天 | 0.5 天 | 正确 |
| 缺陷 3（状态码）| "1 行改动" | 确认 0.25 天 | 状态码 + 消息双路径（admin vs guest）需要约 30 行 |
| 缺陷 4（keyword-history）| "需评估" | 1-1.5 天 | 独立表方案：migration + 路由 + schema + 前端对接。为最大不确定性项 |
| 缺陷 5（feishu_docs）| 1 天 | 0.5-1 天 | migration + model + CRUD + 回填。无法回填到正确 user 时需权衡 |
| 缺陷 6（jimeng）| 0.5 天 | 0.25 天 | 删 9 行 + 加 5 行错误消息 |
| **合计** | **~3.5 天** | **2.75-4.25 天** | 取中值约 3.5 天，审计估计持平 |

---

## 七、总体结论

这 6 个缺陷构成了一个典型的"早期项目安全债务"集合：核心功能能跑，边界条件未覆盖。修复它们不会引入架构复杂度（所有改动都是局部的、边界清晰的），但会显著提升系统的完整性——特别是游客配额从"形同虚设"到"基本有效"这一跃迁。

**Pass 的理由**：
1. 每个缺陷都有**可验证的危害路径**——不是理论风险，是触发条件清晰的实证 bug
2. 修复方案**最小化**——没有引入新抽象、新中间件、新基础设施
3. 修复成本与危害级别**匹配**——P0 项简单直接，P2 项边界清晰
4. 无过度设计——没有"顺便重构"、没有"统一改造"、没有"引入 CAPTCHA/RateLimit 中间件"

**唯一需要设计决策的点**：缺陷 4（keyword-history）的落地方案——需从"加 user_id 到 KeywordCache"改为"独立 keyword_history 表"，以避免与现有缓存共享语义冲突。此决策不影响 Pass 结论，仅影响实现细节。

VERDICT: PASS
