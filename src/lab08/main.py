"""lab08 SQL 基础与多表整合（SQLite 版）。

教材出处：第 8 章 SQL 语言基础与 MySQL 入门（PDF p238-266，MySQL 实现）

业务问题
--------
数据分析师需要"自助取数"：不依赖 IT 出报表，自己从业务数据库中按需查询、
计算指标、合并多表。教材以 KDD99 银行数据集为例讲解 SQL。

本实验的迁移思路
--------
- 教材用 MySQL，本实验用 Python 标准库 `sqlite3`（无需安装数据库服务）；
- 每条教材 SQL 都在 SQLite 中执行，同时用 `pandas` 写等价实现；
- 逐条对拍行数、列与数值，确保 SQL 与 pandas 结果一致；
- 表结构与书中一致：sale / clients / disp / card / trans / loans。

数据说明：按 KDD99 表结构生成的模拟小样本（见 data_prep.py）。
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common.config import COLORS, save_fig, save_table, setup_plot
from lab08.data_prep import build_database, build_tables

WEEKDAY = "((CAST(strftime('%w', date) AS INTEGER) + 6) % 7)"
RESULTS: list[dict] = []


def query(conn: sqlite3.Connection, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn)


def check(name: str, sdf: pd.DataFrame, pdf: pd.DataFrame, sort_cols: list[str],
          note: str = "") -> None:
    """对拍 SQL 与 pandas 结果。"""
    pdf = pdf[sdf.columns].copy()
    s = sdf.copy()
    for df in (s, pdf):
        for col in df.columns:
            if pd.api.types.is_float_dtype(df[col]):
                df[col] = df[col].round(6)
    s = s.sort_values(sort_cols).reset_index(drop=True)
    pdf = pdf.sort_values(sort_cols).reset_index(drop=True)
    try:
        pd.testing.assert_frame_equal(s, pdf, check_dtype=False, atol=1e-6)
        status = "PASS"
    except AssertionError as exc:  # 保留首行差异方便排查
        status = "FAIL"
        note = str(exc).splitlines()[0]
    RESULTS.append({"检查项": name, "SQL行数": len(sdf), "pandas行数": len(pdf),
                    "状态": status, "备注": note})
    print(f"  [{status}] {name}：SQL {len(sdf)} 行 / pandas {len(pdf)} 行"
          + (f"  {note}" if note and status == "FAIL" else ""))


def compare_union(conn: sqlite3.Connection, tables: dict[str, pd.DataFrame]) -> None:
    """UNION 去重 / UNION ALL 保留重复的行数对比。"""
    base_sql = "SELECT year, market FROM sale WHERE year = 2012"
    branch_sql = "SELECT year, market FROM sale WHERE market = '东'"
    n_union = len(query(conn, f"{base_sql} UNION {branch_sql}"))
    n_union_all = len(query(conn, f"{base_sql} UNION ALL {branch_sql}"))

    sale = tables["sale"]
    left = sale.loc[sale["year"] == 2012, ["year", "market"]]
    right = sale.loc[sale["market"] == "东", ["year", "market"]]
    n_pd_union = len(pd.concat([left, right]).drop_duplicates())
    n_pd_union_all = len(pd.concat([left, right]))

    ok = n_union == n_pd_union and n_union_all == n_pd_union_all
    RESULTS.append({"检查项": "UNION / UNION ALL", "SQL行数": n_union_all,
                    "pandas行数": n_pd_union_all, "状态": "PASS" if ok else "FAIL",
                    "备注": f"UNION 去重后 {n_union} 行（pandas {n_pd_union}）"})
    print(f"  [{'PASS' if ok else 'FAIL'}] UNION / UNION ALL："
          f"UNION {n_union} 行、UNION ALL {n_union_all} 行"
          f"（pandas {n_pd_union} / {n_pd_union_all}）")


def plot_market_rate(sale: pd.DataFrame) -> Path:
    rate = sale.assign(rate=sale["profit"] / sale["sale"]).groupby("market", as_index=False)["rate"].mean()
    rate = rate.sort_values("rate", ascending=False)
    fig, ax = plt.subplots(figsize=(6.6, 4))
    bars = ax.bar(rate["market"], rate["rate"], color=COLORS[: len(rate)], width=0.55)
    for b, v in zip(bars, rate["rate"]):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.002, f"{v:.1%}", ha="center", fontsize=10)
    ax.set_ylim(0, rate["rate"].max() * 1.18)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("各市场平均销售利润率（profit / sale）")
    ax.set_ylabel("平均利润率")
    ax.set_xlabel("市场")
    return save_fig(fig, "lab08_market_rate")


def plot_daily(daily: pd.DataFrame) -> Path:
    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["date"])
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.bar(daily["date"], daily["cnt"], color=COLORS[0], width=0.7, label="交易笔数")
    ax.axhline(60, color=COLORS[3], ls="--", lw=1.2, label="HAVING 阈值 60 笔")
    ax.set_ylabel("交易笔数")
    ax.set_title("1998 年 12 月每日交易笔数（教材阈值 300 按样本量等比调整）")

    ax2 = ax.twinx()
    ax2.plot(daily["date"], daily["sum_amount"] / 10000, color=COLORS[1], lw=1.8,
             marker="o", ms=3, label="日交易总额（万元）")
    ax2.set_ylabel("日交易总额（万元）")

    handles, labels = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles + handles2, labels + labels2, fontsize=8.5, loc="upper left")
    fig.autofmt_xdate()
    return save_fig(fig, "lab08_daily_trans")


def main() -> None:
    setup_plot()
    tables = build_tables()
    db_path = build_database(tables)
    conn = sqlite3.connect(db_path)

    print("=" * 70)
    print("lab08 SQL 基础与多表整合（SQLite + pandas 对拍）")
    print("=" * 70)
    print("表规模：" + "，".join(f"{k}={len(v)}" for k, v in tables.items()))

    sale, clients, disp, card, trans, loans = (tables[k] for k in
                                              ["sale", "clients", "disp", "card", "trans", "loans"])

    print("\n[1] 单表查询：筛选 + 排序")
    sql_a = """
        SELECT account_id, date, bank, amount
        FROM trans
        WHERE date BETWEEN '1998-12-01' AND '1998-12-31'
          AND k_symbol = '房屋贷款'
        ORDER BY date, account_id
    """
    sdf = query(conn, sql_a)
    pdf = trans[(trans["date"] >= "1998-12-01") & (trans["date"] <= "1998-12-31")
                & (trans["k_symbol"] == "房屋贷款")][["account_id", "date", "bank", "amount"]]
    check("单表筛选排序（12 月房屋贷款）", sdf, pdf, ["date", "account_id"])

    print("\n[2] 创建新列：销售利润率 rate")
    sql_b = "SELECT *, profit / sale AS rate FROM sale WHERE profit / sale < 0.07 ORDER BY year, market"
    sdf = query(conn, sql_b)
    pdf = sale.assign(rate=sale["profit"] / sale["sale"])
    pdf = pdf[pdf["rate"] < 0.07][["year", "market", "sale", "profit", "rate"]]
    check("新列 rate + WHERE 表达式", sdf, pdf, ["year", "market", "sale", "profit"])

    print("\n[3] 日期函数 + CASE 重编码：是否工作日")
    sql_c = f"""
        SELECT account_id, date, bank, amount,
               {WEEKDAY} AS weekday,
               CASE WHEN {WEEKDAY} >= 5 THEN '非工作日' ELSE '是工作日' END AS 是否工作日
        FROM trans
        WHERE date BETWEEN '1998-12-01' AND '1998-12-31'
          AND k_symbol = '房屋贷款'
        ORDER BY date, account_id
    """
    sdf = query(conn, sql_c)
    pdf = trans[(trans["date"] >= "1998-12-01") & (trans["date"] <= "1998-12-31")
                & (trans["k_symbol"] == "房屋贷款")][["account_id", "date", "bank", "amount"]].copy()
    pdf["weekday"] = pd.to_datetime(pdf["date"]).dt.day_of_week
    pdf["是否工作日"] = np.where(pdf["weekday"] >= 5, "非工作日", "是工作日")
    check("weekday + CASE 工作日标记", sdf, pdf, ["date", "account_id"])

    print("\n[4] 汇总 + 分组 + HAVING")
    sql_d = """
        SELECT date, COUNT(trans_id) AS cnt, AVG(amount) AS mean_amount,
               SUM(amount) AS sum_amount
        FROM trans
        GROUP BY date
        HAVING COUNT(trans_id) > 60
        ORDER BY date
    """
    daily = query(conn, sql_d)
    agg = trans.groupby("date", as_index=False).agg(
        cnt=("trans_id", "count"), mean_amount=("amount", "mean"), sum_amount=("amount", "sum"))
    pdf = agg[agg["cnt"] > 60].sort_values("date")
    check("按日汇总 + HAVING > 60", daily, pdf, ["date"])

    print("\n[5] 三表左连接：card → disp → clients")
    sql_e = """
        SELECT t1.card_id, t1.disp_id, t1.issued, t1.type,
               t3.sex, t3.birth_date, t3.district_id
        FROM card t1
        LEFT JOIN disp t2 ON t1.disp_id = t2.disp_id
        LEFT JOIN clients t3 ON t2.client_id = t3.client_id
        ORDER BY t1.card_id
    """
    card_client = query(conn, sql_e)
    dc = disp[["disp_id", "client_id"]]
    pdf = (card[["card_id", "disp_id", "issued", "type"]]
           .merge(dc, on="disp_id", how="left")
           .merge(clients[["client_id", "sex", "birth_date", "district_id"]],
                  on="client_id", how="left"))
    check("三表左连接 card-disp-clients", card_client, pdf, ["card_id"])

    print("\n[6] 不等值连接：放款前 365 天内的交易")
    sql_f = """
        SELECT t1.loan_id, t1.account_id, t1.date, t1.amount,
               t2.trans_id, t2.date AS trans_date, t2.amount AS trans_amount, t2.k_symbol
        FROM loans t1
        JOIN trans t2
          ON t1.account_id = t2.account_id
         AND t1.date > t2.date
         AND t1.date <= date(t2.date, '+365 days')
        ORDER BY t1.loan_id, t1.account_id, t1.date, t2.date
    """
    unequal = query(conn, sql_f)
    t = trans[["account_id", "trans_id", "date", "amount", "k_symbol"]].rename(
        columns={"date": "trans_date", "amount": "trans_amount"})
    pdf = loans[["loan_id", "account_id", "date", "amount"]].merge(t, on="account_id", how="left")
    pdf = pdf[pdf["trans_date"].notna()].copy()
    lower = (pd.to_datetime(pdf["date"]) - pd.Timedelta(days=365)).dt.strftime("%Y-%m-%d")
    pdf = pdf[(pdf["trans_date"] < pdf["date"]) & (pdf["trans_date"] >= lower)]
    check("不等值连接（贷款前一年交易）", unequal,
          pdf[["loan_id", "account_id", "date", "amount", "trans_id",
               "trans_date", "trans_amount", "k_symbol"]],
          ["loan_id", "account_id", "date", "trans_date"])

    print("\n[7] 子查询")
    sql_g1 = """
        SELECT loan_id, account_id, date, amount
        FROM loans
        WHERE amount > (SELECT AVG(amount) FROM loans)
        ORDER BY loan_id
    """
    sdf = query(conn, sql_g1)
    pdf = loans[["loan_id", "account_id", "date", "amount"]][loans["amount"] > loans["amount"].mean()]
    check("非关联子查询（高于平均贷款额）", sdf, pdf, ["loan_id"])

    sql_g2 = """
        SELECT c.client_id, c.sex
        FROM clients c
        WHERE EXISTS (
            SELECT 1 FROM disp d
            WHERE d.client_id = c.client_id AND d.type = 'OWNER'
        )
        ORDER BY c.client_id
    """
    sdf = query(conn, sql_g2)
    owner_ids = disp.loc[disp["type"] == "OWNER", "client_id"].unique()
    pdf = clients[clients["client_id"].isin(owner_ids)][["client_id", "sex"]]
    check("关联子查询（EXISTS 有 OWNER 账户）", sdf, pdf, ["client_id"])

    print("\n[8] 集合运算：UNION 与 UNION ALL")
    compare_union(conn, tables)

    print("\n[9] 视图：把三表连接固化为可复用视图")
    conn.execute("DROP VIEW IF EXISTS v_card_client")
    conn.execute(f"""
        CREATE VIEW v_card_client AS
        SELECT t1.card_id, t1.disp_id, t1.issued, t1.type,
               t3.sex, t3.birth_date, t3.district_id
        FROM card t1
        LEFT JOIN disp t2 ON t1.disp_id = t2.disp_id
        LEFT JOIN clients t3 ON t2.client_id = t3.client_id
    """)
    view_df = query(conn, "SELECT * FROM v_card_client ORDER BY card_id")
    check("视图 v_card_client 与三表连接一致", view_df, card_client[view_df.columns], ["card_id"])

    # 汇总指标
    print("\n" + "-" * 70)
    rate = sale.assign(rate=sale["profit"] / sale["sale"]).groupby("market")["rate"].mean()
    print("各市场平均销售利润率：" + "，".join(f"{m} {v:.1%}" for m, v in rate.items()))
    dec_house = len(query(conn, sql_a))
    print(f"12 月房屋贷款交易 {dec_house} 笔；日均超 60 笔的交易日 {len(daily)} 天")
    print(f"三表连接得到 {len(card_client)} 张卡；贷款前一年交易匹配 {len(unequal)} 行；"
          f"高于平均贷款额 {len(query(conn, sql_g1))} 笔")

    failed = [r for r in RESULTS if r["状态"] != "PASS"]
    print("\n对拍汇总：" + f"{len(RESULTS)} 项，通过 {len(RESULTS) - len(failed)}，失败 {len(failed)}")

    save_table(pd.DataFrame(RESULTS), "lab08_sql_vs_pandas")
    save_table(daily, "lab08_daily_summary")
    save_table(card_client, "lab08_card_client")
    plot_market_rate(sale)
    plot_daily(daily)

    conn.close()
    print("\n产物已写入 output/figures 与 output/tables（lab08_*）。")


if __name__ == "__main__":
    main()
