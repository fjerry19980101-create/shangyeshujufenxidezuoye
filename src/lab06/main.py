"""lab06 银行贷款流程价值流分析（VSM）。

教材出处：第 3 章 3.6.2 银行贷款流程优化示例（PDF p124-127，VSM 图示）

业务问题
--------
客户投诉贷款审批流程耗时过长、需多次往返银行提交资料、小错误频繁。
需要找到流程中可以优化的节点，提升客户满意度、减少客诉。

分析路径（教材 VSM 思路）
--------
流程拆解（5 节点、逐节点耗时）→ 与行业 TOP 银行标杆对比定位差距
→ 业务访谈找根因 → 制定 RPA + AI 自动化方案 → 优化后总周期对比。

数据说明：教材已给出全部节点耗时，本实验直接录入书中数值，不做模拟（见 data_prep.py）。
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

from common.config import COLORS, save_fig, save_table, setup_plot
from lab06.data_prep import vsm_summary, vsm_table


def draw_timeline(ax, df, time_col: str, title: str, highlight=()) -> None:
    """在坐标轴上绘制一行 VSM 节点时间轴。"""
    colors = {"增值": COLORS[2], "必要非增值": COLORS[5], "纯非增值": "#B9B9B9"}
    y, h, w, gap = 0.42, 0.40, 1.05, 0.28

    for i, row in df.iterrows():
        x = i * (w + gap)
        face = COLORS[1] if row["序号"] in highlight else colors[row["价值判定"]]
        edge = COLORS[3] if row["序号"] in highlight else "white"
        ax.add_patch(
            Rectangle((x, y), w, h, facecolor=face, edgecolor=edge,
                      linewidth=2.5, joinstyle="round")
        )
        label = textwrap.fill(row["流程节点"], 7)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontsize=8.5, color="white")
        ax.text(x + w / 2, y + h + 0.05, f"{row['序号']}", ha="center",
                fontsize=9, fontweight="bold", color="#555555")
        ax.text(x + w / 2, y - 0.09, f"{row[time_col]:g} 天", ha="center",
                fontsize=10, fontweight="bold",
                color=COLORS[3] if row["序号"] in highlight else "#333333")

        if i < len(df) - 1:
            ax.add_patch(
                FancyArrowPatch((x + w, y + h / 2), (x + w + gap, y + h / 2),
                                arrowstyle="-|>", mutation_scale=14,
                                color="#777777", lw=1.2)
            )

    total_x = len(df) * (w + gap) - gap + 0.25
    ax.text(total_x + 0.25, y + h / 2, f"总周期\n{df[time_col].sum():g} 天",
            ha="left", va="center", fontsize=10, fontweight="bold", color=COLORS[0])
    ax.set_xlim(0, total_x + 1.05)
    ax.set_ylim(0.1, 1.15)
    ax.set_title(title, loc="left", fontsize=12)
    ax.axis("off")


def plot_vsm(df) -> Path:
    fig, axes = plt.subplots(2, 1, figsize=(12, 5.6))
    draw_timeline(
        axes[0], df, "当前耗时",
        "当前流程：7 天（橙色为与行业标杆差距最大的节点 2、3）",
        highlight=(2, 3),
    )
    draw_timeline(
        axes[1], df, "行业标杆",
        "优化目标：4 天（节点 2、3 各压缩至 0.5 天，其余节点不变）",
    )
    fig.suptitle("银行贷款审批流程价值流图（VSM）", fontsize=14, fontweight="bold")
    fig.tight_layout()
    return save_fig(fig, "lab06_vsm_timeline")


def plot_node_compare(df) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.4))
    x = np.arange(len(df))
    w = 0.36
    ax.bar(x - w / 2, df["当前耗时"], width=w, color=COLORS[1], label="当前流程")
    ax.bar(x + w / 2, df["行业标杆"], width=w, color=COLORS[0], label="行业 TOP 银行")
    for i, row in df.iterrows():
        ax.text(i - w / 2, row["当前耗时"] + 0.06, f"{row['当前耗时']:g}",
                ha="center", fontsize=9)
        ax.text(i + w / 2, row["行业标杆"] + 0.06, f"{row['行业标杆']:g}",
                ha="center", fontsize=9)
        if row["差距"] > 0:
            ax.text(i, max(row["当前耗时"], row["行业标杆"]) + 0.38,
                    f"差距 {row['差距']:g} 天", ha="center", fontsize=9,
                    color=COLORS[3], fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['序号']}. {r['流程节点']}" for _, r in df.iterrows()],
                       fontsize=8.5)
    ax.set_ylabel("耗时（天）")
    ax.set_ylim(0, 2.7)
    ax.set_title("各流程节点耗时：当前 vs 行业标杆（仅节点 2、3 存在差距）")
    ax.legend()
    return save_fig(fig, "lab06_node_compare")


def plot_summary(summary) -> Path:
    metrics = summary.set_index("指标")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))

    ax = axes[0]
    vals = [metrics.loc["总周期（天）", "当前流程"], metrics.loc["总周期（天）", "优化目标"]]
    bars = ax.bar(["当前流程", "优化目标"], vals, color=[COLORS[1], COLORS[2]], width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.12, f"{v:g} 天",
                ha="center", fontsize=11)
    ax.set_ylim(0, 8.5)
    ax.set_title(f"总周期压缩：7 → 4 天（-{(7 - 4) / 7:.0%}）")
    ax.set_ylabel("天")

    ax = axes[1]
    ratios = [
        metrics.loc["增值时间占比", "当前流程"],
        metrics.loc["增值时间占比", "优化目标"],
    ]
    bars = ax.bar(["当前流程", "优化目标"], ratios, color=[COLORS[1], COLORS[2]], width=0.5)
    for b, v in zip(bars, ratios):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.008, f"{v:.1%}",
                ha="center", fontsize=11)
    ax.set_ylim(0, 0.6)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("增值时间占比（增值 2 天 / 总周期）")

    fig.suptitle("优化效果：周期缩短 3 天，增值占比翻倍", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return save_fig(fig, "lab06_summary")


def main() -> None:
    setup_plot()

    df = vsm_table()
    summary = vsm_summary(df)
    metrics = summary.set_index("指标")

    current_total = metrics.loc["总周期（天）", "当前流程"]
    target_total = metrics.loc["总周期（天）", "优化目标"]
    gap = metrics.loc["可压缩时间（天）", "当前流程"]
    value_added = metrics.loc["增值时间（天）", "当前流程"]
    ratio_now = metrics.loc["增值时间占比", "当前流程"]
    ratio_after = metrics.loc["增值时间占比", "优化目标"]

    print("=" * 66)
    print("lab06 银行贷款流程价值流分析（教材数值，非模拟）")
    print("=" * 66)
    for _, r in df.iterrows():
        print(
            f"{r['序号']}. {r['流程节点']}：{r['当前耗时']:g} 天"
            f"（标杆 {r['行业标杆']:g} 天，差距 {r['差距']:g} 天）"
            f"  价值判定：{r['价值判定']}"
        )
    print("-" * 66)
    print(f"当前总周期 {current_total:g} 天，其中增值时间仅 {value_added:g} 天"
          f"（增值占比 {ratio_now:.1%}）")
    print(f"与行业 TOP 银行相比，仅节点 2、3 存在差距，合计可压缩 {gap:g} 天")
    print(f"优化目标总周期 {target_total:g} 天（压缩 {gap / current_total:.1%}），增值占比提升至 {ratio_after:.1%}")
    print("-" * 66)
    print("业务根因与改进措施：")
    for _, r in df.iterrows():
        if r["差距"] > 0:
            print(f"  节点 {r['序号']} {r['流程节点']}")
            print(f"    根因：{r['业务问题']}")
            print(f"    措施：{r['改进措施']}")
    print(
        "\n验证计划：措施执行 1 个月后，重新评估关键节点平均耗时并收集客户反馈，\n"
        "确认客诉是否改善；通过持续监控与优化确保改进有效。"
    )

    save_table(df, "lab06_vsm_nodes")
    save_table(summary, "lab06_summary")

    plot_vsm(df)
    plot_node_compare(df)
    plot_summary(summary)

    print("\n产物已写入 output/figures 与 output/tables（lab06_*）。")


if __name__ == "__main__":
    main()
