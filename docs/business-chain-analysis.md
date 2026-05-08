# YouTube Compass — 核心业务链路分析与修正建议

> Author: 业务分析 | Date: 2026-05-08 | Status: 审阅中
>
> 基于核心目标出发的全链路诊断报告

---

## 一、核心目标重申

项目的两个核心目标：

1. **博主发现与追踪**：追踪对标博主、检索新秀博主（粉丝少但增长快），挖掘潜在潜力视频
2. **视频混剪输出**：将下载的视频混剪，生成新视频并提供下载地址

这两条主链路之间存在强依赖关系：**发现 → 追踪 → 下载 → 混剪 → 输出**，缺任何一环都会导致用户流失。

---

## 二、现有链路全景（As-Is）

### 2.1 博主发现与追踪链路

```
[入口] 用户输入关键词
    ↓
[蓝海雷达] BlueOceanRadar.tsx → /radar/scan
    ↓ 返回视频列表（按爆款系数排序）
[视频维度] GlobalVideoList / VideoBoard 查看视频统计
    ↓
[频道跳转] 点击视频作者 → ChannelDetail.tsx
    ↓
[手动追踪] 用户手动搜索频道 → ChannelList.tsx → /channels/add-by-channel-id
    ↓
[竞对面板] CompetitorAnalysis.tsx 查看多频道对比
    ↓
[AI洞察] competitor_ai_service → AI竞争格局分析
```

**问题**：步骤 3→4 之间存在跳转断裂，从发现视频到追踪博主需要用户手动查找频道 ID。

---

### 2.2 视频下载与混剪链路

```
[入口] 用户在蓝海雷达/视频列表发现潜力视频
    ↓
[下载任务] DownloadList.tsx → POST /downloads/download（video_ids 列表）
    ↓ yt-dlp 后台执行
[任务查看] 轮询 /downloads/download-tasks 查看进度
    ↓
[混剪配置] MixConfigModal.tsx → POST /materials/mix
    ↓ ffmpeg 后台执行
[任务完成] 轮询 /materials/mix-tasks 查看状态
    ↓
[文件下载] GET /downloads/download-tasks/{id}/file（本地文件服务）
```

**问题**：步骤 1→2 需要用户在不同页面之间手动跳转，从"发现视频"到"提交下载"没有一键路径。

---

## 三、链路断点诊断（问题清单）

### P0 — 核心链路断裂（直接影响核心目标）

#### 断点 A：「视频发现 → 博主追踪」缺一键转化

**现象**：
- 蓝海雷达扫描结果是**视频**维度列表，展示 title/views/viral_coefficient
- 用户想追踪某个视频的作者，必须：
  1. 记住/复制频道 ID
  2. 切换到「频道列表」页面
  3. 手动输入 ID 添加到追踪池
- 没有从雷达结果直接「追踪此博主」的按钮

**影响**：用户在发现高价值博主的关键时刻被迫中断操作，转化率极低。

---

#### 断点 B：「博主追踪 → 新视频监控」缺自动化

**现象**：
- `UserCompetitorPool` 表存储了追踪列表，但没有定时任务轮询新视频
- 用户必须手动触发 `POST /youtube/channels/batch-update` 才能更新频道数据
- 没有「哪个被追踪博主昨天发了新视频」的主动推送或通知机制

**影响**：追踪功能沦为静态标记，无法实现「主动监控」的核心价值。

---

#### 断点 C：「视频发现 → 一键下载」缺集成入口

**现象**：
- 蓝海雷达结果页、全局视频列表页没有「下载」操作按钮
- 用户需要：
  1. 在雷达结果中记住目标视频
  2. 切换到「下载管理」页面
  3. 手动输入视频 URL 或 ID
- 下载管理页与发现页完全割裂

**影响**：从「发现潜力视频」到「下载视频」的核心操作需要 3+ 步，摩擦极大。

---

#### 断点 D：「下载完成 → 混剪选片」缺关联视图

**现象**：
- 下载完成后，用户停留在下载列表页
- 混剪入口（MixConfigModal）藏在什么位置目前代码中不清晰，可能是独立的素材管理页
- 无法在下载列表直接「勾选已下载视频 → 发起混剪」
- `VideoHighlight`（精彩片段）表存在，但何时触发提取未见自动逻辑，用户也无法手动触发

**影响**：下载与混剪两个核心操作之间缺乏连续体验，用户必须重新学习在哪里发起混剪。

---

#### 断点 E：「混剪完成 → 文件下载」链路模糊

**现象**：
- `GET /downloads/download-tasks/{id}/file` 提供文件服务
- `GET /downloads/download-tasks/{id}/play-token` 提供短期令牌
- 但混剪任务完成后的输出文件是否也走同一套接口？`MixTask.output_path` 如何映射到下载 URL？
- 前端是否有明确的「混剪完成 → 点击下载」按钮和跳转路径？

**影响**：用户可能不知道混剪结果在哪里，或无法直接下载。

---

### P1 — 体验断层（影响效率，但有绕过路径）

#### 断点 F：新秀博主发现缺专项功能

**现象**：
- 蓝海雷达过滤条件有 `max_subscribers`（粉丝上限），可以间接筛出小博主
- 但没有专门的「新秀博主排行榜」：按粉丝增长速度、近期发布频率、粉丝/视频比排序
- `YouTubeChannelHistory` 表存在，说明历史数据有积累，但没有增长率计算和展示界面

**影响**：发现「正在爆发的新秀」（粉丝少但增长快）需要用户靠直觉判断，无数据支撑。

---

#### 断点 G：下载目录不可配置

**现象**：
- `DownloadTask.local_path` 由后端 `downloader_service.py` 决定存储路径
- 没有找到用户/组织级别的「下载根目录」配置入口
- 多用户场景下，无法区分各用户的存储空间

**影响**：在生产环境多用户部署时，磁盘管理混乱；用户无法指定下载到特定目录。

---

#### 断点 H：混剪参数的「精彩片段提取」逻辑不透明

**现象**：
- `MixTask` 有 `use_highlights` 字段，启用后从 `VideoHighlight` 取片段
- 但 `VideoHighlight` 的数据何时产生？`highlight_extract_service.py` 何时被调用？
- 用户无法手动标注精彩片段，也无法查看已提取的精彩片段列表

**影响**：混剪质量依赖自动提取，但提取时机不透明，用户无法干预和优化。

---

#### 断点 I：竞对分析缺「视频级别」对比

**现象**：
- `CompetitorAnalysis.tsx` 主要是频道维度（粉丝、总播放、视频数）的对比
- 没有「A博主的这类视频 vs B博主的这类视频」的横向对比
- 没有展示「被追踪博主近30天爆款视频」的聚合视图

**影响**：竞对分析停留在宏观频道指标层面，无法支撑「学什么、拍什么」的创作决策。

---

### P2 — 体验优化（锦上添花）

#### 断点 J：蓝海雷达扫描结果无持久化

- 每次扫描结果不保存，刷新即丢失
- 无历史扫描记录对比（何时发现的，当时的爆款系数是多少）

#### 断点 K：下载任务无批量操作

- 发现 10 个潜力视频后，需要逐个提交下载，没有「批量选中 → 一键下载」

#### 断点 L：混剪没有预览功能

- 混剪完成前无法预览效果，只能等待任务完成后再查看

---

## 四、修正建议（To-Be）

### 4.1 修复 P0 断点——核心链路贯通

#### 建议 A-1：雷达结果增加「追踪博主」一键操作

**位置**：`BlueOceanRadar.tsx` 结果表格、`GlobalVideoList.tsx`

**方案**：
- 每行视频记录增加「追踪博主」按钮
- 点击后调用 `POST /channels/add-by-channel-id`，传入该视频的 `channel_id`
- 成功后显示「已加入追踪池」提示，不跳转页面

**后端**：`/channels/add-by-channel-id` 已存在，无需新增接口，仅需前端改动。

```tsx
// GlobalVideoList.tsx 操作列新增
<Button size="small" onClick={() => handleTrackChannel(video.channel_id)}>
  追踪博主
</Button>
```

---

#### 建议 A-2：雷达结果增加「一键下载」操作

**位置**：`BlueOceanRadar.tsx` 结果表格、`GlobalVideoList.tsx`

**方案**：
- 每行视频增加勾选框（多选）
- 表格顶部增加「下载选中视频」批量操作按钮
- 点击后直接调用 `POST /downloads/download`，传入选中的 `video_id` 列表
- 提交后给出成功提示，并显示跳转到「下载管理」的链接

```tsx
// 批量操作栏
<Button onClick={() => handleBatchDownload(selectedVideoIds)}>
  下载选中视频（{selectedVideoIds.length}）
</Button>
```

---

#### 建议 B-1：追踪频道定时更新任务

**位置**：`backend/app/`，新增 `app/tasks/channel_monitor.py`

**方案**：
- 后端新增定时任务（APScheduler 或 Celery Beat），每日/每6小时执行一次
- 遍历 `user_competitor_pools` 中的频道，调用 `fetch_recent_videos()` 拉取新视频
- 新视频存入 `youtube_videos` 表，并标记 `is_new=True`
- 前端「竞对分析」页展示「最近 7 天新发布」标签

**备选方案（简化）**：
- 不引入 Celery，在用户打开「竞对分析」页时触发懒更新
- 后端新增 `GET /channels/{id}/refresh` 接口，检查距上次更新时间决定是否拉取

---

#### 建议 D-1：下载列表增加「发起混剪」入口

**位置**：`DownloadList.tsx`

**方案**：
- 下载完成的视频行增加勾选框
- 已下载视频可多选，顶部「混剪选中视频」按钮弹出 `MixConfigModal`
- `MixConfigModal` 预填充已选视频的 `download_task_id` 列表
- 混剪接口 `POST /materials/mix` 接受 `download_task_ids`，后端从 `local_path` 读取文件

**数据流**：
```
DownloadTask（COMPLETED）→ 勾选 → MixConfigModal（预填 source_video_paths）
→ POST /materials/mix → MixTask（PENDING）→ ffmpeg → MixTask（COMPLETED）
→ 下载链接（/materials/mix-tasks/{id}/file）
```

---

#### 建议 E-1：混剪完成后提供明确下载地址

**位置**：`backend/app/api/v1/materials.py`，`MixTask` 模型

**方案**：
- 确认 `MixTask` 完成后，`output_path` 字段存储混剪输出文件路径
- 新增接口 `GET /materials/mix-tasks/{id}/download`，流式返回文件
- 或将混剪结果上传到云存储，返回签名 URL
- 前端混剪任务列表：任务完成后显示「下载混剪结果」按钮

**后端改动**（最小化）：
```python
# materials.py 新增
@router.get("/mix-tasks/{task_id}/download")
async def download_mix_result(task_id: int, ...):
    task = await get_mix_task(db, task_id, user_id)
    return FileResponse(task.output_path, filename=f"mix_{task_id}.mp4")
```

---

### 4.2 修复 P1 断点——体验提升

#### 建议 F-1：新秀博主发现模块

**新增页面**：`pages/youtube/RisingCreators.tsx`

**方案**：
- 从 `YouTubeChannel` + `YouTubeChannelHistory` 计算增长率
- 排行榜维度：
  - 7天粉丝增长率（`subscriber_count` 环比）
  - 近30天视频发布频率
  - 平均视频爆款系数（最近10个视频）
- 新增后端接口 `GET /channels/rising`：
  ```python
  # 查询逻辑
  SELECT c.*, 
    (c.subscriber_count - h.subscriber_count) / h.subscriber_count AS growth_rate
  FROM youtube_channels c
  JOIN youtube_channel_history h ON c.id = h.channel_id
  WHERE h.recorded_at >= NOW() - INTERVAL 7 DAY
  ORDER BY growth_rate DESC
  LIMIT 50
  ```

---

#### 建议 G-1：下载根目录可配置

**位置**：`backend/app/core/config.py`，`IntegrationSettings` 模型

**方案**：
- 在组织配置（`integration_settings`）增加 `download_base_path` 字段
- 前端配置中心增加「下载目录」设置项
- `downloader_service.py` 从配置读取根目录：
  ```python
  base_path = integration_config.download_base_path or settings.DEFAULT_DOWNLOAD_PATH
  task_path = os.path.join(base_path, str(org_id), str(user_id), f"{video_id}.mp4")
  ```

---

#### 建议 H-1：精彩片段提取透明化

**位置**：`DownloadList.tsx`，`highlight_extract_service.py`

**方案**：
- 下载完成后自动触发精彩片段提取（后台异步任务）
- 下载列表增加「精彩片段」列，显示提取状态和片段数量
- 新增「精彩片段预览」对话框，展示 `VideoHighlight` 列表，支持播放器定位
- 用户可手动标记/删除精彩片段

---

#### 建议 I-1：竞对分析增加视频维度

**位置**：`CompetitorAnalysis.tsx`

**方案**：
- 追踪频道面板增加「近期爆款视频」Tab
- 展示每个被追踪频道近30天内 `viral_coefficient` 最高的视频
- 支持跨频道横向对比：同类主题（通过 `ai_tags` 匹配）视频的表现

---

## 五、完整贯通的理想业务链路（To-Be）

```
[Step 1 发现]
  蓝海雷达 输入关键词 → 返回潜力视频列表（带爆款系数）
     ↓ 每行支持：「追踪博主」「加入下载队列」「查看频道」
     
[Step 2 追踪]
  「追踪博主」一键添加到竞对池
  系统每日自动拉取被追踪频道的新视频
  「新秀榜」页面：按增长速度排序的新兴博主
     ↓
     
[Step 3 下载]
  雷达结果 / 追踪频道新视频 → 多选 → 「批量下载」
  下载任务自动完成精彩片段提取
  下载列表：进度、精彩片段数、文件大小
     ↓
     
[Step 4 混剪]
  下载列表勾选多个视频 → 「混剪选中视频」
  MixConfigModal：配置比例（16:9/9:16）、音频、是否使用精彩片段
  ffmpeg 后台处理
     ↓
     
[Step 5 输出]
  混剪任务完成 → 「下载混剪结果」按钮
  提供直链下载 / 云存储签名 URL
  可选：发布到 YouTube（/youtube/publish 接口已存在）
```

---

## 六、实施优先级路线图

### Phase 1（1-2周）：贯通核心链路

| 改动 | 类型 | 影响范围 | 预估工作量 |
|------|------|--------|---------|
| 雷达结果增加「追踪博主」按钮 | 前端 | BlueOceanRadar.tsx, GlobalVideoList.tsx | 0.5天 |
| 雷达结果增加「下载」多选操作 | 前端 | BlueOceanRadar.tsx | 1天 |
| 下载列表增加「发起混剪」入口 | 前端+后端 | DownloadList.tsx, materials.py | 1天 |
| 混剪完成提供下载接口 | 后端 | materials.py | 0.5天 |

**Phase 1 完成标志**：用户可在蓝海雷达发现视频后，3步内完成下载并发起混剪。

---

### Phase 2（2-4周）：监控与发现增强

| 改动 | 类型 | 影响范围 | 预估工作量 |
|------|------|--------|---------|
| 追踪频道定时更新（后台任务） | 后端 | 新增 channel_monitor.py | 2天 |
| 新秀博主排行榜接口+页面 | 前端+后端 | 新增 RisingCreators.tsx | 3天 |
| 竞对分析增加近期爆款视频Tab | 前端+后端 | CompetitorAnalysis.tsx | 2天 |
| 精彩片段提取透明化 | 前端+后端 | DownloadList.tsx | 2天 |

---

### Phase 3（持续优化）：体验打磨

| 改动 | 类型 | 影响范围 |
|------|------|--------|
| 下载目录可配置 | 后端+前端 | config.py, ConfigCenter.tsx |
| 蓝海雷达扫描结果持久化 | 后端 | 新增 radar_scan_history 表 |
| 批量下载进度聚合视图 | 前端 | DownloadList.tsx |
| 混剪结果预览功能 | 前端 | 视频播放器组件 |

---

## 七、技术风险说明

### 风险 1：YouTube API 配额

- 追踪频道定时更新会消耗大量配额（每个 `channels.list` 调用 ~1 单元，但 `search.list` 需 100 单元）
- **建议**：更新时优先使用 `channels.list`（直接频道ID查询，成本低），仅针对需要视频更新的频道才调用 `search.list`
- 现有 `quota_service.py` 已有配额追踪，需在更新任务中接入

### 风险 2：磁盘容量

- 视频文件较大（通常 200MB-2GB/个），多用户批量下载会快速消耗磁盘
- **建议**：增加下载配额限制（per user/org），定时清理超过 N 天的已下载文件
- `DownloadTask.local_path` 在文件删除后应更新状态为 `EXPIRED`

### 风险 3：ffmpeg 并发资源

- 多个混剪任务并发执行时，CPU/内存压力大
- **建议**：混剪任务队列限制并发数（建议 max 2-3 个），超出的放入等待队列

---

## 八、现有优势资产（勿重复造轮子）

以下已有的基础设施应充分复用：

| 现有能力 | 文件位置 | 可复用于 |
|--------|--------|--------|
| `viral_coefficient` 计算 | `youtube_service.py` | 新秀博主排行榜 |
| `YouTubeChannelHistory` 表 | `models/channel.py` | 增长率计算 |
| `VideoHighlight` 模型 | `models/video.py` | 精彩片段透明化 |
| `play_token` 短期令牌 | `downloads.py` | 混剪结果播放预览 |
| `object_storage.py` 多云上传 | `services/` | 混剪结果上传云端 |
| `/youtube/publish` 接口 | `youtube.py` | 混剪结果一键发布 |
| `config_manager.py` 配置中心 | `services/` | 下载目录配置扩展 |

---

*文档由业务链路分析生成，建议在每个 Phase 完成后更新此文档，记录实际与预期的偏差。*
