"""lab01 同期群留存分析。

教材出处：第 2 章 2.1.1 分类分析（PDF p43-61，Excel 实现）

业务问题
--------
内容产品在 3 月 8 日做了"免费注册"拉新活动，新增用户环比 +32.5%。
需要回答：这波新用户的质量如何？留存是否被拉低？哪个群组值得继续投放？

分析路径（与教材口径一致）
--------
1. 按注册日划分同期群（cohort）；
2. 计算各群组在注册后第 1/3/5/7 天的留存率；
3. 横向比较群组（活动群组 vs 常规群组）；
4. 纵向观察留存衰减，判断拉新质量。

数据说明：教材未附源数据，本实验按书中结论反向构造模拟数据（见 data_prep.py）。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from common.config import COLORS, save_fig, save_table, setup_plot
from lab01.data_prep import (
    ACTIVITY_DATE,
    BASE_NEW_USERS,
    RETENTION_DAYS,
    build_cohort_users,
    cohort_retention,
    cohort_size,
)


def summarize(users: pd.DataFrame) -> pd.DataFrame:
    """汇总活动群组与常规群组的留存对比。"""
    is_activity = users["register_date"] == ACTIVITY_DATE
    rows = []
    for d in RETENTION_DAYS:
        col = f"retained_d{d}"
        act = users.loc[is_activity, col].mean()
        normal = users.loc[~is_activity, col].mean()
        overall = users[col].mean()
        rows.append(
            {
                "观测日": f"D{d}",
                "活动群组留存率": act,
                "其他群组留存率": normal,
                "全体留存率": overall,
                "差距(活动-其他)": act - normal,
            }
        )
    return pd.DataFrame(rows)


def plot_cohort_size(size: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(11, 4.2))
    colors = [
        COLORS[1] if d == ACTIVITY_DATE else COLORS[0] for d in size["register_date"]
    ]
    ax.bar(size["register_date"], size["new_users"], color=colors, width=0.8)
    ax.axhline(size["new_users"].median(), color=COLORS[5], ls="--", lw=1,
               label=f"日常中位数 {size['new_users'].median():.0f}")
    ax.set_title("每日新增注册用户数（3 月 8 日活动日标橙）")
    ax.set_ylabel("新增用户数")
    ax.set_xlabel("注册日期")
    ax.legend(loc="upper left")
    fig.autofmt_xdate()
    return save_fig(fig, "lab01_cohort_size")


def plot_heatmap(ret: pd.DataFrame) -> Path:
    """3 月注册群组的留存矩阵热力图。"""
    march = ret.loc["2024-03-01":]
    fig, ax = plt.subplots(figsize=(7.5, 9))
    sns.heatmap(
        march,
        annot=True,
        fmt=".0%",
        cmap="Blues",
        vmin=0,
        vmax=0.5,
        linewidths=0.4,
        cbar_kws={"label": "留存率"},
        ax=ax,
    )
    ax.set_title("3 月各注册同期群留存率矩阵")
    ax.set_xlabel("注册后观测日")
    ax.set_ylabel("注册日期")
    ax.set_yticklabels([d.strftime("%m-%d") for d in march.index], rotation=0)
    return save_fig(fig, "lab01_retention_heatmap")


def plot_curve(summary: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    x = RETENTION_DAYS
    ax.plot(x, summary["活动群组留存率"], marker="o", lw=2, color=COLORS[1],
            label="3-08 活动群组")
    ax.plot(x, summary["其他群组留存率"], marker="s", lw=2, color=COLORS[0],
            label="其他群组（均值）")
    for _, r in summary.iterrows():
        ax.annotate(f"{r['活动群组留存率']:.0%}",
                    (int(r["观测日"][1:]), r["活动群组留存率"]),
                    textcoords="offset points", xytext=(0, 8),
                    ha="center", color=COLORS[1], fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"D{d}" for d in x])
    ax.set_ylim(0, 0.55)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("活动群组 vs 其他群组的留存衰减曲线")
    ax.set_xlabel("注册后第 N 天")
    ax.set_ylabel("留存率")
    ax.legend()
    return save_fig(fig, "lab01_retention_curve")


def main() -> None:
    setup_plot()

    users = build_cohort_users()
    size = cohort_size(users)
    ret = cohort_retention(users)
    summary = summarize(users)

    # 活动日新增相对基线（800 人/日）的增幅
    act_new = int(size.loc[size["register_date"] == ACTIVITY_DATE, "new_users"].iloc[0])
    lift = act_new / BASE_NEW_USERS - 1

    d1_act = summary.loc[0, "活动群组留存率"]
    d1_normal = summary.loc[0, "其他群组留存率"]
    d1_all = summary.loc[0, "全体留存率"]

    print("=" * 58)
    print("lab01 同期群留存分析（模拟还原）")
    print("=" * 58)
    print(f"注册日期范围：{size['register_date'].min():%Y-%m-%d} ~ {size['register_date'].max():%Y-%m-%d}")
    print(f"注册用户总数：{len(users):,}")
    print(f"活动日新增：{act_new:,}（基线 {BASE_NEW_USERS} 人/日，增幅 {lift:+.1%}）")
    print("-" * 58)
    for _, r in summary.iterrows():
        print(
            f"{r['观测日']}：活动群组 {r['活动群组留存率']:.1%} | "
            f"其他群组 {r['其他群组留存率']:.1%} | 全体 {r['全体留存率']:.1%}"
        )
    print("-" * 58)
    print(
        f"结论：活动带来 {lift:+.1%} 新增，但次日留存仅 {d1_act:.1%}，"
        f"低于常规群组 {d1_normal:.1%}（差 {d1_act - d1_normal:+.1%}），"
        "拉新质量偏低，需要优化新手引导与首日激活。"
    )
    print(f"全体次日留存均值：{d1_all:.1%}（与教材 44% 口径一致）")

    save_table(size, "lab01_cohort_size")
    save_table(ret.reset_index(), "lab01_cohort_retention")
    save_table(summary, "lab01_summary")

    plot_cohort_size(size)
    plot_heatmap(ret)
    plot_curve(summary)

    print("\n产物已写入 output/figures 与 output/tables（lab01_*）。")


if __name__ == "__main__":
    main()
