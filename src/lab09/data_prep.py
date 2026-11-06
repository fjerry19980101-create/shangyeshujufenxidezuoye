"""lab09 数据与取数：信用卡用户画像（KDD99 银行数据集结构）。

教材 9.4 用 3 段 SQL 从 KDD99 的 card / disp / clients / trans 表取数，
生成 Creditcard 宽表（每张卡一行），再用 Excel 画 5 张画像图。

本实验用 pandas 复现这三段取数逻辑：

- var1：card → disp → clients 左连接，计算持卡时年龄 age；
- var2：把每张卡与发卡前的交易做不等值连接，取最近一次交易日 last_days、
  发卡前平均余额 balance；
- var3：把范围限定在发卡前 365 天，统计交易笔数、借/贷金额、出账比例。

公开数据集站点在本机网络不可达（DNS 解析失败），因此按书中表结构与画像
结论反向构造 900 张卡的模拟数据，固定随机种子 42。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RANDOM_SEED = 42
N_CARDS = 900
TYPE_COUNTS = {"普通卡": 540, "金卡": 270, "青年卡": 90}


def build_tables() -> dict[str, pd.DataFrame]:
    """构造 clients / disp / card / trans 四张表（一卡一账户一客户）。"""
    rng = np.random.default_rng(RANDOM_SEED)

    card_types = [t for t, n in TYPE_COUNTS.items() for _ in range(n)]
    card_types = [card_types[i] for i in rng.permutation(len(card_types))]

    # 发卡日期
    issued = pd.to_datetime("1994-01-01") + pd.to_timedelta(
        rng.integers(0, 1825, size=N_CARDS), unit="D")

    # 持卡年龄：青年卡集中在 20 岁，金卡与普通卡中位数接近
    age_at_card = np.where(
        np.array(card_types) == "青年卡",
        rng.normal(20.5, 2.2, N_CARDS),
        np.where(np.array(card_types) == "金卡",
                 rng.normal(42, 8, N_CARDS), rng.normal(40, 9, N_CARDS)),
    )
    age_at_card = np.clip(age_at_card, 18, 70)
    birth = issued - pd.to_timedelta(np.round(age_at_card * 365.25), unit="D")

    # 性别：金卡男性占比更高
    sex = []
    for t in card_types:
        p_male = 0.72 if t == "金卡" else 0.50
        sex.append(rng.choice(["男", "女"], p=[p_male, 1 - p_male]))
    clients = pd.DataFrame({
        "client_id": np.arange(1, N_CARDS + 1),
        "sex": sex,
        "birth_date": birth.strftime("%Y-%m-%d"),
    })

    disp = pd.DataFrame({
        "disp_id": np.arange(1, N_CARDS + 1),
        "client_id": np.arange(1, N_CARDS + 1),
        "account_id": np.arange(1, N_CARDS + 1),
        "type": "OWNER",
    })

    card = pd.DataFrame({
        "card_id": np.arange(1, N_CARDS + 1),
        "disp_id": np.arange(1, N_CARDS + 1),
        "type": card_types,
        "issued": issued.strftime("%Y-%m-%d"),
    })

    # 交易：每张卡在发卡前 2 年内有 8~20 笔，余额水平随卡类型分层
    balance_base = {"金卡": 62000, "普通卡": 36000, "青年卡": 12000}
    trans_rows = []
    tid = 1
    for i, t in enumerate(card_types):
        issue = issued[i]
        n = int(rng.integers(8, 21))
        # 一半交易落在发卡前 1 年内，保证 var3 窗口内有数据
        offsets = np.concatenate([
            rng.integers(1, 366, size=max(1, n // 2)),
            rng.integers(366, 731, size=n - max(1, n // 2)),
        ])
        offsets = offsets[rng.permutation(len(offsets))]
        dates = issue - pd.to_timedelta(offsets, unit="D")
        base = balance_base[t]
        balances = np.clip(rng.normal(base, base * 0.35, n), 500, None)
        amounts = np.round(rng.uniform(100, 8000, n), 2)
        types = rng.choice(["借", "贷"], size=n)
        # 发卡前一年窗口内至少各有一笔借、贷，避免贷借比分母为 0
        in_window = np.where(offsets <= 365)[0]
        if len(in_window) >= 2:
            types[in_window[0]], types[in_window[1]] = "借", "贷"
        for j in range(n):
            trans_rows.append({
                "trans_id": tid,
                "account_id": i + 1,
                "date": dates[j].strftime("%Y-%m-%d"),
                "type": types[j],
                "operation": rng.choice(["转入", "转出"]),
                "amount": float(amounts[j]),
                "balance": round(float(balances[j]), 2),
                "k_symbol": rng.choice(["房屋贷款", "租金", "保险", "其他"], p=[0.15, 0.25, 0.2, 0.4]),
                "bank": rng.choice(["AB", "CD", "EF", "GH"]),
                "account": rng.choice(["A", "B", "C"]),
            })
            tid += 1

    trans = pd.DataFrame(trans_rows)
    return {"clients": clients, "disp": disp, "card": card, "trans": trans}


def build_creditcard(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """pandas 复现教材 var1 / var2 / var3 三段取数逻辑。"""
    card, disp, clients, trans = (tables[k] for k in ["card", "disp", "clients", "trans"])

    # ---- var1：三表左连接 + 持卡年龄 ----
    var1 = (card.merge(disp[["disp_id", "client_id", "account_id"]], on="disp_id", how="left")
            .merge(clients[["client_id", "sex", "birth_date"]], on="client_id", how="left"))
    var1["issued"] = pd.to_datetime(var1["issued"])
    var1["birth_date"] = pd.to_datetime(var1["birth_date"])
    var1["age"] = (var1["issued"] - var1["birth_date"]).dt.days / 365.0

    # ---- var2：发卡前全部交易 → 最近交易间隔 + 平均余额 ----
    tr = trans.copy()
    tr["date"] = pd.to_datetime(tr["date"])
    pre = var1[["card_id", "account_id", "issued"]].merge(tr, on="account_id", how="left")
    pre = pre[pre["date"] < pre["issued"]]

    var2 = pre.groupby("card_id", as_index=False).agg(
        last_date=("date", "max"), balance=("balance", "mean"))
    var2 = var2.merge(var1[["card_id", "issued"]], on="card_id")
    var2["last_days"] = (var2["issued"] - var2["last_date"]).dt.days

    # ---- var3：发卡前 365 天 → 交易笔数、借/贷金额、出账比例 ----
    win = pre[pre["date"] >= pre["issued"] - pd.Timedelta(days=365)].copy()
    win["in_amount"] = np.where(win["type"] == "借", win["amount"], 0.0)
    win["out_amount"] = np.where(win["type"] == "贷", win["amount"], 0.0)

    var3 = win.groupby("card_id", as_index=False).agg(
        trans_count=("trans_id", "count"),
        trans_in_amount=("in_amount", "sum"),
        trans_out_amount=("out_amount", "sum"),
        avg_balance=("balance", "mean"),
    )
    var3["out_ratio"] = var3["trans_out_amount"] / var3["avg_balance"]
    var3["out_in_ratio"] = (var3["trans_out_amount"] / var3["trans_in_amount"]).replace(
        [np.inf, -np.inf], np.nan)

    # ---- 最终宽表 ----
    out = (var1[["card_id", "disp_id", "issued", "type", "sex", "age"]]
           .merge(var2[["card_id", "last_days", "balance"]], on="card_id", how="left")
           .merge(var3[["card_id", "trans_count", "trans_in_amount", "trans_out_amount",
                        "out_ratio", "out_in_ratio"]], on="card_id", how="left"))
    out["issued"] = out["issued"].dt.strftime("%Y-%m-%d")
    return out.sort_values("card_id").reset_index(drop=True)


if __name__ == "__main__":
    t = build_tables()
    print({k: v.shape for k, v in t.items()})
    cc = build_creditcard(t)
    print(cc.shape)
    print(cc.head())
