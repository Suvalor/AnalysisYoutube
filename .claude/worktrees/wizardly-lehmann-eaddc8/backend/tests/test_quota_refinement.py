"""YouTube API 配额精确计算测试。"""

from __future__ import annotations

import pytest

from app.services.quota_service import calc_quota_points, API_QUOTA_TABLE


# ── calc_quota_points 纯函数测试 ──

def test_search_fixed_100():
    """search.list 固定 100 点，part_count 不影响。"""
    assert calc_quota_points("search", times=1) == 100
    assert calc_quota_points("search", times=1, part_count=5) == 100
    assert calc_quota_points("search", times=3) == 300


def test_channels_by_part_count():
    """channels.list 配额 = part_count × 1。"""
    assert calc_quota_points("channels", times=1, part_count=1) == 1
    assert calc_quota_points("channels", times=1, part_count=2) == 2
    assert calc_quota_points("channels", times=1, part_count=3) == 3
    assert calc_quota_points("channels", times=5, part_count=2) == 10


def test_videos_by_part_count():
    """videos.list 配额 = part_count × 1。"""
    assert calc_quota_points("videos", times=1, part_count=1) == 1
    assert calc_quota_points("videos", times=1, part_count=2) == 2
    assert calc_quota_points("videos", times=1, part_count=4) == 4
    assert calc_quota_points("videos", times=3, part_count=4) == 12


def test_playlist_items_by_part_count():
    """playlistItems.list 配额 = part_count × 1。"""
    assert calc_quota_points("playlistItems", times=1, part_count=1) == 1
    assert calc_quota_points("playlistItems", times=2, part_count=1) == 2


def test_comment_threads_by_part_count():
    """commentThreads.list 配额 = part_count × 1。"""
    assert calc_quota_points("commentThreads", times=1, part_count=1) == 1
    assert calc_quota_points("commentThreads", times=5, part_count=1) == 5


def test_backward_compat_default_part_count():
    """不传 part_count 时默认为 1，向后兼容。"""
    assert calc_quota_points("channels", times=1) == 1
    assert calc_quota_points("videos", times=1) == 1
    assert calc_quota_points("playlistItems", times=1) == 1
    assert calc_quota_points("commentThreads", times=1) == 1


def test_unknown_api():
    """未知 API 方法返回 0。"""
    assert calc_quota_points("unknown", times=1) == 0


def test_times_zero():
    """times=0 时仍至少 1 次。"""
    assert calc_quota_points("channels", times=0) == 1


# ── API_QUOTA_TABLE 完整性测试 ──

def test_quota_table_has_all_methods():
    """查表包含所有已知 API 方法。"""
    expected = {"search", "channels", "videos", "playlistItems", "commentThreads"}
    assert set(API_QUOTA_TABLE.keys()) == expected


def test_search_base_100_per_part_0():
    """search 基础 100，per_part 0。"""
    assert API_QUOTA_TABLE["search"]["base"] == 100
    assert API_QUOTA_TABLE["search"]["per_part"] == 0


def test_channels_base_0_per_part_1():
    """channels 基础 0，per_part 1。"""
    assert API_QUOTA_TABLE["channels"]["base"] == 0
    assert API_QUOTA_TABLE["channels"]["per_part"] == 1


def test_videos_base_0_per_part_1():
    """videos 基础 0，per_part 1。"""
    assert API_QUOTA_TABLE["videos"]["base"] == 0
    assert API_QUOTA_TABLE["videos"]["per_part"] == 1


# ── 实际场景测试 ──

def test_navigation_guide_scenario():
    """出海导航场景：5次search + 10次channels(part=2)。"""
    search_cost = calc_quota_points("search", times=5)
    channels_cost = calc_quota_points("channels", times=10, part_count=2)
    assert search_cost == 500
    assert channels_cost == 20
    assert search_cost + channels_cost == 520


def test_bulk_pipeline_scenario():
    """批量流水线：channels(part=3) + playlistItems(part=1) + videos(part=4)。"""
    ch = calc_quota_points("channels", times=1, part_count=3)
    pl = calc_quota_points("playlistItems", times=1, part_count=1)
    vid = calc_quota_points("videos", times=1, part_count=4)
    assert ch == 3
    assert pl == 1
    assert vid == 4


def test_blue_ocean_radar_scenario():
    """蓝海雷达：1次search + 1次videos(part=2) + 1次channels(part=2)。"""
    search = calc_quota_points("search", times=1)
    videos = calc_quota_points("videos", times=1, part_count=2)
    channels = calc_quota_points("channels", times=1, part_count=2)
    assert search == 100
    assert videos == 2
    assert channels == 2
    assert search + videos + channels == 104


def test_comment_scrape_scenario():
    """评论抓取：5次commentThreads(part=1)。"""
    cost = calc_quota_points("commentThreads", times=5, part_count=1)
    assert cost == 5


# ── quota_guard_service 测试 ──

def test_quota_guard_uses_calc_quota_points():
    """quota_guard 使用 calc_quota_points 估算。"""
    from app.services.quota_guard_service import DAILY_QUOTA_LIMIT
    assert DAILY_QUOTA_LIMIT == 10_000
    # 验证估算：15次search + 15次channels(part=2) = 1500 + 30 = 1530
    search = calc_quota_points("search", times=15)
    channels = calc_quota_points("channels", times=15, part_count=2)
    assert search == 1500
    assert channels == 30
    assert search + channels == 1530
