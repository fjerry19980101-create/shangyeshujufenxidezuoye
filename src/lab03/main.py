"""lab03 收入趋势与同比归因。

教材出处：第 3 章 3.4.1 企业收入趋势分析示例（PDF p105-109，Excel 透视表）

业务问题
--------
线上超市 2017-2020 年的收入增长是否健康？如果不理想，问题出在哪一年、
哪个月、哪个省份？

分析路径（与教材一致，逐层下钻）
--------
年度趋势 → 2020 年月度趋势 → 2020 年各月同比 → 2020 年 11 月分省同比
→ 聚焦四川省全年各月同比 → 回到业务场景归因（本地竞品冲击）。

数据说明：教材未附数据，本实验按书中结论反向构造面板数据（见 data_prep.py）。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import pandas as pd

from common.config import COLORS, save_fig, save_table, setup_plot
from lab03.data_prep import (
    annual_revenue,
    build_panel,
    province_yoy,
    yoy_by_month,
)


def pct(v: float) -> str:
    return f"{v:+.1%}"


def plot_annual(annual: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.3))
    bars = ax.bar(annual["年份"].astype(str), annual["收入"], color=COLORS[0], width=0.55)
    for b, v in zip(bars, annual["收入"]):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.01, f"{v:,.0f}",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("收入（万元）")
    ax.set_title("年度销售收入趋势（2017-2020）")

    ax2 = ax.twinx()
    ax2.plot(annual["年份"].astype(str), annual["同比"], color=COLORS[1],
             marker="o", lw=2)
    for x, v in zip(annual["年份"].astype(str), annual["同比"]):
        if pd.notna(v):
            ax2.annotate(f"{v:+.1%}", (x, v), textcoords="offset points",
                         xytext=(0, -16), ha="center", va="top",
                         color=COLORS[1], fontsize=9)
    ax2.set_ylim(0, 0.18)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax2.set_ylabel("同比增速")
    ax2.grid(False)
    return save_fig(fig, "lab03_annual")


def plot_monthly(panel: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.4))
    for year, color, label in ((2019, COLORS[5], "2019 年"), (2020, COLORS[1], "2020 年")):
        s = panel[panel["年份"] == year].groupby("月份")["收入"].sum()
        ax.plot(s.index, s.values, marker="o", color=color, lw=2, label=label)
    ax.set_xticks(range(1, 13))
    ax.set_xlabel("月份")
    ax.set_ylabel("收入（万元）")
    ax.set_title("2020 年月度销售收入 vs 2019（下半年增速明显放缓）")
    ax.legend()
    return save_fig(fig, "lab03_monthly_2020")


def plot_monthly_yoy(monthly: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    colors = [COLORS[3] if v < 0 else COLORS[0] for v in monthly["同比"]]
    bars = ax.bar(monthly["月份"], monthly["同比"], color=colors, width=0.62)
    for b, v in zip(bars, monthly["同比"]):
        ax.text(b.get_x() + b.get_width() / 2,
                v + (0.002 if v >= 0 else -0.002), f"{v:+.1%}",
                ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5)
    ax.axhline(0, color="#333333", lw=0.8)
    ax.set_xticks(range(1, 13))
    ax.set_xlabel("2020 年月份")
    ax.set_ylabel("同比增速")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_ylim(-0.04, 0.12)
    ax.set_title("2020 年各月收入同比：11 月转负")
    ax.annotate("11 月负增长", xy=(11, monthly.loc[10, "同比"]),
                xytext=(9.2, -0.032), fontsize=9, color=COLORS[3],
                arrowprops=dict(arrowstyle="->", color=COLORS[3], lw=1))
    return save_fig(fig, "lab03_monthly_yoy")


def plot_province(prov: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(9, 8.2))
    colors = [COLORS[3] if v < 0 else COLORS[0] for v in prov["同比"]]
    bars = ax.barh(prov["省份"], prov["同比"], color=colors, height=0.65)
    for b, v in zip(bars, prov["同比"]):
        ax.text(v + (0.003 if v >= 0 else -0.003), b.get_y() + b.get_height() / 2,
                f"{v:+.1%}", va="center",
                ha="left" if v >= 0 else "right", fontsize=7.8)
    ax.axvline(0, color="#333333", lw=0.8)
    ax.set_xlim(-0.20, 0.06)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("2020 年 11 月各省份收入同比（负增长省份标红）")
    ax.set_xlabel("同比增速")
    ax.set_ylabel("省份")
    ax.invert_yaxis()
    return save_fig(fig, "lab03_nov_province")


def plot_sichuan(sichuan: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.4))
    key_months = {7, 9, 11}
    colors = [COLORS[4] if m in key_months else COLORS[3] for m in sichuan["月份"]]
    bars = ax.bar(sichuan["月份"], sichuan["同比"], color=colors, width=0.62)
    for b, v in zip(bars, sichuan["同比"]):
        ax.text(b.get_x() + b.get_width() / 2, v - 0.002, f"{v:.1%}",
                ha="center", va="top", fontsize=8.5)
    ax.axhline(0, color="#333333", lw=0.8)
    ax.set_xticks(range(1, 13))
    ax.set_xlabel("2020 年月份")
    ax.set_ylabel("同比增速")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_ylim(-0.16, 0.01)
    ax.set_title("四川省 2020 年各月同比：全年负增长，7/9/11 月最差（深色）")
    return save_fig(fig, "lab03_sichuan")


def main() -> None:
    setup_plot()

    panel = build_panel()
    annual = annual_revenue(panel)
    monthly = yoy_by_month(panel, 2020)
    prov = province_yoy(panel, 2020, 11)
    sichuan = yoy_by_month(panel, 2020, province="四川")

    h1 = monthly.loc[monthly["月份"] <= 6, "同比"].mean()
    h2 = monthly.loc[monthly["月份"] >= 7, "同比"].mean()
    nov_yoy = monthly.loc[monthly["月份"] == 11, "同比"].iloc[0]
    neg_count = int((prov["同比"] < 0).sum())

    print("=" * 62)
    print("lab03 收入趋势与同比归因（模拟还原）")
    print("=" * 62)
    for _, r in annual.iterrows():
        print(f"{int(r['年份'])} 年收入：{r['收入']:>12,.0f} 万元  同比 {pct(r['同比']) if pd.notna(r['同比']) else '—'}")
    print("-" * 62)
    print(f"2020 上半年月均同比 {h1:+.2%}，下半年月均同比 {h2:+.2%}，增长明显放缓")
    print(f"2020 年 11 月全国同比 {nov_yoy:+.2%}，出现负增长")
    print(f"11 月共 {neg_count} 个省份同比为负，最差为 {prov.iloc[0]['省份']}（{prov.iloc[0]['同比']:.1%}）")
    print("-" * 62)
    print(f"四川省 2020 年 12 个月同比全部为负，最差月份：")
    for m in (7, 9, 11):
        v = sichuan.loc[sichuan["月份"] == m, "同比"].iloc[0]
        print(f"  {m} 月：{v:.1%}")
    print("-" * 62)
    print(
        "结论（与教材一致）：\n"
        "  1) 年度看 2017-2020 持续增长，问题藏在月度维度；\n"
        "  2) 2020 下半年增长放缓，9-11 月不理想，11 月转负；\n"
        "  3) 11 月多省份负增长，四川全年负增长且 7/9/11 月最差；\n"
        "  4) 业务归因：四川出现本地竞品，低价+大量本地网点+线上配送，\n"
        "     打破原有竞争格局；建议评估竞品可持续性，从渠道布局与\n"
        "     供应链/多层次定价两方面制定应对方案，并持续跟踪复盘。"
    )

    save_table(annual, "lab03_annual")
    save_table(monthly, "lab03_monthly_2020")
    save_table(prov, "lab03_nov_province")
    save_table(sichuan, "lab03_sichuan_2020")

    plot_annual(annual)
    plot_monthly(panel)
    plot_monthly_yoy(monthly)
    plot_province(prov)
    plot_sichuan(sichuan)

    print("\n产物已写入 output/figures 与 output/tables（lab03_*）。")


if __name__ == "__main__":
    main()
