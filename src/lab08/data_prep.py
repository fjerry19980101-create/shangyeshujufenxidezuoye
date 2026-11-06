"""lab08 数据：KDD99 银行数据集的小样本关系表 + SQLite 建库。

教材第 8 章以 kdd99 库的 sale、clients、disp、card、trans、loans 等表讲解 SQL。
本实验按同一表结构生成小样本数据（固定随机种子 42），用于：

- 单表查询：筛选、排序、去重、新列、CASE 重编码；
- 汇总：COUNT/AVG/SUM + GROUP BY + HAVING；
- 多表连接：card-disp-clients 三表连接、贷款与交易的不等值连接；
- 子查询与 UNION / UNION ALL；
- 视图。

数据为按 KDD99 表结构模拟的样本，不代表真实银行数据。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_SEED = 42
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "lab08_kdd99.db"


def _random_dates(rng, n, start: str, end: str) -> list[str]:
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    days = rng.integers(0, (end_ts - start_ts).days + 1, size=n)
    return [(start_ts + pd.Timedelta(days=int(d))).strftime("%Y-%m-%d") for d in days]


def build_tables() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(RANDOM_SEED)

    # 销售表：2010-2013 × 4 个市场
    markets = ["东", "西", "南", "北"]
    rows = []
    for year in range(2010, 2014):
        for market in markets:
            for _ in range(5):
                sale = int(rng.integers(800, 1600))
                rate = float(rng.uniform(0.03, 0.18))
                rows.append({"year": year, "market": market, "sale": sale,
                             "profit": round(sale * rate, 2)})
    sale = pd.DataFrame(rows)

    # 客户表
    n_clients = 400
    sex = rng.choice(["女", "男"], size=n_clients, p=[0.55, 0.45])
    clients = pd.DataFrame({
        "client_id": np.arange(1, n_clients + 1),
        "sex": sex,
        "birth_date": _random_dates(rng, n_clients, "1950-01-01", "1985-12-31"),
        "district_id": rng.integers(1, 78, size=n_clients),
    })

    # 账户归属表
    n_disp = 500
    disp = pd.DataFrame({
        "disp_id": np.arange(1, n_disp + 1),
        "client_id": rng.integers(1, n_clients + 1, size=n_disp),
        "account_id": rng.integers(1, 451, size=n_disp),
        "type": rng.choice(["OWNER", "DISPOSER"], size=n_disp, p=[0.7, 0.3]),
    })

    # 信用卡表
    n_card = 350
    card = pd.DataFrame({
        "card_id": np.arange(1, n_card + 1),
        "disp_id": rng.choice(disp["disp_id"], size=n_card, replace=False),
        "type": rng.choice(["普通", "金卡", "白金"], size=n_card, p=[0.6, 0.3, 0.1]),
        "issued": _random_dates(rng, n_card, "1994-01-01", "1998-12-31"),
    })

    # 交易表：3000 笔，其中约 2/3 集中在 1998 年 12 月
    n_trans = 3000
    dec_n = 2000
    dates = _random_dates(rng, dec_n, "1998-12-01", "1998-12-31") + \
        _random_dates(rng, n_trans - dec_n, "1998-01-01", "1998-11-30")
    trans = pd.DataFrame({
        "trans_id": np.arange(1, n_trans + 1),
        "account_id": rng.integers(1, 451, size=n_trans),
        "date": dates,
        "type": rng.choice(["借", "贷"], size=n_trans),
        "operation": rng.choice(["转入", "转出", "存款", "取款"], size=n_trans),
        "amount": np.round(rng.uniform(100, 10000, size=n_trans), 2),
        "balance": np.round(rng.uniform(0, 50000, size=n_trans), 2),
        "k_symbol": rng.choice(["房屋贷款", "租金", "保险", "其他"], size=n_trans,
                               p=[0.15, 0.25, 0.20, 0.40]),
        "bank": rng.choice(["AB", "CD", "EF", "GH"], size=n_trans),
        "account": rng.choice(["A", "B", "C"], size=n_trans),
    })

    # 贷款表
    n_loans = 200
    amount = np.round(rng.uniform(10000, 500000, size=n_loans), 2)
    duration = rng.choice([12, 24, 36, 60], size=n_loans)
    loans = pd.DataFrame({
        "loan_id": np.arange(1, n_loans + 1),
        "account_id": rng.integers(1, 451, size=n_loans),
        "date": _random_dates(rng, n_loans, "1998-01-01", "1998-12-31"),
        "amount": amount,
        "duration": duration,
        "payments": np.round(amount / duration, 2),
        "status": rng.choice(["A", "B", "C"], size=n_loans, p=[0.7, 0.2, 0.1]),
    })

    return {"sale": sale, "clients": clients, "disp": disp,
            "card": card, "trans": trans, "loans": loans}


def build_database(tables: dict[str, pd.DataFrame] | None = None,
                   path: Path = DB_PATH) -> Path:
    """删除旧库后重建 SQLite 数据库。"""
    tables = build_tables() if tables is None else tables
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    with sqlite3.connect(path) as conn:
        for name, df in tables.items():
            df.to_sql(name, conn, index=False)
    return path


if __name__ == "__main__":
    data = build_tables()
    print({k: v.shape for k, v in data.items()})
    print(build_database(data))
