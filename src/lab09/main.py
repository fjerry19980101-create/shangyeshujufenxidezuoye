"""lab09 信用卡用户画像（SQL + Excel → pandas + matplotlib）。

教材出处：第 9 章 9.4 信用卡用户画像（PDF p281-294）
- 9.4.1-9.4.3：写 3 段 SQL（var1/var2/var3）并从 KDD99 取数生成 Creditcard 宽表；
- 9.4.4：用 Excel 画 5 张画像图，按卡类型描述持卡人特征。

业务问题
--------
不同类型信用卡（普通卡/金卡/青年卡）的持卡人在基本信息、交易行为、财务水平上
有何差异？运营可据此做差异化产品推荐与精准营销。

Python 迁移
--------
- 用 pandas 复现三段取数（三表连接、不等值连接、365 天窗口聚合）；
- 用 matplotlib/seaborn 复现 5 张画像图；
- 数据说明：公开站点不可达，按书中结构与结论反向构造 900 张卡（见 data_prep.py）。
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
from lab09.data_prep import build_creditcard, build_tables

CARD_ORDER = ["普通卡", "金卡", "青年卡"]
PALETTE = {"普通卡": COLORS[0], "金卡": COLORS[1], "青年卡": COLORS[2]}


def summary_table(cc: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for t in CARD_ORDER:
        g = cc[cc["type"] == t]
        rows.append({
            "卡类型": t,
            "发卡量": len(g),
            "占比": len(g) / len(cc),
            "年龄中位数": g["age"].median(),
            "男性占比": (g["sex"] == "男").mean(),
            "交易次数中位数": g["trans_count"].median(),
            "发卡前余额中位数": g["balance"].median(),
            "平均出账比例": g["out_ratio"].mean(),
            "平均贷借比": g["out_in_ratio"].mean(),
        })
    return pd.DataFrame(rows)


def plot_count(cc: pd.DataFrame) -> Path:
    counts = cc["type"].value_counts().reindex(CARD_ORDER)
    fig, ax = plt.subplots(figsize=(6.6, 4))
    bars = ax.bar(counts.index, counts.values, color=[PALETTE[t] for t in counts.index], width=0.55)
    for b, v in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 12, f"{v}\n({v / len(cc):.0%})",
                ha="center", fontsize=9.5)
    ax.set_ylim(0, counts.max() * 1.22)
    ax.set_ylabel("发卡量（张）")
    ax.set_title("各信用卡类型发卡量：普通卡远多于金卡与青年卡")
    return save_fig(fig, "lab09_card_count")


def boxplot(cc, y, title, fname, ylabel) -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    sns.boxplot(data=cc, x="type", y=y, order=CARD_ORDER, hue="type",
                palette=PALETTE, legend=False, width=0.5, ax=ax, showfliers=False)
    sns.stripplot(data=cc, x="type", y=y, order=CARD_ORDER, color="#444444",
                  size=2, alpha=0.25, ax=ax)
    medians = cc.groupby("type")[y].median().reindex(CARD_ORDER)
    for i, m in enumerate(medians):
        ax.text(i + 0.33, m, f"{m:,.1f}" if y == "age" else f"{m:,.0f}", ha="left",
                va="center", fontsize=8.5, color="#222222")
    ax.set_xlabel("卡类型")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    return save_fig(fig, fname)


def plot_sex(cc: pd.DataFrame) -> Path:
    ct = cc.groupby(["type", "sex"]).size().unstack(fill_value=0).reindex(CARD_ORDER)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = range(len(ct))
    w = 0.36
    ax.bar([i - w / 2 for i in x], ct["男"], width=w, color=COLORS[0], label="男")
    ax.bar([i + w / 2 for i in x], ct["女"], width=w, color=COLORS[1], label="女")
    for i in x:
        for off, sex in [(-w / 2, "男"), (w / 2, "女")]:
            v = ct.loc[ct.index[i], sex]
            ax.text(i + off, v + 4, str(v), ha="center", fontsize=9)
    ax.set_xticks(list(x))
    labels = []
    for t in ct.index:
        male_share = ct.loc[t, "男"] / ct.loc[t].sum()
        labels.append(f"{t}\n男 {male_share:.0%}")
    ax.set_xticklabels(labels)
    ax.set_ylim(0, ct.values.max() * 1.2)
    ax.set_ylabel("人数")
    ax.set_title("性别 × 卡类型：金卡男性占比突出，普通卡/青年卡接近均衡")
    ax.legend()
    return save_fig(fig, "lab09_gender_type")


def main() -> None:
    setup_plot()

    tables = build_tables()
    cc = build_creditcard(tables)
    summary = summary_table(cc)

    print("=" * 72)
    print("lab09 信用卡用户画像（KDD99 结构，模拟数据 900 张卡）")
    print("=" * 72)
    print("原始表规模：" + "，".join(f"{k}={len(v)}" for k, v in tables.items()))
    print(f"Creditcard 宽表：{cc.shape[0]} 行 × {cc.shape[1]} 列")
    print("字段：" + "、".join(cc.columns))
    print("-" * 72)
    print(summary.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("-" * 72)

    for _, r in summary.iterrows():
        print(f"{r['卡类型']}：{r['发卡量']} 张（{r['占比']:.0%}），"
              f"年龄中位数 {r['年龄中位数']:.1f} 岁，男性 {r['男性占比']:.0%}，"
              f"交易 {r['交易次数中位数']:.0f} 笔，余额中位数 {r['发卡前余额中位数']:,.0f}")

    print("-" * 72)
    print(
        "结论（与教材一致）：\n"
        "  1) 普通卡发行量远多于青年卡和金卡；\n"
        "  2) 金卡与普通卡持卡人年龄中位数接近，青年卡中位数约 20 岁；\n"
        "  3) 金卡男性占比明显更高，普通卡和青年卡男女人数相当；\n"
        "  4) 三类卡交易次数水平相当；\n"
        "  5) 发卡前账户余额中位数：金卡 > 普通卡 > 青年卡，体现财力分层。\n"
        "  运营含义：青年卡做年轻客群拉新，普通卡做大众客群留存，金卡做高净值\n"
        "  客户经营；出账比例/贷借比可作为风险与活跃度监控指标。"
    )

    save_table(cc, "lab09_creditcard")
    save_table(summary, "lab09_profile_summary")

    plot_count(cc)
    boxplot(cc, "age", "各卡类型持卡人年龄分布：青年卡集中在 20 岁上下",
            "lab09_age_box", "持卡年龄（岁）")
    plot_sex(cc)
    boxplot(cc, "trans_count", "各卡类型持卡人交易次数：三类水平相当",
            "lab09_trans_count_box", "发卡前一年交易笔数")
    boxplot(cc, "balance", "发卡前账户余额：金卡 > 普通卡 > 青年卡",
            "lab09_balance_box", "发卡前平均余额（元）")

    print("\n产物已写入 output/figures 与 output/tables（lab09_*）。")


if __name__ == "__main__":
    main()
