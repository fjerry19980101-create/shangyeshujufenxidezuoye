"""lab05 用户细分与营销评估（电商平台个性化营销）。

教材出处：第 3 章 3.5.2 电商平台的客户个性化营销示例（PDF p118-122，Excel 实现）

业务问题
--------
某多品类电商平台下月要做大型促销，出于流程与预算考虑，只面向"男性或女性"
其中一类人群，缺乏具体营销人群与促销方向。

分析路径（教材三步法）
--------
1. 明确分析重点：按性别分布找到规模更大的人群（女性 60%）；
2. 因果（画像）分析：女性年龄段 → 50 岁以上占 36%；
   50 岁以上女性品类 → 服饰、护肤品为主；再看支付方式 → 设计差异化满减；
3. 验证想法：A/B 测试（测试组=50+女性+服饰/护肤品，对照组=50+女性+其他品类，
   两组等规模），活动后用六项指标评估并复盘。

数据说明：教材未附数据，本实验按书中比例反向构造（见 data_prep.py）。
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
from lab05.data_prep import (
    TARGET_CATEGORIES,
    ab_metrics,
    build_ab_test,
    build_orders,
)


def profile_tables(orders: pd.DataFrame) -> dict[str, pd.DataFrame]:
    female = orders[orders["性别"] == "女"]
    fifty = female[female["年龄段"] == "50岁以上"]
    return {
        "gender": orders["性别"].value_counts().rename_axis("性别").reset_index(name="客户数"),
        "age": female["年龄段"].value_counts().reindex(["18-25岁", "26-35岁", "36-49岁", "50岁以上"])
        .reset_index(name="客户数"),
        "category": fifty["消费品类"].value_counts().rename_axis("消费品类").reset_index(name="客户数"),
        "payment": fifty["支付方式"].value_counts().rename_axis("支付方式").reset_index(name="客户数"),
    }


def plot_profile(tables: dict[str, pd.DataFrame]) -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))

    def bar(ax, df, xcol, ycol, title, highlight=None, rotate=0):
        colors = [COLORS[1] if (highlight and v == highlight) else COLORS[0] for v in df[xcol]]
        bars = ax.bar(df[xcol], df[ycol], color=colors, width=0.58)
        total = df[ycol].sum()
        for b, v in zip(bars, df[ycol]):
            ax.text(b.get_x() + b.get_width() / 2, v + total * 0.01,
                    f"{v / total:.0%}", ha="center", fontsize=9)
        ax.set_title(title)
        ax.set_ylabel("客户数")
        ax.set_ylim(0, df[ycol].max() * 1.18)
        ax.tick_params(axis="x", rotation=rotate)

    bar(axes[0, 0], tables["gender"], "性别", "客户数", "购买客户性别分布（女性 60%）", highlight="女")
    bar(axes[0, 1], tables["age"], "年龄段", "客户数", "女性客户年龄段分布（50+ 占 36%）", highlight="50岁以上")

    cat = tables["category"].copy()
    cat["占比"] = cat["客户数"] / cat["客户数"].sum()
    cat = cat.sort_values("客户数", ascending=False)
    bar(axes[1, 0], cat, "消费品类", "客户数", "50 岁以上女性消费品类分布")
    axes[1, 0].tick_params(axis="x", rotation=20)

    bar(axes[1, 1], tables["payment"], "支付方式", "客户数", "50 岁以上女性支付方式分布", rotate=15)

    fig.suptitle("客户画像：逐步聚焦到「50 岁以上女性 + 服饰/护肤品」", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return save_fig(fig, "lab05_profile")


def plot_ab(metrics: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5), gridspec_kw={"width_ratios": [1, 1.35]})
    test, ctrl = metrics.iloc[0], metrics.iloc[1]

    ax = axes[0]
    x = np.arange(2)
    w = 0.35
    ax.bar(x - w / 2, [test["参与率"], test["转化率"]], width=w, color=COLORS[1], label="测试组")
    ax.bar(x + w / 2, [ctrl["参与率"], ctrl["转化率"]], width=w, color=COLORS[5], label="对照组")
    for i, (a, b) in enumerate(zip([test["参与率"], test["转化率"]], [ctrl["参与率"], ctrl["转化率"]])):
        ax.text(i - w / 2, a + 0.008, f"{a:.1%}", ha="center", fontsize=9)
        ax.text(i + w / 2, b + 0.008, f"{b:.1%}", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(["参与率", "转化率"])
    ax.set_ylim(0, 0.45)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("参与率与转化率对比")
    ax.legend(fontsize=8.5)

    ax = axes[1]
    fields = ["活动参与人数", "转化人数", "新增用户数", "新增活跃用户数"]
    x = np.arange(len(fields))
    ax.bar(x - w / 2, [test[f] for f in fields], width=w, color=COLORS[1], label="测试组")
    ax.bar(x + w / 2, [ctrl[f] for f in fields], width=w, color=COLORS[5], label="对照组")
    for i, f in enumerate(fields):
        ax.text(i - w / 2, test[f] + 5, str(test[f]), ha="center", fontsize=9)
        ax.text(i + w / 2, ctrl[f] + 5, str(ctrl[f]), ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(fields, fontsize=9)
    ax.set_ylim(0, 320)
    ax.set_title("活动结果指标（人数）")
    ax.legend(fontsize=8.5)

    fig.suptitle("A/B 测试：测试组全面优于对照组", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return save_fig(fig, "lab05_ab_test")


def main() -> None:
    setup_plot()

    orders = build_orders()
    tables = profile_tables(orders)
    ab = build_ab_test(orders)
    metrics = ab_metrics(ab)

    total = len(orders)
    female_n = int((orders["性别"] == "女").sum())
    female = orders[orders["性别"] == "女"]
    fifty = female[female["年龄段"] == "50岁以上"]
    fifty_share = len(fifty) / len(female)
    target_n = int(fifty["消费品类"].isin(TARGET_CATEGORIES).sum())

    test, ctrl = metrics.iloc[0], metrics.iloc[1]

    print("=" * 66)
    print("lab05 电商平台个性化营销：用户细分 + A/B 测试（模拟还原）")
    print("=" * 66)
    print(f"购买客户 {total:,} 人：女性 {female_n:,}（{female_n / total:.0%}）、男性 {total - female_n:,}（{(total - female_n) / total:.0%}）")
    print(f"女性 {len(female):,} 人中 50 岁以上 {len(fifty):,} 人（{fifty_share:.0%}）")
    print(f"50 岁以上女性中，购买服饰/护肤品 {target_n:,} 人（{target_n / len(fifty):.0%}）")
    print("-" * 66)
    print("50 岁以上女性支付方式：")
    for _, r in tables["payment"].iterrows():
        print(f"  {r['支付方式']}：{r['客户数']:,} 人（{r['客户数'] / len(fifty):.0%}）")
    print("-" * 66)
    print("A/B 测试结果（每组 777 人）：")
    for _, r in metrics.iterrows():
        print(
            f"  {r['分组']}：参与 {r['活动参与人数']}（{r['参与率']:.1%}），"
            f"转化 {r['转化人数']}（{r['转化率']:.1%}），"
            f"新增 {r['新增用户数']}，新增活跃 {r['新增活跃用户数']}（{r['新增活跃率']:.1%}）"
        )
    print("-" * 66)
    print(
        "结论（与教材一致）：\n"
        "  1) 女性占比 60% → 促销面向女性人群；\n"
        "  2) 50+ 女性占 36%，品类集中服饰+护肤品 → 活动主题「50 岁优雅」，\n"
        "     选品西服 + 抗老面霜；\n"
        "  3) 支付方式差异明显 → 支付宝满 150 减 30、银行卡满 200 减 50、\n"
        "     微信满 300 享八折；\n"
        f"  4) A/B 测试：参与率 {test['参与率']:.1%} vs {ctrl['参与率']:.1%}，"
        f"转化率 {test['转化率']:.1%} vs {ctrl['转化率']:.1%}，\n"
        "     新增用户与新增活跃均显著领先，用户细分策略有效，可复制到下次活动。"
    )

    for name, df in tables.items():
        save_table(df, f"lab05_{name}")
    save_table(metrics, "lab05_ab_metrics")

    plot_profile(tables)
    plot_ab(metrics)

    print("\n产物已写入 output/figures 与 output/tables（lab05_*）。")


if __name__ == "__main__":
    main()
