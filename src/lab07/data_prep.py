"""lab07 数据：指标归因的三种拆解口径（教材 5.3.3 原值）。

教材给出两组确定数值，直接录入、不做模拟：

1. 加法拆解（变化量/变化率）
   上期：A1=2000、A2=5600、A3=1200、A4=1200，合计 12000
   本期：A1=2000、A2=4000、A3=1000、A4=1000，合计 10000

2. 乘法拆解（替换法与 LMDI）
   营收 = 订单数 × 单价
   上期：110 × 100 = 11000；本期：105 × 95 = 9975

3. 双因素法（比率指标）
   整体下单转化率 50% → 27%
   产品 1：40% → 20%，下单人数 500 → 1000
   产品 2：60% → 40%，下单人数 500 → 500
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# 加法案例（合计：上期 12000 → 本期 10000）
ADDITIVE_CASE = pd.DataFrame(
    {
        "指标": ["A1", "A2", "A3", "A4"],
        "上期值": [4000, 5600, 1200, 1200],
        "本期值": [4000, 4000, 1000, 1000],
    }
)

# 乘法案例
REVENUE_CASE = {
    "订单数": (110, 105),
    "单价": (100, 95),
}

# 双因素案例：产品、上期/本期比率、上期/本期下单人数
TWO_FACTOR_CASE = pd.DataFrame(
    {
        "产品": ["产品1", "产品2"],
        "上期转化率": [0.40, 0.60],
        "本期转化率": [0.20, 0.40],
        "上期下单人数": [500, 500],
        "本期下单人数": [1000, 500],
    }
)


def additive_decompose(df: pd.DataFrame = ADDITIVE_CASE) -> pd.DataFrame:
    """加/减法拆解：变化量贡献度与变化率贡献度。"""
    out = df.copy()
    out["增量"] = out["本期值"] - out["上期值"]
    total_prev = out["上期值"].sum()
    total_delta = out["增量"].sum()
    out["变化量贡献度"] = out["增量"] / total_delta
    out.loc[out["增量"] == 0, "变化量贡献度"] = 0.0
    out["变化率贡献度"] = out["增量"] / total_prev
    return out


def replacement_method() -> pd.DataFrame:
    """替换法：逐个因素用当期值、其余用上期值，计算对总指标增量的贡献。"""
    orders0, orders1 = REVENUE_CASE["订单数"]
    price0, price1 = REVENUE_CASE["单价"]
    y0, y1 = orders0 * price0, orders1 * price1
    delta = y1 - y0

    c_orders = orders1 * price0 - y0
    c_price = orders0 * price1 - y0

    # LMDI：用对数均值把乘法转成加法，贡献按对数增量占比分配
    ln_share_orders = (np.log(orders1) - np.log(orders0)) / (np.log(y1) - np.log(y0))
    ln_share_price = (np.log(price1) - np.log(price0)) / (np.log(y1) - np.log(y0))

    return pd.DataFrame(
        {
            "因素": ["订单数", "单价", "合计", "交互项（合计-实际）"],
            "替换法贡献": [c_orders, c_price, c_orders + c_price, delta - (c_orders + c_price)],
            "替换法占比": [c_orders / delta, c_price / delta, 1.0, 0.0],
            "LMDI贡献": [delta * ln_share_orders, delta * ln_share_price, delta, 0.0],
            "LMDI占比": [ln_share_orders, ln_share_price, 1.0, 0.0],
        }
    )


def two_factor_method() -> pd.DataFrame:
    """双因素法：波动贡献度 A + 结构贡献度 B = 整体贡献度 C。"""
    df = TWO_FACTOR_CASE.copy()
    p0_all = df["上期下单人数"].sum()
    p1_all = df["本期下单人数"].sum()
    x0_all = (df["上期转化率"] * df["上期下单人数"]).sum() / p0_all
    x1_all = (df["本期转化率"] * df["本期下单人数"]).sum() / p1_all

    df["上期占比"] = df["上期下单人数"] / p0_all
    df["本期占比"] = df["本期下单人数"] / p1_all
    # 波动贡献：自身比率变化 × 上期结构占比
    df["波动贡献A"] = (df["本期转化率"] - df["上期转化率"]) * df["上期占比"]
    # 结构贡献：结构占比变化 ×（自身本期比率 - 整体上期比率）
    df["结构贡献B"] = (df["本期占比"] - df["上期占比"]) * (df["本期转化率"] - x0_all)
    df["整体贡献C"] = df["波动贡献A"] + df["结构贡献B"]

    overall = pd.DataFrame(
        {
            "产品": ["总体"],
            "上期转化率": [x0_all],
            "本期转化率": [x1_all],
            "上期下单人数": [p0_all],
            "本期下单人数": [p1_all],
            "上期占比": [1.0],
            "本期占比": [1.0],
            "波动贡献A": [df["波动贡献A"].sum()],
            "结构贡献B": [df["结构贡献B"].sum()],
            "整体贡献C": [df["整体贡献C"].sum()],
        }
    )
    return pd.concat([df, overall], ignore_index=True)


if __name__ == "__main__":
    print(additive_decompose())
    print(replacement_method())
    print(two_factor_method())
