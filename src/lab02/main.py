"""lab02 广告与销售漏斗分析。

教材出处：第 2 章 2.1.2 链式分析（PDF p61-70，Excel 漏斗图）

业务问题
--------
新产品投入大量推广资源但效果平平。整体转化率只有 1.08%，而相似成熟产品
广告曝光转化率均值 5%、最高 15%。需要定位瓶颈环节，把有限预算用在刀刃上。

分析路径（与教材口径一致）
--------
广告触达 → 查看广告 → 跳转商品介绍页 → 点击立即购买 → 购买成功
逐环节算转化率：触达 10% / 跳转 20% / 购买意愿 60% / 购买 90%
→ 与行业均值、行业最高对比，定位瓶颈
→ 测算单因素与双因素提升后的总体转化率。

数据说明：教材只给转化率，本实验按书中比例构造漏斗人数（见 data_prep.py）。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common.config import COLORS, save_fig, save_table, setup_plot
from lab02.data_prep import (
    BASELINE_TOUCH,
    INDUSTRY,
    build_funnel,
    build_improved_funnel,
    scenario_table,
)


def plot_funnel(funnel: pd.DataFrame) -> Path:
    """横向居中条形漏斗图；宽度按人数平方根缩放，人数以标签为准。"""
    fig, ax = plt.subplots(figsize=(9, 5.6))
    n = len(funnel)
    max_users = funnel["人数"].max()
    colors = [COLORS[0], "#3A6E9E", "#5486B3", COLORS[1], COLORS[3]]

    for i, row in funnel.iterrows():
        width = np.sqrt(row["人数"] / max_users)
        left = (1 - width) / 2
        ax.barh(i, width, left=left, height=0.62, color=colors[i], alpha=0.92)
        if width >= 0.28:
            ax.text(0.5, i, f"{row['人数']:,}", ha="center", va="center",
                    color="white", fontsize=11, fontweight="bold")
        else:
            # 条形过窄时把人数标到右侧，避免文字被条形裁切
            ax.text(left + width + 0.015, i, f"{row['人数']:,}",
                    ha="left", va="center", color="#333333",
                    fontsize=10.5, fontweight="bold")
        if i > 0:
            ax.annotate(
                f"{row['环节转化率']:.0%}  {row['转化率名称']}",
                xy=(0.5 + width / 2, i - 0.5),
                xytext=(0.5 + width / 2 + 0.12, i - 0.5),
                va="center", fontsize=9, color="#444444",
                arrowprops=dict(arrowstyle="-|>", color="#999999", lw=0.8),
            )

    ax.set_yticks(range(n))
    ax.set_yticklabels(funnel["环节"])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.75)
    ax.set_xticks([])
    ax.set_title(
        f"广告用户行为漏斗（总体转化率 {funnel['累计转化率'].iloc[-1]:.2%}）\n"
        "条形宽度按人数平方根缩放，实际人数见条内标注",
        fontsize=12,
    )
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(False)
    return save_fig(fig, "lab02_funnel")


def plot_benchmark(funnel: pd.DataFrame, imp: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.35, 1]})

    # 左：两个瓶颈环节 vs 行业
    ax = axes[0]
    x = np.arange(len(INDUSTRY))
    w = 0.26
    for k, col in enumerate(["本项目", "行业均值", "行业最高"]):
        ax.bar(x + (k - 1) * w, INDUSTRY[col], width=w, label=col, color=COLORS[k])
        for xi, v in zip(x + (k - 1) * w, INDUSTRY[col]):
            ax.text(xi, v + 0.008, f"{v:.0%}", ha="center", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(INDUSTRY["环节"])
    ax.set_ylim(0, 0.75)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("瓶颈环节转化率对比")
    ax.legend(fontsize=8.5, loc="upper left")

    # 右：总体转化率 vs 行业
    ax = axes[1]
    overall = [
        ("本项目\n(现状)", funnel["累计转化率"].iloc[-1], COLORS[1]),
        ("改进后\n(实际)", imp["累计转化率"].iloc[-1], COLORS[2]),
        ("行业均值", 0.05, COLORS[0]),
        ("行业最高", 0.15, COLORS[4]),
    ]
    labels = [o[0] for o in overall]
    vals = [o[1] for o in overall]
    bars = ax.bar(labels, vals, color=[o[2] for o in overall], width=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.003, f"{v:.2%}",
                ha="center", fontsize=9.5)
    ax.set_ylim(0, 0.18)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("总体（曝光→购买）转化率对比")

    fig.suptitle("广告漏斗与行业基准对比", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return save_fig(fig, "lab02_benchmark")


def plot_scenarios(sc: pd.DataFrame, actual: float) -> Path:
    rows = sc[["情景", "总体转化率"]].copy()
    rows.loc[len(rows)] = {"情景": "改进实施后\n（实际）", "总体转化率": actual}
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    colors = [COLORS[5], COLORS[0], COLORS[2], COLORS[1], COLORS[3]]
    bars = ax.bar(rows["情景"], rows["总体转化率"], color=colors, width=0.58)
    for b, v in zip(bars, rows["总体转化率"]):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.0008, f"{v:.2%}",
                ha="center", fontsize=9.5)
    ax.axhline(0.05, color=COLORS[0], ls="--", lw=1, label="行业均值 5%")
    ax.set_ylim(0, 0.07)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1%}"))
    ax.set_title("各优化情景下的总体转化率（教材测算 vs 实际落地）")
    ax.tick_params(axis="x", labelsize=8.5)
    ax.legend(fontsize=8.5)
    return save_fig(fig, "lab02_scenarios")


def main() -> None:
    setup_plot()

    funnel = build_funnel()
    imp = build_improved_funnel()
    scenarios = scenario_table()

    base_overall = funnel["累计转化率"].iloc[-1]
    gap = base_overall - 0.05
    jump_only = scenarios.loc[1, "总体转化率"]
    touch_only = scenarios.loc[2, "总体转化率"]
    both = scenarios.loc[3, "总体转化率"]
    actual = imp["累计转化率"].iloc[-1]

    print("=" * 60)
    print("lab02 广告与销售漏斗分析（按教材口径构造）")
    print("=" * 60)
    print(f"广告触达人数：{BASELINE_TOUCH:,}")
    for _, r in funnel.iloc[1:].iterrows():
        print(
            f"  {r['转化率名称']:<8}{r['环节转化率']:.0%}  "
            f"→ {r['环节']:<12}{r['人数']:,}（累计 {r['累计转化率']:.2%}）"
        )
    print("-" * 60)
    print(f"总体转化率：{base_overall:.2%}，行业均值 5%，差距 {gap * 100:.2f} 个百分点")
    print(f"仅跳转提升至 50%：{jump_only:.2%}（+{jump_only - base_overall:.2%}，教材约 +1.7pp）")
    print(f"仅触达提升至 20%：{touch_only:.2%}（+{touch_only - base_overall:.2%}，教材约 +1pp）")
    print(f"双提升（教材测算）：{both:.2%}（与行业均值持平）")
    print(f"改进实施后：{actual:.2%}（与教材 5.2% 一致）")
    print("-" * 60)
    print(
        "结论：瓶颈在「触达」（10% vs 行业 20%）与「跳转」（20% vs 行业 50%）。\n"
        "      跳转环节提升带来的收益更大；两项同时优化可达 5.4%。\n"
        "      落地手段：广告页「了解详情」按钮改为滑动悬浮；参考相似产品高转化标题文案。"
    )

    save_table(funnel.drop(columns=["转化率名称"]), "lab02_funnel")
    save_table(imp.drop(columns=["转化率名称"]), "lab02_improved_funnel")
    save_table(INDUSTRY, "lab02_benchmark")
    save_table(scenarios, "lab02_scenarios")

    plot_funnel(funnel)
    plot_benchmark(funnel, imp)
    plot_scenarios(scenarios, actual)

    print("\n产物已写入 output/figures 与 output/tables（lab02_*）。")


if __name__ == "__main__":
    main()
