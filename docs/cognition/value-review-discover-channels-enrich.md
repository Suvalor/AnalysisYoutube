# 深度认知报告：智能挖掘爆款小号 — 数据修复与信息增强

**日期**：2026-05-20
**审查模块**：`/api/channels/discover` 频道挖掘列表
**审查人**：Gemini Cognitive Engine v4.0
**来源文档**：`docs/scope-change/20260520-discover-channels-enrich.md`

---

## 一、本质解构 (First Principles)

剥离所有流行词和框架，这个需求的物理形态是什么？

### 1.1 本质三层

| 层 | 物理形态 | 技术本质 |
|----|---------|----------|
| P0 修复 | 前端 `dataIndex` 写错字段名 | 一次字符串替换：`"total_views"` → `"channel_total_views"` |
| P1 翻量 | `max_results` 默认值 25 → 50 | 一次整数修改，在 YouTube API 允许范围内 |
| P2 富信息 | 新增 4 个字段展示 | 从 YouTube API 响应中提取已存在但未透传的数据 |

核心洞察：**这不是在创造新能力，而是在把已经抵达后端的"沉默数据"透传出来。**

- `video_count`：`channels.list` 返回的 `statistics.videoCount`，后端已经在解析 `statistics` 对象，只是没有提取这个字段。
- `avg_views_per_video`：后端已有的 `total_views` / 新提取的 `video_count`，一次除法。
- `trigger_video_title`：`videos.list` 返回的 `snippet.title`，只需将 `part` 从 `"statistics"` 改为 `"snippet,statistics"` 即可获取。
- `channel_created_at`：`channels.list` 返回的 `snippet.publishedAt`，后端已经使用 `snippet` 对象（提取了 `title` 和 `thumbnails`），仅需多取一个字段。

### 1.2 MVP 判断

方案比原生实现复杂吗？**否。** 全部改动都是"从已有 API 响应中多取一个字段"或"修正一个字段名"，零额外复杂度。

是否触发"比原生复杂 10 倍"的拒绝条件？**否。** 这是教科书级的轻量增强。

---

## 二、核心矛盾 (Materialist Dialectics)

### 矛盾 A：信息密度 vs 表格可读性

- **获得**：用户在不离开搜索结果列表的情况下，可以评估频道质量（视频数、均播放量、创建时间、爆款视频标题）。
- **牺牲**：新增 2 列（视频数、均播放量），富化了 1 列（爆款视频播放从单一数值变为数值+标题），表格横向空间压力增大。
- **缓解措施**：需求中将"频道链接"和"爆款视频"两列合并为"链接"列（竖向排列），净增列数为 0（2 新增 - 1 合并 = +1 列，原 7 列变为 8 列）。标准桌面宽度（>1280px）下无横向滚动风险。

### 矛盾 B：数据即时性 vs API 配额消耗

- **获得**：用户每次搜索获得更丰富的信息，减少"点进频道详情才失望"的无效操作。
- **牺牲**：无。YouTube Data API v3 按 request 计费，`part` 参数叠加不额外扣费。需求确认：
  - `videos.list` `part` 从 `"statistics"` 改为 `"snippet,statistics"` — 配额消耗不变
  - `max_results` 25 → 50 — 仍为单次 `search.list` 调用（~100 quota），不增加 request 数
  - 新增字段全部来自已调用的 API 端点，不引入新 API 调用

### 矛盾 C：计算精度 vs 展示清晰度

- `avg_views_per_video` 后端返回 `float`（如 12345.6），前端用 `Math.round()` 取整展示。
- 损失了小数点精度，但符合卡牌展示场景——用户关心的是"均播放量大约 1.2 万"而非"12345.6"。
- 这是合理的 UI 层精度降级，影响面零。

---

## 三、系统影响 (Systems Thinking)

### 3.1 API 契约变更

| 端点 | 变更类型 | 破坏性 | 影响面 |
|------|---------|--------|--------|
| `POST /api/channels/discover` | Response body 新增 4 字段 | 向后兼容（新增字段含默认值） | 仅前端消费 |

无外部消费者，前后端同步更新，无契约断裂风险。

### 3.2 数据库

**零影响。** `discover_channels_by_keyword()` 是纯内存操作，不读写任何数据库表。频道数据来自 YouTube API 实时查询，不落库。需求中提到的"可能需要缓存"未实施，也无必要——该端点使用场景为低频的手动搜索，不是高频轮询。

### 3.3 YouTube API 调用链

现有调用链（无变化）：
```
search.list (1 call, ~100 quota)
  → 提取 channelId 列表
  → videos.list (N batch calls, 1 quota each) + channels.list (M batch calls, 1 quota each)
  → 本地过滤（订阅数阈值）
  → 返回
```

唯一变化是 `videos.list` 的 `part` 参数，不改变调用次数和配额消耗。

### 3.4 前端状态

`ChannelList.tsx` 中的 `discoverColumns` 数组长度从 7 增至 8。`DiscoverFormValues` 无变化（`max_results` 已是类型成员）。`DiscoverChannelItem` 类型新增 4 字段。所有改动都在现有组件的局部范围内，不涉及路由、状态管理、或跨组件通信。

### 3.5 连锁反应检查

- 数据库索引：不涉及。
- 缓存失效：不涉及（无缓存依赖）。
- 其他端点：蓝海雷达 (`/api/radar/blue-ocean`) 使用独立的 `BlueOceanChannelItem` schema，不受影响。
- 配额追踪：`quota_service.py` 追踪的是 request 次数计数，`part` 参数变化不影响计数逻辑。

---

## 四、潜在风险

### 技术风险

| 风险 | 等级 | 说明 | 缓解 |
|------|------|------|------|
| `video_count=0` 导致除零 | LOW | 后端已有 `if video_count > 0 else 0.0` 防护 | 已处理 |
| YouTube API 返回字段缺失 | LOW | `statistics.videoCount`、`snippet.publishedAt` 是标准字段，但理论上可为 null | 已用 `try/except` 包裹，缺失时降级为 0 或 None |
| API 响应体积增大 | LOW | `videos.list` 返回 `snippet` 会增加响应体积（每个视频 ~2-5 KB），50 个视频约增 100-250 KB | 对用户体验影响可忽略，YouTube API 延迟主要在网络上 |

### 业务风险

| 风险 | 等级 | 说明 |
|------|------|------|
| `avg_views_per_video` 误导性 | MEDIUM | 均播放量 = 总播放量 / 总视频数，但频道早期视频可能播放量很低，新频道可能因少数爆款而均播放量虚高。该指标是粗粒度估计，不是精确的"近期内容表现"。但作为快速筛选维度，可接受。 |
| `channel_created_at` 缺失 | LOW | 部分老频道的 `snippet.publishedAt` 可能不准确（YouTube 限制），但这是 API 层面的固有限制，非本需求引入。前端做了空值判断，缺失时不显示。 |

### 用户体验风险

| 风险 | 等级 | 说明 |
|------|------|------|
| 表格信息过载 | LOW | 8 列表格在桌面端完全可用。1366px 宽度下表格总宽度约 865px，无横向滚动。 |
| "已关注"按钮误触 | LOW | 无改动，现有逻辑不变。 |

---

## 五、实施状态发现

代码审查发现：**本 PRD 中的全部改动已经以 working tree 修改的形式存在于代码仓库中**，尚未提交 (unstaged)。

| 文件 | 变更内容 | 状态 |
|------|---------|------|
| `backend/app/schemas/discovery.py` | `DiscoverChannelItem` 新增 4 字段；`max_results` default 25→50 | 已实现 (unstaged) |
| `backend/app/services/youtube_service.py` | 提取 `video_count`、`avg_views_per_video`、`trigger_video_title`、`channel_created_at`；`videos.list` part 改为 `snippet,statistics` | 已实现 (unstaged) |
| `frontend/src/services/authApi.ts` | `DiscoverChannelItem` type 新增 4 字段 | 已实现 (unstaged) |
| `frontend/src/pages/youtube/ChannelList.tsx` | P0 修复 (`total_views` → `channel_total_views`)；新增视频数/均播放量列；爆款视频播放富化；频道列富化（创建时间）；链接列合并；`max_results` 25→50（`setFieldsValue` + form） | 已实现 (unstaged) |

### 剩余微不一致

`ChannelList.tsx` 第 730 行 Form 组件 `initialValues` 中 `max_results` 仍为 `25`：

```tsx
initialValues={{ published_after: 14, max_subscribers: 50000, max_results: 25 }}
```

但由于 `openDiscoverModal()` 在 `resetFields()` 后立即调用 `setFieldsValue({ max_results: 50 })`，用户实际看到的表单值是 50，此 `initialValues` 为死代码，无用户影响。建议在 Phase 3 实现阶段顺手修正以保持代码一致性。

---

## 六、判定

**VERDICT: PASS**

理由：需求本质是"透传已有但沉默的 API 数据"，零新依赖、零架构变更、零配额增量。实现已完成且正确（仅 1 处 cosmetic 死代码建议修正）。技术风险全部 LOW 级别并已有防护代码。

风险提示：`avg_views_per_video` 作为筛选维度是粗粒度估计（MEDIUM 级别局限），建议在 UI 提示或在后续迭代中补充近期 N 期均播放量。本判定不阻止当前需求推进，可作为 vNext 优化项。
