"""lab07 指标归因：价值树拆解与贡献度计算。

教材出处：第 5 章 5.3.3 归因分析（PDF p175-186，Excel 实现）

业务问题
--------
某产品营收从 11000 下降到 9975，需要判断订单数与单价各自的影响程度，
为后续运营动作提供量化依据。

教材给出四种指标归因算法，本实验全部用 Python 复现并与书中数值对拍：

1. 加/减法（变化量）：ΔX = Δx1 + … + Δxn，贡献度 = Δxn / ΔX；
2. 加/减法（变化率）：变化率指标需在统一分母下拆解，贡献度 = Δxn / X0；
3. 替换法：被考查因素取当期值、其余取上期值，贡献 = 假设组合值 - 上期总值；
4. LMDI：取对数把乘法转加法，贡献占比 = ln(x1/x0) / ln(Y1/Y0)；
5. 双因素法：比率指标拆为波动贡献 A + 结构贡献 B。

数据说明：教材已给出全部数值，本实验直接录入，不做模拟（见 data_prep.py）。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import numpy as np

from common.config import COLORS, save_fig, save_table, setup_plot
from lab07.data_prep import (
    REVENUE_CASE,
    additive_decompose,
    replacement_method,
    two_factor_method,
)


def plot_revenue_waterfall(methods) -> Path:
    y0 = REVENUE_CASE["订单数"][0] * REVENUE_CASE["单价"][0]
    y1 = REVENUE_CASE["订单数"][1] * REVENUE_CASE["单价"][1]
    c_orders = methods.loc[0, "替换法贡献"]
    c_price = methods.loc[1, "替换法贡献"]
    interaction = methods.loc[3, "替换法贡献"]

    labels = ["上期营收", "订单数", "单价", "交互项", "本期营收"]
    values = [y0, c_orders, c_price, interaction, y1]

    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    running = y0
    for i, delta in enumerate(values):
        if i == 0:
            ax.bar(i, y0, color=COLORS[0], width=0.6)
            ax.text(i, y0 + 25, f"{y0:,}", ha="center", fontsize=9)
        elif i == len(values) - 1:
            ax.bar(i, y1, color=COLORS[1], width=0.6)
            ax.text(i, y1 + 25, f"{y1:,}", ha="center", fontsize=9)
        else:
            bottom = running if delta >= 0 else running + delta
            color = COLORS[3] if delta >= 0 else COLORS[2]
            ax.bar(i, abs(delta), bottom=bottom, color=color, width=0.6)
            ax.text(i, max(running, running + delta) + 30,
                    f"{delta:+,}", ha="center", fontsize=9)
            running += delta

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_ylim(9800, 11250)
    ax.set_ylabel("营收（元）")
    ax.set_title("营收变化瀑布图：订单数 -500、单价 -550，交互项 +25")
    return save_fig(fig, "lab07_revenue_waterfall")


def plot_method_compare(methods) -> Path:
    df = methods.iloc[:2]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))

    ax = axes[0]
    x = np.arange(len(df))
    w = 0.35
    ax.bar(x - w / 2, df["替换法贡献"], width=w, color=COLORS[1], label="替换法")
    ax.bar(x + w / 2, df["LMDI贡献"], width=w, color=COLORS[0], label="LMDI")
    for i in range(len(df)):
        ax.text(i - w / 2, df["替换法贡献"].iloc[i] - 45, f"{df['替换法贡献'].iloc[i]:.0f}",
                ha="center", va="top", fontsize=9)
        ax.text(i + w / 2, df["LMDI贡献"].iloc[i] - 45, f"{df['LMDI贡献'].iloc[i]:.1f}",
                ha="center", va="top", fontsize=9)
    ax.axhline(0, color="#333333", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(df["因素"])
    ax.set_ylim(-620, 60)
    ax.set_ylabel("贡献金额（元）")
    ax.set_title("两种乘法拆解的贡献金额")
    ax.legend(fontsize=8.5, loc="upper right")

    ax = axes[1]
    ax.bar(x - w / 2, df["替换法占比"], width=w, color=COLORS[1], label="替换法")
    ax.bar(x + w / 2, df["LMDI占比"], width=w, color=COLORS[0], label="LMDI")
    for i in range(len(df)):
        ax.text(i - w / 2, df["替换法占比"].iloc[i] + 0.008,
                f"{df['替换法占比'].iloc[i]:.1%}", ha="center", fontsize=9)
        ax.text(i + w / 2, df["LMDI占比"].iloc[i] + 0.008,
                f"{df['LMDI占比'].iloc[i]:.2%}", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(df["因素"])
    ax.set_ylim(0, 0.65)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("贡献占比：替换法合计 102.4%，LMDI 恰好 100%")
    ax.legend(fontsize=8.5)

    fig.suptitle("替换法 vs LMDI：结果方向一致，LMDI 可精确闭合", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return save_fig(fig, "lab07_method_compare")


def plot_additive(df) -> Path:
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    colors = [COLORS[5] if v == 0 else COLORS[3] for v in df["变化率贡献度"]]
    bars = ax.bar(df["指标"], df["变化率贡献度"], color=colors, width=0.55)
    for b, v in zip(bars, df["变化率贡献度"]):
        ax.text(b.get_x() + b.get_width() / 2, v - 0.004,
                f"{v:+.2%}", ha="center", va="top", fontsize=9.5)
    ax.axhline(df["变化率贡献度"].sum(), color=COLORS[0], ls="--", lw=1.2,
               label=f"合计 {df['变化率贡献度'].sum():.2%}")
    ax.axhline(0, color="#333333", lw=0.8)
    ax.set_ylim(-0.18, 0.03)
    ax.set_yticks([-0.18, -0.15, -0.12, -0.09, -0.06, -0.03, 0, 0.03])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("变化率加法拆解：各指标对 -16.7% 的贡献")
    ax.legend(fontsize=9)
    return save_fig(fig, "lab07_additive")


def plot_two_factor(df) -> Path:
    prods = df[df["产品"] != "总体"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(prods))
    ax.bar(x, prods["波动贡献A"], color=COLORS[0], width=0.48, label="波动贡献 A")
    ax.bar(x, prods["结构贡献B"], bottom=prods["波动贡献A"],
           color=COLORS[1], width=0.48, label="结构贡献 B")
    for i, row in prods.iterrows():
        ax.text(i - 0.02, -0.004, f"A {row['波动贡献A']:.1%}", ha="center", va="top",
                fontsize=8.5, color="#EEEEEE")
        ax.text(i + 0.27, row["波动贡献A"] + row["结构贡献B"] / 2,
                f"B {row['结构贡献B']:+.1%}", ha="left", va="center", fontsize=8.5)
        ax.text(i, row["整体贡献C"] - 0.018, f"C {row['整体贡献C']:.1%}",
                ha="center", va="top", fontsize=10, fontweight="bold", color=COLORS[3])
    ax.axhline(0, color="#333333", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(prods["产品"])
    ax.set_ylim(-0.20, 0.03)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("双因素法：整体转化率 50% → 27%，两产品贡献 C 合计 -23.3%")
    ax.legend(fontsize=8.5, loc="lower right")
    return save_fig(fig, "lab07_two_factor")


def main() -> None:
    setup_plot()

    add = additive_decompose()
    methods = replacement_method()
    two = two_factor_method()

    y0 = REVENUE_CASE["订单数"][0] * REVENUE_CASE["单价"][0]
    y1 = REVENUE_CASE["订单数"][1] * REVENUE_CASE["单价"][1]
    delta = y1 - y0
    orders0, orders1 = REVENUE_CASE["订单数"]
    price0, price1 = REVENUE_CASE["单价"]

    print("=" * 68)
    print("lab07 指标归因：价值树拆解与贡献度（教材数值，非模拟）")
    print("=" * 68)
    print("【1】加法拆解（变化量）")
    print(f"上期合计 {add['上期值'].sum():,} → 本期 {add['本期值'].sum():,}，增量 {add['增量'].sum():+,}")
    for _, r in add.iterrows():
        print(f"  {r['指标']}：增量 {r['增量']:+,}，贡献度 {r['变化量贡献度']:+.1%}")

    print("\n【2】加法拆解（变化率）")
    for _, r in add.iterrows():
        print(f"  {r['指标']}：变化率贡献 {r['变化率贡献度']:+.2%}")
    print(f"  合计：{add['变化率贡献度'].sum():+.2%}（教材 -16.7%）")

    print("\n【3】乘法拆解：营收 = 订单数 × 单价")
    print(f"上期 {orders0} × {price0} = {y0:,}，本期 {orders1} × {price1} = {y1:,}，增量 {delta:+,}")
    print(f"  替换法：订单数 {methods.loc[0, '替换法贡献']:+,}，单价 {methods.loc[1, '替换法贡献']:+,}，"
          f"合计 {methods.loc[2, '替换法贡献']:+,}（与实际增量差 {methods.loc[3, '替换法贡献']:+,}，为交互项）")
    print(f"  LMDI：订单数 {methods.loc[0, 'LMDI贡献']:+.1f}（{methods.loc[0, 'LMDI占比']:.2%}），"
          f"单价 {methods.loc[1, 'LMDI贡献']:+.1f}（{methods.loc[1, 'LMDI占比']:.2%}），合计 {delta:+,}")

    print("\n【4】双因素法：整体下单转化率")
    for _, r in two.iterrows():
        if r["产品"] == "总体":
            print(f"  {r['产品']}：{r['上期转化率']:.0%} → {r['本期转化率']:.0%}")
        else:
            print(f"  {r['产品']}：A {r['波动贡献A']:+.1%} + B {r['结构贡献B']:+.1%} "
                  f"= C {r['整体贡献C']:+.1%}（教材 -15.0% / -8.3%）")
    print("-" * 68)
    print(
        "结论（与教材一致）：\n"
        "  1) 营收下降 1025 元（-9.32%），订单数与单价都有影响，单价略大；\n"
        "  2) 替换法结果 -500 / -550 直观但合计 -1050，与实际差 25（交互项），\n"
        "     只能作为影响程度参考；LMDI 按 47.56% / 52.44% 精确闭合；\n"
        "  3) 双因素法把转化率下降拆成波动与结构两部分：产品 1 贡献 -15%，\n"
        "     产品 2 贡献 -8.3%，产品 1 是主因；\n"
        "  4) 归因结论需回到业务场景：订单数下降看流量/渠道，单价下降看折扣/\n"
        "     商品结构，再结合二八法则聚焦核心因素制定方案。"
    )

    save_table(add, "lab07_additive")
    save_table(methods, "lab07_revenue_methods")
    save_table(two, "lab07_two_factor")

    plot_revenue_waterfall(methods)
    plot_method_compare(methods)
    plot_additive(add)
    plot_two_factor(two)

    print("\n产物已写入 output/figures 与 output/tables（lab07_*）。")


if __name__ == "__main__":
    main()
