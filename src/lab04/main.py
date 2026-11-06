"""lab04 财务费用杜邦拆解。

教材出处：第 3 章 3.4.2 财务费用趋势分析示例（PDF p110-115，Excel 实现）

业务问题
--------
零售连锁企业 2020 年 7 月总财务费用比 6 月高 5%，财务费用波动给盈利带来压力。
需要层层拆解，找到具体是哪一项费用上涨，并回到业务场景给出优化方案。

分析路径（杜邦式逐层拆解）
--------
总财务费用（6 月 vs 7 月）→ 三项期间费用（管理/销售/财务）→ 管理费用明细
→ 定位异常项（培训与发展、咨询费）→ 业务访谈区分长期/临时 → 制定优化方案。

数据说明：教材未附明细金额，本实验按书中比例反向构造（见 data_prep.py）。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import numpy as np

from common.config import COLORS, save_fig, save_table, setup_plot
from lab04.data_prep import (
    ANOMALY_THRESHOLD,
    BUSINESS_NATURE,
    MANAGEMENT_DETAIL,
    PERIOD_EXPENSES,
    add_growth,
)


def plot_total(period: pd.DataFrame) -> Path:
    june, july = period["6月"].sum(), period["7月"].sum()
    fig, ax = plt.subplots(figsize=(5.6, 4.4))
    bars = ax.bar(["6 月", "7 月"], [june, july], color=[COLORS[0], COLORS[1]], width=0.5)
    for b, v in zip(bars, [june, july]):
        ax.text(b.get_x() + b.get_width() / 2, v + 8000, f"{v:,.0f}",
                ha="center", fontsize=10)
    ax.set_ylim(june * 0.95, july * 1.06)
    ax.set_ylabel("总财务费用（元）")
    ax.set_title(f"总财务费用对比：7 月环比 {july / june - 1:+.1%}")
    return save_fig(fig, "lab04_total")


def plot_period(period: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1.25, 1]})

    ax = axes[0]
    x = np.arange(len(period))
    w = 0.34
    ax.bar(x - w / 2, period["6月"], width=w, color=COLORS[5], label="6 月")
    ax.bar(x + w / 2, period["7月"], width=w, color=COLORS[1], label="7 月")
    for i, (j6, j7) in enumerate(zip(period["6月"], period["7月"])):
        ax.text(i - w / 2, j6 + 6000, f"{j6 / 10000:.0f}万", ha="center", fontsize=8.5)
        ax.text(i + w / 2, j7 + 6000, f"{j7 / 10000:.1f}万", ha="center", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(period["费用项"])
    ax.set_ylim(0, 800_000)
    ax.set_ylabel("金额（元）")
    ax.set_title("三项期间费用 6 月 vs 7 月")
    ax.legend(fontsize=8.5)

    ax = axes[1]
    colors = [COLORS[3] if v > 0 else COLORS[2] for v in period["对总增量贡献"]]
    bars = ax.bar(period["费用项"], period["对总增量贡献"], color=colors, width=0.55)
    for b, v in zip(bars, period["对总增量贡献"]):
        ax.text(b.get_x() + b.get_width() / 2, v + (0.02 if v >= 0 else -0.02),
                f"{v:+.1%}", ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
    ax.axhline(0, color="#333333", lw=0.8)
    ax.set_ylim(-0.3, 1.25)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("各项对总费用增量的贡献度")

    fig.suptitle("管理费用是总费用增长的主要来源", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return save_fig(fig, "lab04_period")


def plot_management_detail(detail) -> Path:
    detail = detail.sort_values("环比增长率")
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    colors = []
    for _, r in detail.iterrows():
        if r["环比增长率"] > ANOMALY_THRESHOLD:
            colors.append(COLORS[1])
        else:
            colors.append(COLORS[0])
    bars = ax.barh(detail["明细项"], detail["环比增长率"], color=colors, height=0.6)
    for b, v in zip(bars, detail["环比增长率"]):
        ax.text(v + (0.01 if v >= 0 else -0.01), b.get_y() + b.get_height() / 2,
                f"{v:+.1%}", va="center",
                ha="left" if v >= 0 else "right", fontsize=9)
    ax.axvline(ANOMALY_THRESHOLD, color=COLORS[3], ls="--", lw=1.2,
               label=f"异常阈值 +{ANOMALY_THRESHOLD:.0%}")
    ax.axvline(0, color="#333333", lw=0.8)
    ax.set_xlim(-0.1, 1.05)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("管理费用明细项环比增长（超过 5% 标橙）")
    ax.set_xlabel("环比增长率")
    ax.legend(fontsize=8.5, loc="lower right")
    return save_fig(fig, "lab04_management_detail")


def plot_waterfall(period: pd.DataFrame) -> Path:
    june = period["6月"].sum()
    july = period["7月"].sum()
    labels = ["6 月总费用", "管理费用", "销售费用", "财务费用", "7 月总费用"]
    deltas = list(period["环比增量"])
    values = [june, *deltas, july]

    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    running = june
    for i, delta in enumerate(values):
        if i == 0:
            ax.bar(i, june, color=COLORS[0], width=0.6)
            ax.text(i, june + 8000, f"{june:,.0f}", ha="center", fontsize=9)
        elif i == len(values) - 1:
            ax.bar(i, july, color=COLORS[1], width=0.6)
            ax.text(i, july + 8000, f"{july:,.0f}", ha="center", fontsize=9)
        else:
            bottom = running if delta >= 0 else running + delta
            color = COLORS[3] if delta >= 0 else COLORS[2]
            ax.bar(i, abs(delta), bottom=bottom, color=color, width=0.6)
            ax.text(i, max(running, running + delta) + 8000,
                    f"{delta:+,.0f}", ha="center", fontsize=9)
            running += delta

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_ylim(1_480_000, 1_700_000)
    ax.set_ylabel("金额（元）")
    ax.set_title("总财务费用变化的瀑布图（6 月 → 7 月）")
    return save_fig(fig, "lab04_waterfall")


def main() -> None:
    setup_plot()

    period = add_growth(PERIOD_EXPENSES, "费用项")
    detail = add_growth(MANAGEMENT_DETAIL, "明细项")
    detail["是否异常"] = detail["环比增长率"] > ANOMALY_THRESHOLD

    june, july = period["6月"].sum(), period["7月"].sum()
    total_growth = july / june - 1

    print("=" * 64)
    print("lab04 财务费用杜邦拆解（模拟还原）")
    print("=" * 64)
    print(f"第一层：6 月总费用 {june:,} 元 → 7 月 {july:,} 元，环比 {total_growth:+.1%}")
    print("第二层：三项期间费用")
    for _, r in period.iterrows():
        print(
            f"  {r['费用项']}：{r['6月']:,} → {r['7月']:,}  "
            f"环比 {r['环比增长率']:+.1%}，贡献总增量 {r['对总增量贡献']:+.1%}"
        )
    print("第三层：管理费用明细（阈值 5%）")
    for _, r in detail.sort_values("环比增长率", ascending=False).iterrows():
        flag = "  ← 异常" if r["是否异常"] else ""
        print(f"  {r['明细项']}：环比 {r['环比增长率']:+.1%}{flag}")
    print("-" * 64)
    print("业务归因（教材访谈结论）：")
    for item, nature in BUSINESS_NATURE.items():
        print(f"  {item}：{nature}")
    print(
        "结论：管理费用的增长主要来自培训与发展和咨询费。\n"
        "      培训与发展是长期因素（持续 1~2 年），必须制定优化方案；\n"
        "      咨询费属于 7 月临时需求，后续优化时可不计入。\n"
        "      建议：优化差旅政策、改用在线培训、与培训机构谈批量折扣，\n"
        "      并在方案执行 3~6 个月后从费用、培训满意度、业务绩效三方面复盘。"
    )

    save_table(period, "lab04_period_expenses")
    save_table(detail, "lab04_management_detail")

    plot_total(period)
    plot_period(period)
    plot_management_detail(detail)
    plot_waterfall(period)

    print("\n产物已写入 output/figures 与 output/tables（lab04_*）。")


if __name__ == "__main__":
    main()
