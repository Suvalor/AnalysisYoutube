# 需求文档：智能挖掘爆款小号 — 数据修复与信息增强

**日期**：2026-05-20
**状态**：已完成
**模块**：智能挖掘爆款小号（`/api/channels/discover`）  
**受影响文件**：
- `backend/app/schemas/discovery.py`
- `backend/app/services/youtube_service.py`
- `frontend/src/services/authApi.ts`
- `frontend/src/pages/youtube/ChannelList.tsx`

---

## 一、问题描述

| # | 现象 | 根因 |
|---|------|------|
| P0 | 总播放量全部显示为 0 | `discoverColumns` 的 `dataIndex` 写成了 `"total_views"`，而后端字段名是 `channel_total_views`，导致 `render(v)` 始终收到 `undefined`，`formatNumber(undefined)` 输出 `"0"` |
| P1 | 返回频道数量少 | `max_results` 默认值仅 25，YouTube API 最高支持 50 |
| P2 | 信息不足以做选频判决 | 结果缺少视频数、均播放量、爆款视频标题、频道创建时间等关键判断维度 |

---

## 二、需求目标

1. **修复 P0 数据异常**：总播放量正确显示真实数值。
2. **提升数据覆盖量**：单次挖掘最多返回 50 条候选频道（从 25 条翻倍）。
3. **丰富信息维度**：新增 4 个字段，帮助用户在不点击外链的情况下判断频道质量。

---

## 三、字段增量（新增）

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `video_count` | `int` | `channels.list` → `statistics.videoCount` | 频道已发布视频总数 |
| `avg_views_per_video` | `float` | 后端计算（总播放量 ÷ 视频数） | 均播放量，衡量持续输出能力 |
| `trigger_video_title` | `str \| None` | `videos.list` → `snippet.title` | 触发挖掘的爆款视频标题 |
| `channel_created_at` | `str \| None` | `channels.list` → `snippet.publishedAt` | 频道创建时间（ISO 8601） |

---

## 四、变更详情

### 4.1 后端 schema（`backend/app/schemas/discovery.py`）

`DiscoverChannelItem` 新增 4 个字段：

```python
class DiscoverChannelItem(BaseModel):
    yt_channel_id: str
    title: str
    thumbnail_url: str | None = None
    subscriber_count: int
    channel_total_views: int
    video_count: int = 0              # 新增
    trigger_video_views: int
    trigger_video_title: str | None = None   # 新增
    avg_views_per_video: float = 0.0  # 新增
    channel_created_at: str | None = None    # 新增
    channel_url: str
    viral_video_url: str
```

`ChannelDiscoverRequest.max_results` 默认值由 `25` 调整为 `50`。

### 4.2 后端 service（`backend/app/services/youtube_service.py`）

`discover_channels_by_keyword()` 内部改动：

1. `videos.list` 请求的 `part` 从 `"statistics"` 改为 `"snippet,statistics"`，以获取视频标题。
2. 新增 `trigger_video_title_map: dict[str, str]`，从 `snippet.title` 提取标题。
3. 从 `statistics.videoCount` 提取 `video_count`。
4. 后端计算 `avg_views_per_video = round(total_views / video_count, 1)`（`video_count` 为 0 时返回 `0.0`）。
5. 从 `snippet.publishedAt` 提取 `channel_created_at`。
6. 上述字段一并写入 `items.append({...})` 的字典。

### 4.3 前端类型（`frontend/src/services/authApi.ts`）

`DiscoverChannelItem` 同步新增 4 个字段：

```typescript
export type DiscoverChannelItem = {
  yt_channel_id: string;
  title: string;
  thumbnail_url: string | null;
  subscriber_count: number;
  channel_total_views: number;
  video_count: number;
  trigger_video_views: number;
  trigger_video_title: string | null;
  avg_views_per_video: number;
  channel_created_at: string | null;
  channel_url: string;
  viral_video_url: string;
};
```

### 4.4 前端表格（`frontend/src/pages/youtube/ChannelList.tsx`）

`discoverColumns` 改动：

| 改动 | 详情 |
|------|------|
| 修复 dataIndex | `"total_views"` → `"channel_total_views"` |
| 频道列增强 | 在频道名下方显示「X 年前创建」（`dayjs(channel_created_at).fromNow()`） |
| 新增「视频数」列 | `dataIndex: "video_count"`，格式化显示 |
| 新增「均播放量」列 | `dataIndex: "avg_views_per_video"`，取整后格式化 |
| 爆款视频播放列增强 | 播放量下方追加视频标题（ellipsis + tooltip） |
| 「频道链接」+「爆款视频」合并 | 合并为「链接」列，竖向排列两个超链接，节省横向空间 |
| max_results 默认值 | `25` → `50`（`setFieldsValue` + form `initialValues` 两处同步修改） |

---

## 五、列表展示方案（修复后）

| 列 | 宽度 | 内容 |
|----|------|------|
| 频道 | 200 | 头像 + 频道名 + 创建时间 |
| 订阅数 | 90 | 格式化数值 |
| 总播放量 | 100 | 格式化数值（修复字段名后正确显示） |
| 视频数 | 75 | 格式化数值 |
| 均播放量 | 90 | 格式化数值 |
| 爆款视频播放 | 110 | 播放量（橙色加粗）+ 视频标题（灰色小字） |
| 链接 | 100 | 频道 / 爆款视频（竖排超链接） |
| 操作 | 100 | 添加关注 / 已关注 |

---

## 六、API 配额影响

`videos.list` 新增 `snippet` part 不增加 quota 消耗（YouTube API 按 request 计费，`part` 叠加不额外扣费）。  
`max_results` 从 25 → 50 不影响 `search.list` 配额（仍为单次调用，约 100 quota 单位）。

---

## 七、验收标准

| 场景 | 预期结果 |
|------|----------|
| 搜索关键词后，「总播放量」列 | 显示真实数值，不为 0 |
| 单次搜索最多可返回 | 50 条候选频道（受实际 YouTube 结果数量限制） |
| 「爆款视频播放」单元格 | 播放量上方为橙色数值，下方为视频标题灰色小字 |
| 「频道」单元格 | 频道名下方显示「X 年前创建」 |
| 「视频数」列 | 正确显示频道已发布视频数量 |
| 「均播放量」列 | 正确显示总播放量 ÷ 视频数的整数近似值 |
| 频道视频数为 0 时 | 均播放量显示 0，不报除零错误 |

## AutoDev 执行进度

- [x] Phase 1：需求对齐 / PRD
- [x] Phase 1.5：价值审查
- [x] Phase 2：设计与架构
- [x] Phase 3：实现
- [x] Phase 4：代码审查
- [x] Phase 5：业务验收

### 最新状态
- 当前阶段：Phase 7 交付完成
- 最近更新时间：2026-05-20
- 变更文件：
  - 后端新增：app/models/channel_cache.py, app/crud/channel_cache.py, app/services/channel_cache_service.py, alembic/versions/20260520_000001_add_channel_cache_table.py, alembic/versions/20260520_000002_add_refresh_attempted_at_to_channel_cache.py
  - 后端修改：app/schemas/discovery.py, app/api/v1/channels.py, app/services/youtube_service.py, app/db/base.py, app/core/config.py
  - 前端修改：src/services/authApi.ts, src/pages/youtube/ChannelList.tsx
- 验证命令：`cd frontend && npx tsc --noEmit && npm run build`
- 验证结果：tsc EXIT:0（仅预存test文件无关错误）, build EXIT:0（12.17s构建成功）
- 阻塞项：无
- 假设与取舍：
  - subscriber_count hidden → 映射为 -1（前端formatNumber待优化为显示"隐藏"）
  - 缓存富化quota暂未追踪（YouTube API按request计费，part叠加不额外扣费）
  - trust_env=False 为预存问题，不在本次scope内修复
  - blue_ocean_radar_scan 重复定义为预存问题，不在本次scope内修复
