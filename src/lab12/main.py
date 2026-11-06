"""lab12 数据模型：E-R 图、星型模型与交叉筛选（Power BI → Python）。

教材出处：第 12 章 12.2 数据模型（PDF p324-346，Power BI 实现）

业务问题
--------
拿到 KDD99 银行数据集后，先要读懂表与表之间的关系：谁是主键、谁是外键、
是一对一还是一对多、筛选该往哪个方向传。关系没理清，后面的度量值一定算错。

Python 迁移
--------
- 规范化模型：SQLite 建 8 张表，显式声明外键，用 PRAGMA 校验；
- 星型模型：把雪花结构展开成 1 张事实表 + 4 张维度表；
- 等价性：同一口径分别走两套模型，结果逐行对拍；
- 交叉筛选：量化"维度筛事实"与"事实筛维度"的差别；
- E-R 图与星型图：networkx + matplotlib。
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from common.config import COLORS, save_fig, save_table, setup_plot
from lab12.data_prep import build_database, build_star, build_tables
from lab12.model import (
    RELATIONSHIPS,
    check_cardinality,
    check_foreign_keys,
    cross_filter_demo,
    query_compare,
)

# E-R 图的固定布局与连线标签偏移（避免标签压线）
ER_POS = {
    "district": (0.0, 3.0),
    "client": (-2.2, 1.7),
    "account": (2.2, 1.7),
    "disp": (0.0, 0.6),
    "card": (-2.2, -0.7),
    "trans": (0.0, -1.8),
    "loan": (2.2, -1.8),
    "perm_order": (4.2, -1.8),
}

ER_LABEL_POS = {
    ("district", "client"): (-1.1, 2.42),
    ("district", "account"): (1.1, 2.42),
    ("client", "disp"): (-1.1, 1.15),
    ("account", "disp"): (1.1, 1.15),
    ("disp", "card"): (-1.1, -0.05),
    ("account", "trans"): (1.1, -0.05),
    ("account", "loan"): (2.5, -0.05),
    ("account", "perm_order"): (3.4, 0.0),
}

ER_TEXT = {
    "district": "district\nPK district_id",
    "client": "client\nPK client_id\nFK district_id",
    "account": "account\nPK account_id\nFK district_id",
    "disp": "disp\nPK disp_id\nFK client_id\nFK account_id",
    "card": "card\nPK card_id\nFK disp_id",
    "trans": "trans\nPK trans_id\nFK account_id",
    "loan": "loan\nPK loan_id\nFK account_id",
    "perm_order": "perm_order\nPK order_id\nFK account_id",
}


def draw_er() -> Path:
    g = nx.DiGraph()
    g.add_nodes_from(ER_POS)
    g.add_edges_from([(p, c) for p, c, *_ in RELATIONSHIPS])

    fig, ax = plt.subplots(figsize=(11, 6.4))
    nx.draw_networkx_edges(
        g, ER_POS, ax=ax, edge_color=COLORS[5], width=1.4, arrows=True,
        arrowsize=14, connectionstyle="arc3,rad=0.0",
    )
    for node, text in ER_TEXT.items():
        ax.text(
            *ER_POS[node], text, ha="center", va="center", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.45", fc="white", ec=COLORS[0], lw=1.2),
        )
    for (u, v), (x, y) in ER_LABEL_POS.items():
        ax.text(x, y, "1 : N", ha="center", va="center", fontsize=8.5,
                color=COLORS[3], fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
    ax.text(0, 4.0, "KDD99 规范化模型（雪花结构）：disp 为 client 与 account 的桥表",
            ha="center", fontsize=13, fontweight="bold")
    ax.text(0, -2.65, "箭头方向 = 外键指向主键（多端 → 一端）；全部关系均为 1:N",
            ha="center", fontsize=9, color=COLORS[5])
    ax.set_xlim(-4.0, 5.2)
    ax.set_ylim(-2.9, 4.3)
    ax.axis("off")
    save_fig(fig, "lab12_er")
    return ROOT


def draw_star(fact_rows: int) -> Path:
    pos = {
        "dim_client": (0.0, 2.3),
        "dim_date": (-2.6, 1.3),
        "dim_card": (2.6, 1.3),
        "dim_account": (0.0, -2.1),
        "fact_trans": (0.0, 0.0),
    }
    g = nx.DiGraph([(k, "fact_trans") for k in pos if k != "fact_trans"])

    fig, ax = plt.subplots(figsize=(10, 6.2))
    nx.draw_networkx_edges(g, pos, ax=ax, edge_color=COLORS[5], width=1.6, arrows=True,
                           arrowsize=14)
    labels = {
        "fact_trans": f"fact_trans\n{fact_rows:,} 行\nFK date_key / account_key\nFK client_key / card_key",
        "dim_client": "dim_client\nclient_key\nsex / age_band\ndistrict / region",
        "dim_date": "dim_date\ndate_key\nyear / month\nday / weekday",
        "dim_card": "dim_card\ncard_key\ncard_type\nissued_year",
        "dim_account": "dim_account\naccount_key\nfrequency\nopen_year / district",
    }
    for node, text in labels.items():
        big = node == "fact_trans"
        ax.text(
            *pos[node], text, ha="center", va="center", fontsize=9,
            bbox=dict(
                boxstyle="round,pad=0.5",
                fc="#EAF1F8" if big else "white",
                ec=COLORS[1] if big else COLORS[0],
                lw=1.6 if big else 1.1,
            ),
        )
    for (u, v), xy in {
        ("dim_client", "fact_trans"): (0, 1.15),
        ("dim_date", "fact_trans"): (-1.3, 0.65),
        ("dim_card", "fact_trans"): (1.3, 0.65),
        ("dim_account", "fact_trans"): (0, -1.05),
    }.items():
        ax.text(*xy, "1 : N", ha="center", va="center", fontsize=8.5,
                color=COLORS[3], fontweight="bold")

    ax.set_title("星型模型：1 张事实表 + 4 张维度表（维度主键 → 事实外键）")
    ax.text(0, -3.1, "口径示例：按 card_type 汇总 amount，与规范化模型的多表 JOIN 结果逐行一致",
            ha="center", fontsize=9, color=COLORS[5])
    ax.set_xlim(-4.2, 4.2)
    ax.set_ylim(-3.4, 3.4)
    ax.axis("off")
    save_fig(fig, "lab12_star")
    return ROOT


def collect_schema(conn: sqlite3.Connection) -> pd.DataFrame:
    """导出每张表的字段、类型、主键与外键（相当于 Power BI 的模型视图）。"""
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
    ]
    rows = []
    for t in tables:
        fks = {r[3]: f"{r[2]}.{r[4]}" for r in conn.execute(f"PRAGMA foreign_key_list({t})")}
        for cid, name, ctype, notnull, _default, pk in conn.execute(f"PRAGMA table_info({t})"):
            rows.append(
                {
                    "表": t,
                    "字段": name,
                    "类型": ctype,
                    "主键": "是" if pk else "",
                    "非空": "是" if notnull else "",
                    "外键": fks.get(name, ""),
                    "字段序号": cid,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    setup_plot()
    tables = build_tables()
    star = build_star(tables)
    db_path = build_database(tables, star)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        fk = check_foreign_keys(conn)
        card = check_cardinality(conn)
        compare = query_compare(conn)
        demo = cross_filter_demo(conn)
        schema = collect_schema(conn)
    finally:
        conn.close()

    assert fk.empty, f"存在外键违规：\n{fk}"
    assert card["结论"].eq("通过").all(), card
    assert compare["金额一致"].all() and compare["笔数一致"].all(), compare

    save_table(schema, "lab12_schema")
    save_table(
        pd.DataFrame(
            [
                {"父表": p, "子表": c, "基数": card_n, "外键": f"{c}.{fk_col} → {p}.{pk}"}
                for p, c, pk, fk_col, card_n in RELATIONSHIPS
            ]
        ),
        "lab12_relationships",
    )
    save_table(card, "lab12_cardinality_check")
    save_table(compare, "lab12_compare")
    save_table(demo, "lab12_cross_filter")

    draw_er()
    draw_star(len(star["fact_trans"]))

    print("=" * 72)
    print(f"数据库：{db_path}")
    print(f"规范化模型：{ {k: len(v) for k, v in tables.items()} }")
    print(f"星型模型：{ {k: len(v) for k, v in star.items()} }")
    print("-" * 72)
    print("外键检查：通过（0 条违规）")
    print(card.to_string(index=False))
    print("-" * 72)
    print("规范化 vs 星型（按卡类型汇总金额）：")
    print(compare.to_string(index=False))
    print("-" * 72)
    print("交叉筛选演示：")
    print(demo.to_string(index=False))
    print("=" * 72)


if __name__ == "__main__":
    main()
