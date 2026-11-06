"""lab12 模型层：关系校验、星型模型查询与交叉筛选演示。

教材 12.2 的落点是"数据模型"而不是"分析算法"，因此本模块的"模型"是一组
关于关系的断言：外键是否完整、基数是否与设计一致、规范化模型与星型模型
查询结果是否等价、筛选方向如何影响结果。
"""

from __future__ import annotations

import sqlite3

import pandas as pd

# 规范化模型的 8 条关系（与 data_prep.DDL 中的外键一一对应）
RELATIONSHIPS = [
    ("district", "client", "district_id", "district_id", "1:N"),
    ("district", "account", "district_id", "district_id", "1:N"),
    ("client", "disp", "client_id", "client_id", "1:N"),
    ("account", "disp", "account_id", "account_id", "1:N"),
    ("disp", "card", "disp_id", "disp_id", "1:N"),
    ("account", "trans", "account_id", "account_id", "1:N"),
    ("account", "loan", "account_id", "account_id", "1:N"),
    ("account", "perm_order", "account_id", "account_id", "1:N"),
]

NORMALIZED_SQL = """
SELECT c.type AS card_type,
       ROUND(SUM(t.amount), 2) AS total_amount,
       COUNT(*) AS trans_count
FROM trans t
JOIN account a ON a.account_id = t.account_id
JOIN disp d ON d.account_id = a.account_id
JOIN card c ON c.disp_id = d.disp_id
GROUP BY c.type
ORDER BY c.type
"""

STAR_SQL = """
SELECT c.card_type,
       ROUND(SUM(f.amount), 2) AS total_amount,
       COUNT(*) AS trans_count
FROM fact_trans f
JOIN dim_card c ON c.card_key = f.card_key
GROUP BY c.card_type
ORDER BY c.card_type
"""


def check_foreign_keys(conn: sqlite3.Connection) -> pd.DataFrame:
    """PRAGMA foreign_key_check：返回违规行，空表即表示外键全部有效。"""
    rows = conn.execute("PRAGMA foreign_key_check").fetchall()
    return pd.DataFrame(rows, columns=["表", "rowid", "被引用表", "外键序号"])


def check_cardinality(conn: sqlite3.Connection) -> pd.DataFrame:
    """逐条关系验证：父表主键唯一，且子表外键没有孤儿值。"""
    out = []
    for parent, child, pk, fk, card in RELATIONSHIPS:
        dup = conn.execute(
            f"SELECT COUNT(*) - COUNT(DISTINCT {pk}) FROM {parent}"
        ).fetchone()[0]
        child_n = conn.execute(f"SELECT COUNT(*) FROM {child}").fetchone()[0]
        orphan = conn.execute(
            f"SELECT COUNT(*) FROM {child} c LEFT JOIN {parent} p "
            f"ON c.{fk} = p.{pk} WHERE p.{pk} IS NULL"
        ).fetchone()[0]
        out.append(
            {
                "父表": parent,
                "子表": child,
                "外键": f"{child}.{fk} → {parent}.{pk}",
                "设计基数": card,
                "子表行数": child_n,
                "父键重复": dup,
                "孤儿外键": orphan,
                "结论": "通过" if dup == 0 and orphan == 0 else "异常",
            }
        )
    return pd.DataFrame(out)


def query_compare(conn: sqlite3.Connection) -> pd.DataFrame:
    """同一业务口径分别走规范化模型与星型模型，结果应完全一致。"""
    norm = pd.read_sql_query(NORMALIZED_SQL, conn)
    star = pd.read_sql_query(STAR_SQL, conn)
    assert norm["card_type"].tolist() == star["card_type"].tolist(), "维度成员不一致"

    out = norm.rename(columns={"total_amount": "规范化_金额", "trans_count": "规范化_笔数"})
    out["星型_金额"] = star["total_amount"].to_numpy()
    out["星型_笔数"] = star["trans_count"].to_numpy()
    out["金额一致"] = (out["规范化_金额"] - out["星型_金额"]).abs() < 1e-6
    out["笔数一致"] = out["规范化_笔数"] == out["星型_笔数"]
    return out


def cross_filter_demo(conn: sqlite3.Connection) -> pd.DataFrame:
    """演示交叉筛选方向。

    Power BI 默认是"单向"：维度表筛选事实表。反向（事实表筛选维度表）只
    在设置为"双向"时才成立。这里用两个查询把差别量化出来。
    """
    by_client = conn.execute(
        """SELECT COUNT(*) FROM fact_trans f
           JOIN dim_client c ON c.client_key = f.client_key
           WHERE c.sex = '女'"""
    ).fetchone()[0]
    all_trans = conn.execute("SELECT COUNT(*) FROM fact_trans").fetchone()[0]
    big_trans = conn.execute(
        "SELECT COUNT(*) FROM fact_trans WHERE amount > 7500"
    ).fetchone()[0]
    big_clients = conn.execute(
        "SELECT COUNT(DISTINCT client_key) FROM fact_trans WHERE amount > 7500"
    ).fetchone()[0]
    total_clients = conn.execute("SELECT COUNT(*) FROM dim_client").fetchone()[0]

    return pd.DataFrame(
        [
            {
                "场景": "维度 → 事实（单向，默认）",
                "查询": "性别='女' 的交易笔数",
                "结果": by_client,
                "占比": f"{by_client / all_trans:.1%}",
            },
            {
                "场景": "事实 → 维度（需双向）",
                "查询": "金额>7500 涉及的客户数",
                "结果": big_clients,
                "占比": f"{big_clients / total_clients:.1%}",
            },
            {
                "场景": "参照：金额>7500 的交易笔数",
                "查询": "事实表自身筛选（金额>7500）",
                "结果": big_trans,
                "占比": f"{big_trans / all_trans:.1%}",
            },
        ]
    )
