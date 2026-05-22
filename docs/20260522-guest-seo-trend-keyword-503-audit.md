# 游客身份下热门趋势、SEO 评分、关键词研究 503 排查

日期：2026-05-22

## 结论

是同一类情况。

当前日志里的：

```text
POST /api/seo/trending 503
{"detail": "服务暂不可用，请稍后重试"}
```

不是页面权限拦截，也不是游客身份本身不允许访问，而是游客调用依赖 YouTube Data API 的功能时，后端没有拿到系统级 `YOUTUBE_API_KEY`，因此统一返回面向游客的 503 提示。

本地环境检查结果：

```text
backend/.env: YOUTUBE_API_KEY missing or empty
```

## 三个功能的游客访问情况

| 功能 | 前端页面 | 前端 API | 后端接口 | 游客可调用 | 缺少 YouTube API Key 时 |
| --- | --- | --- | --- | --- | --- |
| 热门趋势 | `/trend-discovery` | `trendDiscoveryApi` | `POST /api/seo/trending` | 是 | 503：`服务暂不可用，请稍后重试` |
| SEO 评分 | `/seo-scoring` | `seoScoringApi` | `POST /api/seo/seo-score` | 是 | 503：`服务暂不可用，请稍后重试` |
| 关键词研究 | `/keyword-research` | `keywordResearchApi` | `POST /api/keyword/research` | 是 | 503：`服务暂不可用，请稍后重试` |

## 代码证据

### 前端页面权限

`frontend/src/components/Layout/TabbedShell.tsx` 中三个页面均是 `UserRole.GUEST`：

```ts
{ path: "/keyword-research", ..., minRole: UserRole.GUEST },
{ path: "/seo-scoring", ..., minRole: UserRole.GUEST },
{ path: "/trend-discovery", ..., minRole: UserRole.GUEST },
```

所以游客可以打开页面。

### 前端请求接口

`frontend/src/services/authApi.ts` 中三个调用分别是：

```ts
apiClient.post("/api/keyword/research", payload)
apiClient.post("/api/seo/seo-score", payload)
apiClient.post("/api/seo/trending", payload)
```

### 后端游客路径

三个主接口都已经使用 `OptionalUserDep` + `GuestInfoDep`，说明接口设计上支持游客访问：

- `backend/app/api/v1/keyword.py`：`keyword_research(...)`
- `backend/app/api/v1/seo.py`：`seo_scoring_endpoint(...)`
- `backend/app/api/v1/seo.py`：`trend_discovery_endpoint(...)`

三者都会在游客身份下先做游客配额预留检查，成功后再解析集成配置。

### 503 触发点

游客没有 `org_id`，所以这三个接口都会以 `org_id=None` 调用：

```py
icfg = await resolve_integration_config(db, org_id=None)
```

`backend/app/services/config_manager.py` 中说明：

```py
org_id 为空或 session 为空时，仅使用环境变量 / Settings。
```

因此游客不会读取某个组织的设置中心配置，只会读系统级配置。当前系统级 `YOUTUBE_API_KEY` 缺失时：

- `POST /api/keyword/research` 返回 503
- `POST /api/seo/seo-score` 返回 503
- `POST /api/seo/trending` 返回 503

其中游客看到的错误文案都会是：

```text
服务暂不可用，请稍后重试
```

管理员或已登录用户在相同配置缺失场景下会看到更明确的：

```text
未配置 YouTube API Key，请在设置中心配置
```

## 需要注意的细节

1. `POST /api/seo/trending` 如果命中 1 小时内趋势缓存，会直接返回缓存，不需要 YouTube API Key，也不会扣游客配额。
2. `POST /api/seo/seo-score` 的请求体里 `title` 是必填字段，所以实际使用时一定会触发 YouTube API Key 检查。
3. 三个接口都遵循“先检查配额、实际 API 成功后再扣配额”的策略；缺 Key 返回 503 时不会扣游客配额。
4. 这个现象和游客页面权限不是同一层问题：页面能进，接口因为缺系统级外部 API 配置失败。

## 建议处理

短期运维处理：

- 在后端运行环境中配置有效的系统级 `YOUTUBE_API_KEY`。
- 重启后端服务。
- 用游客身份分别验证：
  - `POST /api/seo/trending`
  - `POST /api/seo/seo-score`
  - `POST /api/keyword/research`

产品/实现层可选优化：

- 在游客接口 503 时前端展示更具体但不暴露内部配置的文案，例如“公共体验服务暂时不可用，请稍后再试或登录后使用自己的配置”。
- 如果希望游客也能使用管理员在设置中心填的 YouTube Key，需要新增“系统公共配置”或“游客默认组织配置”的明确机制；当前代码不会把某个组织配置自动用于游客。

