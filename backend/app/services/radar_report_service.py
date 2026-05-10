"""蓝海雷达报告生成服务：将扫描结果转为 Markdown 格式报告。"""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.radar import BlueOceanChannelItem


def generate_radar_report(
    *,
    scan_items: list[BlueOceanChannelItem],
    keyword: str = "",
    ai_summary: str | None = None,
) -> str:
    """
    将蓝海雷达扫描结果生成结构化 Markdown 报告。
    前端可渲染为 HTML 并通过 window.print() 或 html2canvas 导出 PDF/图片。
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []

    # 标题
    lines.append("# 蓝海雷达扫描报告")
    lines.append("")
    if keyword:
        lines.append(f"**关键词**：{keyword}")
    lines.append(f"**生成时间**：{now}")
    lines.append(f"**扫描结果**：共 {len(scan_items)} 条潜力频道")
    lines.append("")
    lines.append("---")
    lines.append("")

    # AI 总结
    if ai_summary:
        lines.append("## AI 分析总结")
        lines.append("")
        lines.append(ai_summary)
        lines.append("")
        lines.append("---")
        lines.append("")

    # 频道列表表格
    if scan_items:
        lines.append("## 潜力频道列表")
        lines.append("")
        lines.append("| # | 频道名称 | 订阅数 | 总播放 | 爆款播放 | 爆款系数 |")
        lines.append("|---|---------|--------|--------|---------|---------|")
        for i, item in enumerate(scan_items, 1):
            lines.append(
                f"| {i} "
                f"| [{item.title}]({item.channel_url}) "
                f"| {item.subscriber_count:,} "
                f"| {item.total_views:,} "
                f"| {item.viral_view_count:,} "
                f"| {item.outlier_score:.1f} |"
            )
        lines.append("")
        lines.append("---")
        lines.append("")

        # 关键指标
        subs_list = [item.subscriber_count for item in scan_items]
        views_list = [item.viral_view_count for item in scan_items]
        scores_list = [item.outlier_score for item in scan_items]

        lines.append("## 关键指标")
        lines.append("")
        lines.append(f"- **平均订阅数**：{sum(subs_list) // len(subs_list):,}")
        lines.append(f"- **最高爆款播放**：{max(views_list):,}")
        lines.append(f"- **平均爆款系数**：{sum(scores_list) / len(scores_list):.1f}")
        lines.append(f"- **最高爆款系数**：{max(scores_list):.1f}")
        lines.append("")

        # Top 5 爆款
        top5 = sorted(scan_items, key=lambda x: x.outlier_score, reverse=True)[:5]
        lines.append("## Top 5 爆款频道")
        lines.append("")
        for i, item in enumerate(top5, 1):
            lines.append(f"{i}. **{item.title}** — 爆款系数 {item.outlier_score:.1f}，订阅 {item.subscriber_count:,}")
            lines.append(f"   - 频道：{item.channel_url}")
            lines.append(f"   - 爆款视频：{item.viral_video_url}")
        lines.append("")
    else:
        lines.append("## 无扫描结果")
        lines.append("")
        lines.append("本次扫描未找到符合条件的频道。")
        lines.append("")

    # 页脚
    lines.append("---")
    lines.append("")
    lines.append("*报告由 YouTube Compass 蓝海雷达自动生成*")

    return "\n".join(lines)
