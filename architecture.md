# 架构设计文档 — 数据缓存与跨模块联动

## 技术栈选型（含理由）
- **数据库缓存**：MySQL 表存储缓存数据，理由：项目已有 MySQL，无需引入 Redis；缓存数据需持久化和查询
- **唯一约束 + upsert**：通过联合唯一约束防止并发重复写入
- **前端无限滚动**：Intersection Observer API + Ant Design List，理由：轻量、无额外依赖

## 缓存策略
- **全局共享**：缓存数据不区分组织（无 org_id 字段），所有用户共享同一份缓存
- **历史记录按用户**：趋势历史、关键词历史按 user_id 保存
- **过期判断**：通过 updated_at 字段判断缓存是否过期
  - 趋势：1小时
  - 频道增长：12小时
  - 关键词研究：1天

## 数据结构设计

### 新增模型 1：`trend_cache`（趋势缓存表）
```python
class TrendCache(Base):
    __tablename__ = "trend_cache"
    __table_args__ = (UniqueConstraint("cache_date", "region", "category_id", name="uq_trend_cache"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_date: Mapped[date] = mapped_column(nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    category_id: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON字符串
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### 新增模型 2：`trend_history`（趋势历史记录表）
```python
class TrendHistory(Base):
    __tablename__ = "trend_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    cache_date: Mapped[date] = mapped_column(nullable=False)
    region: Mapped[str] = mapped_column(String(5), nullable=False)
    category_id: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    region_label: Mapped[str] = mapped_column(String(50), nullable=False)  # 如"美国"
    category_label: Mapped[str] = mapped_column(String(50), nullable=False)  # 如"全部品类"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### 新增模型 3：`keyword_cache`（关键词缓存表）
```python
class KeywordCache(Base):
    __tablename__ = "keyword_cache"
    __table_args__ = (UniqueConstraint("cache_date", "keyword", "region", "language", name="uq_keyword_cache"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_date: Mapped[date] = mapped_column(nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(5), nullable=False, default="US")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="zh")
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON字符串
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### 修改现有模型：频道增长缓存
不新增独立缓存表，而是在 channel_growth API 层增加缓存逻辑：
- 缓存维度：日期 + 用户（因为频道增长数据依赖用户的监控池）
- 缓存方式：在 API 层通过 updated_at 判断 YouTubeChannelHistory 是否在12小时内已更新

## API 接口设计

### 趋势相关
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/seo/trending` | 修改：增加缓存逻辑，1小时内返回缓存 |
| GET | `/api/seo/trend-history` | 新增：获取当前用户最近10条趋势历史 |
| POST | `/api/youtube/channels/add-by-channel-id` | 新增：通过 channel_id 入库频道 |

### 频道增长相关
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/channel-growth/dashboard` | 修改：增加缓存逻辑，12小时内复用 |

### 关键词研究相关
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/keyword/research` | 修改：增加缓存逻辑，1天内返回缓存 |
| GET | `/api/keyword/keyword-history` | 新增：获取当前用户关键词历史 |

## 文件组织结构

### 后端新增/修改文件
```
backend/app/models/trend_cache.py              # TrendCache + TrendHistory
backend/app/models/keyword_cache.py            # KeywordCache
backend/app/schemas/trend_cache.py             # 趋势缓存/历史 schemas
backend/app/schemas/keyword_cache.py           # 关键词缓存 schemas
backend/app/services/trend_cache_service.py    # 趋势缓存服务
backend/app/services/keyword_cache_service.py  # 关键词缓存服务
backend/app/api/v1/seo.py                      # 修改：缓存逻辑 + 历史API
backend/app/api/v1/channels.py                 # 修改：add-by-channel-id
backend/app/api/v1/channel_growth.py           # 修改：缓存逻辑
backend/app/api/v1/keyword.py                  # 修改：缓存逻辑 + 历史API
```

### 前端修改文件
```
frontend/src/pages/trend/TrendDiscovery.tsx      # 历史Card + 入库按钮 + 无限滚动
frontend/src/pages/keyword/KeywordResearch.tsx    # 历史Card + 无限滚动
frontend/src/pages/growth/ChannelGrowthDashboard.tsx  # Channel关键字联动
frontend/src/services/authApi.ts                 # 新增API调用函数
```

## Sprint规划

### Sprint 1：后端数据层 + 缓存API
- 3个新数据库模型 + Alembic迁移
- 趋势缓存服务（1小时过期）
- 关键词缓存服务（1天过期）
- 频道增长缓存逻辑（12小时过期）
- 趋势历史API + 关键词历史API
- 频道入库API（通过channel_id）

### Sprint 2：前端功能实现
- 趋势历史Card（最近10条）
- 趋势视频排行「博主入库」按钮 + 弹窗确认
- 趋势视频排行无限滚动
- 关键词研究热门视频无限滚动
- Channel Overview 关键字联动按钮
- 关键词研究历史Card

### Sprint 3：集成测试 + Review修复

## 风险登记册
| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 缓存数据量增长 | 中 | 低 | 定期清理>7天未访问的缓存 |
| 并发写入重复 | 低 | 中 | UNIQUE约束 + upsert |
| 频道入库重复 | 中 | 低 | 检查是否已存在，已存在则提示 |
| 无限滚动性能 | 低 | 中 | 虚拟滚动 + 数据分批加载 |