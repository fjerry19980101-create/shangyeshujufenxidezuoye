"""lab12 数据：KDD99 银行数据集的规范化模型与星型模型。

教材 12.2（PDF p324-346）用 Power BI 讲数据模型：识别主键/外键、判断基数
（1:1、1:N、N:M）、确认交叉筛选方向，最后落成星型模型。本实验用 SQLite
实现同一套关系，并把规范化模型展开成事实表 + 维度表。

数据说明：复用 lab09 的 KDD99 结构模拟数据（900 张卡），补充 district /
account / loan / perm_order 四张表，使关系模型完整。固定随机种子 42。
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / "src"))

from lab09.data_prep import build_tables as build_core_tables  # noqa: E402

DB_PATH = BASE_DIR / "data" / "processed" / "lab12_model.db"
RANDOM_SEED = 42

DISTRICTS = [
    ("东城", "城区"), ("西城", "城区"), ("朝阳", "城区"), ("海淀", "城区"),
    ("丰台", "城区"), ("石景山", "城区"), ("通州", "近郊"), ("昌平", "近郊"),
    ("大兴", "近郊"), ("顺义", "近郊"), ("房山", "远郊"), ("门头沟", "远郊"),
    ("怀柔", "远郊"), ("平谷", "远郊"), ("密云", "远郊"), ("延庆", "远郊"),
    ("浦东", "城区"), ("徐汇", "城区"), ("静安", "城区"), ("黄浦", "城区"),
]

# 规范化模型的建表语句（外键显式声明，SQLite 需 PRAGMA foreign_keys=ON 才生效）
DDL = [
    """CREATE TABLE district (
        district_id INTEGER PRIMARY KEY,
        district_name TEXT NOT NULL,
        region TEXT NOT NULL,
        population INTEGER NOT NULL)""",
    """CREATE TABLE client (
        client_id INTEGER PRIMARY KEY,
        birth_date TEXT NOT NULL,
        sex TEXT NOT NULL,
        district_id INTEGER NOT NULL,
        FOREIGN KEY (district_id) REFERENCES district(district_id))""",
    """CREATE TABLE account (
        account_id INTEGER PRIMARY KEY,
        district_id INTEGER NOT NULL,
        frequency TEXT NOT NULL,
        open_date TEXT NOT NULL,
        FOREIGN KEY (district_id) REFERENCES district(district_id))""",
    """CREATE TABLE disp (
        disp_id INTEGER PRIMARY KEY,
        client_id INTEGER NOT NULL,
        account_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        FOREIGN KEY (client_id) REFERENCES client(client_id),
        FOREIGN KEY (account_id) REFERENCES account(account_id))""",
    """CREATE TABLE card (
        card_id INTEGER PRIMARY KEY,
        disp_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        issued TEXT NOT NULL,
        FOREIGN KEY (disp_id) REFERENCES disp(disp_id))""",
    """CREATE TABLE trans (
        trans_id INTEGER PRIMARY KEY,
        account_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        type TEXT NOT NULL,
        operation TEXT,
        amount REAL NOT NULL,
        balance REAL,
        k_symbol TEXT,
        bank TEXT,
        account TEXT,
        FOREIGN KEY (account_id) REFERENCES account(account_id))""",
    """CREATE TABLE loan (
        loan_id INTEGER PRIMARY KEY,
        account_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        duration INTEGER NOT NULL,
        payments REAL NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (account_id) REFERENCES account(account_id))""",
    """CREATE TABLE perm_order (
        order_id INTEGER PRIMARY KEY,
        account_id INTEGER NOT NULL,
        bank_to TEXT NOT NULL,
        account_to TEXT NOT NULL,
        amount REAL NOT NULL,
        k_symbol TEXT,
        FOREIGN KEY (account_id) REFERENCES account(account_id))""",
]

# 星型模型：一张事实表 + 四张维度表
STAR_DDL = [
    """CREATE TABLE dim_date (
        date_key TEXT PRIMARY KEY,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        day INTEGER NOT NULL,
        weekday TEXT NOT NULL,
        is_weekend INTEGER NOT NULL)""",
    """CREATE TABLE dim_client (
        client_key INTEGER PRIMARY KEY,
        sex TEXT NOT NULL,
        age_band TEXT NOT NULL,
        district_name TEXT NOT NULL,
        region TEXT NOT NULL)""",
    """CREATE TABLE dim_account (
        account_key INTEGER PRIMARY KEY,
        frequency TEXT NOT NULL,
        open_year INTEGER NOT NULL,
        district_name TEXT NOT NULL)""",
    """CREATE TABLE dim_card (
        card_key INTEGER PRIMARY KEY,
        card_type TEXT NOT NULL,
        issued_year INTEGER NOT NULL)""",
    """CREATE TABLE fact_trans (
        trans_id INTEGER PRIMARY KEY,
        date_key TEXT NOT NULL,
        account_key INTEGER NOT NULL,
        client_key INTEGER NOT NULL,
        card_key INTEGER NOT NULL,
        amount REAL NOT NULL,
        trans_type TEXT NOT NULL,
        operation TEXT,
        k_symbol TEXT,
        FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
        FOREIGN KEY (account_key) REFERENCES dim_account(account_key),
        FOREIGN KEY (client_key) REFERENCES dim_client(client_key),
        FOREIGN KEY (card_key) REFERENCES dim_card(card_key))""",
]


def build_tables() -> dict[str, pd.DataFrame]:
    """在 lab09 四张表的基础上补齐 district / account / loan / perm_order。"""
    rng = np.random.default_rng(RANDOM_SEED)
    core = build_core_tables()
    card = core["card"].copy()
    clients = core["clients"].copy()

    district = pd.DataFrame(
        [
            {
                "district_id": i + 1,
                "district_name": name,
                "region": region,
                "population": int(rng.integers(8, 60) * 10_000),
            }
            for i, (name, region) in enumerate(DISTRICTS)
        ]
    )

    clients["district_id"] = rng.integers(1, len(DISTRICTS) + 1, size=len(clients))

    disp = core["disp"].copy()
    issued = pd.to_datetime(card["issued"])
    account = pd.DataFrame(
        {
            "account_id": disp["account_id"],
            "district_id": rng.integers(1, len(DISTRICTS) + 1, size=len(disp)),
            "frequency": rng.choice(["月发", "周发"], size=len(disp), p=[0.8, 0.2]),
            "open_date": (issued - pd.to_timedelta(rng.integers(30, 400, len(disp)), unit="D"))
            .dt.strftime("%Y-%m-%d"),
        }
    )

    # 约 65% 的账户有贷款
    n_loans = int(len(account) * 0.65)
    loan_accounts = rng.choice(account["account_id"], size=n_loans, replace=False)
    loan_dates = pd.to_datetime(
        rng.choice(account["open_date"], size=n_loans, replace=False)
    ) + pd.to_timedelta(rng.integers(180, 1200, n_loans), unit="D")
    duration = rng.choice([12, 24, 36, 48], size=n_loans, p=[0.3, 0.4, 0.2, 0.1])
    amount = np.round(rng.uniform(2_000, 80_000, n_loans), 2)
    loan = pd.DataFrame(
        {
            "loan_id": np.arange(1, n_loans + 1),
            "account_id": loan_accounts,
            "date": loan_dates.strftime("%Y-%m-%d"),
            "amount": amount,
            "duration": duration,
            "payments": np.round(amount / duration, 2),
            "status": rng.choice(["A", "B", "C"], size=n_loans, p=[0.5, 0.3, 0.2]),
        }
    )

    n_orders = len(account) * 2
    perm_order = pd.DataFrame(
        {
            "order_id": np.arange(1, n_orders + 1),
            "account_id": np.repeat(account["account_id"].to_numpy(), 2),
            "bank_to": rng.choice(["AB", "CD", "EF", "GH"], size=n_orders),
            "account_to": rng.choice(["A", "B", "C", "D"], size=n_orders),
            "amount": np.round(rng.uniform(100, 5_000, n_orders), 2),
            "k_symbol": rng.choice(
                ["房屋贷款", "租金", "保险", "其他"], size=n_orders, p=[0.15, 0.25, 0.2, 0.4]
            ),
        }
    )

    return {
        "district": district,
        "client": clients[["client_id", "birth_date", "sex", "district_id"]],
        "account": account,
        "disp": disp,
        "card": card,
        "trans": core["trans"],
        "loan": loan,
        "perm_order": perm_order,
    }


def build_star(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """把规范化模型（雪花）展开成星型模型。"""
    client, district = tables["client"], tables["district"]
    account, disp = tables["account"], tables["disp"]
    card, trans = tables["card"], tables["trans"]

    birth = pd.to_datetime(client["birth_date"])
    age = 1998 - birth.dt.year
    dim_client = client[["client_id", "sex", "district_id"]].merge(
        district[["district_id", "district_name", "region"]], on="district_id", how="left"
    )
    dim_client["age_band"] = pd.cut(
        age, bins=[0, 30, 40, 50, 100],
        labels=["30岁以下", "30-39", "40-49", "50岁及以上"],
    ).astype(str)
    dim_client = dim_client.rename(columns={"client_id": "client_key"})[
        ["client_key", "sex", "age_band", "district_name", "region"]
    ]

    dim_account = account[["account_id", "district_id", "frequency", "open_date"]].merge(
        district[["district_id", "district_name"]], on="district_id", how="left"
    )
    dim_account["open_year"] = pd.to_datetime(dim_account["open_date"]).dt.year
    dim_account = dim_account.rename(columns={"account_id": "account_key"})[
        ["account_key", "frequency", "open_year", "district_name"]
    ]

    dim_card = card[["card_id", "type", "issued"]].copy()
    dim_card["issued_year"] = pd.to_datetime(dim_card["issued"]).dt.year
    dim_card = dim_card.rename(columns={"card_id": "card_key", "type": "card_type"})[
        ["card_key", "card_type", "issued_year"]
    ]

    dates = pd.to_datetime(trans["date"])
    dim_date = pd.DataFrame({"date_key": sorted(dates.dt.strftime("%Y-%m-%d").unique())})
    dim_date["date_key"] = pd.to_datetime(dim_date["date_key"])
    dim_date["year"] = dim_date["date_key"].dt.year
    dim_date["month"] = dim_date["date_key"].dt.month
    dim_date["day"] = dim_date["date_key"].dt.day
    dim_date["weekday"] = dim_date["date_key"].dt.day_of_week.map(
        {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
    )
    dim_date["is_weekend"] = (dim_date["date_key"].dt.day_of_week >= 5).astype(int)
    dim_date["date_key"] = dim_date["date_key"].dt.strftime("%Y-%m-%d")

    # 交易只带 account_id，通过 disp 补出 client_key / card_key
    link = disp[["account_id", "client_id", "disp_id"]].merge(
        card[["disp_id", "card_id"]], on="disp_id", how="left"
    )
    fact = trans.merge(link, on="account_id", how="left")
    fact_trans = pd.DataFrame(
        {
            "trans_id": fact["trans_id"],
            "date_key": fact["date"],
            "account_key": fact["account_id"],
            "client_key": fact["client_id"],
            "card_key": fact["card_id"],
            "amount": fact["amount"],
            "trans_type": fact["type"],
            "operation": fact["operation"],
            "k_symbol": fact["k_symbol"],
        }
    )

    return {
        "dim_date": dim_date.sort_values("date_key").reset_index(drop=True),
        "dim_client": dim_client,
        "dim_account": dim_account,
        "dim_card": dim_card,
        "fact_trans": fact_trans,
    }


def build_database(tables: dict[str, pd.DataFrame], star: dict[str, pd.DataFrame]) -> Path:
    """重建 SQLite 数据库：先规范化 8 表，再星型 5 表。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            for ddl in DDL:
                conn.execute(ddl)
            for name in [
                "district", "client", "account", "disp", "card", "trans", "loan", "perm_order",
            ]:
                tables[name].to_sql(name, conn, if_exists="append", index=False)
            for ddl in STAR_DDL:
                conn.execute(ddl)
            for name, df in star.items():
                df.to_sql(name, conn, if_exists="append", index=False)
    finally:
        conn.close()
    return DB_PATH


def load_database() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


if __name__ == "__main__":
    t = build_tables()
    s = build_star(t)
    print({k: v.shape for k, v in t.items()})
    print({k: v.shape for k, v in s.items()})
    print(build_database(t, s))
