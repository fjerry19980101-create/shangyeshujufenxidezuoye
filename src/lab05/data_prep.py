"""lab05 模拟数据：电商平台购买客户画像 + 营销 A/B 测试。

教材 3.5.2 已给出画像结论（女性占 60%；女性中 50 岁以上占 36%；50 岁以上
女性主要购买服饰与护肤品），未附原始订单数据。这里按这些比例构造订单表：

- 12,000 名购买客户，女性 7,200（60%）、男性 4,800（40%）；
- 女性年龄分布：18-25 岁 17%、26-35 岁 20%、36-49 岁 27%、50 岁以上 36%；
- 50 岁以上女性品类：服饰 40%、护肤品 30%、食品 12%、电子产品 10%、家居 8%；
- 50 岁以上女性支付方式：支付宝 45%、银行卡 30%、微信 25%。

A/B 测试按教材要求构造：
- 测试组：50 岁以上女性 + 购买服饰/护肤品；
- 对照组：50 岁以上女性 + 购买其他品类；
- 两组规模相同（各 777 人），指标为参与人数、参与率、转化人数、转化率、
  新增用户数、新增活跃用户数。

数据为模拟还原，不代表平台真实交易。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RANDOM_SEED = 2024
TOTAL_CUSTOMERS = 12_000

FEMALE_AGE_COUNTS = {
    "18-25岁": 1224,
    "26-35岁": 1440,
    "36-49岁": 1944,
    "50岁以上": 2592,
}
MALE_AGE_COUNTS = {
    "18-25岁": 1056,
    "26-35岁": 1440,
    "36-49岁": 1344,
    "50岁以上": 960,
}
AGE_RANGES = {
    "18-25岁": (18, 25),
    "26-35岁": (26, 35),
    "36-49岁": (36, 49),
    "50岁以上": (50, 65),
}

# 50 岁以上女性品类分布（合计 2592）
CATEGORY_50F = {
    "服饰": 1037,
    "护肤品": 778,
    "食品": 311,
    "电子产品": 259,
    "家居": 207,
}
TARGET_CATEGORIES = ("服饰", "护肤品")

# A/B 测试行为参数（人数由组规模换算，保证两组可比）
AB_FLAGS = {
    "测试组": {"participants": 272, "converters": 33, "new_users": 25, "new_active": 18},
    "对照组": {"participants": 23, "converters": 2, "new_users": 8, "new_active": 5},
}


def _age_list(counts: dict[str, int], rng: np.random.Generator) -> list[tuple[int, str]]:
    out = []
    for group, n in counts.items():
        low, high = AGE_RANGES[group]
        ages = rng.integers(low, high + 1, size=n)
        out.extend((int(a), group) for a in ages)
    return out


def build_orders() -> pd.DataFrame:
    """生成购买客户订单表（一人一单，便于画像统计）。"""
    rng = np.random.default_rng(RANDOM_SEED)

    female_ages = _age_list(FEMALE_AGE_COUNTS, rng)
    male_ages = _age_list(MALE_AGE_COUNTS, rng)

    # 50 岁以上女性：品类、支付方式按教材分布精确配比后打乱
    cat_pool = [c for c, n in CATEGORY_50F.items() for _ in range(n)]
    cat_pool = [cat_pool[i] for i in rng.permutation(len(cat_pool))]
    pay_pool = ["支付宝"] * 1166 + ["银行卡"] * 778 + ["微信支付"] * 648
    pay_pool = [pay_pool[i] for i in rng.permutation(len(pay_pool))]
    cat_iter, pay_iter = iter(cat_pool), iter(pay_pool)

    rows = []
    uid = 1

    # 女性：50 岁以上按教材品类分布，其余按一般分布
    for age, group in female_ages:
        if group == "50岁以上":
            cat = next(cat_iter)
            pay = next(pay_iter)
            amount = float(rng.normal({"支付宝": 180, "银行卡": 245, "微信支付": 320}[pay], 40))
        else:
            cat = rng.choice(["服饰", "护肤品", "食品", "电子产品", "家居"],
                             p=[0.30, 0.20, 0.20, 0.15, 0.15])
            pay = rng.choice(["支付宝", "银行卡", "微信支付"], p=[0.55, 0.20, 0.25])
            amount = float(rng.normal(150, 55))
        rows.append(_row(uid, "女", age, group, cat, pay, amount, rng))
        uid += 1

    # 男性
    for age, group in male_ages:
        cat = rng.choice(["服饰", "护肤品", "食品", "电子产品", "家居"],
                         p=[0.20, 0.10, 0.15, 0.35, 0.20])
        pay = rng.choice(["支付宝", "银行卡", "微信支付"], p=[0.50, 0.25, 0.25])
        amount = float(rng.normal(190, 70))
        rows.append(_row(uid, "男", age, group, cat, pay, amount, rng))
        uid += 1

    return pd.DataFrame(rows)


def _row(uid, sex, age, group, category, payment, amount, rng) -> dict:
    return {
        "客户ID": f"C{uid:05d}",
        "性别": sex,
        "年龄": age,
        "年龄段": group,
        "消费品类": category,
        "支付方式": payment,
        "消费金额": round(max(amount, 20), 2),
        "下单日期": pd.Timestamp("2024-05-01") + pd.Timedelta(days=int(rng.integers(0, 31))),
    }


def _assign_flags(df: pd.DataFrame, cfg: dict, rng: np.random.Generator) -> pd.DataFrame:
    """按目标人数标记参与、转化、新增、新增活跃（倾向分排序取前 k 个）。"""
    out = df.copy()
    n = len(out)

    def take(k: int) -> np.ndarray:
        order = np.argsort(rng.uniform(size=n))
        mask = np.zeros(n, dtype=bool)
        mask[order[:k]] = True
        return mask

    out["参与"] = take(cfg["participants"])
    # 转化仅发生在参与用户中
    idx = np.where(out["参与"].values)[0]
    sub_order = idx[np.argsort(rng.uniform(size=len(idx)))]
    out["转化"] = False
    out.iloc[sub_order[: cfg["converters"]], out.columns.get_loc("转化")] = True
    out["新增用户"] = take(cfg["new_users"])
    # 新增活跃从新增用户中取
    new_idx = np.where(out["新增用户"].values)[0]
    act_order = new_idx[np.argsort(rng.uniform(size=len(new_idx)))]
    out["新增活跃"] = False
    out.iloc[act_order[: cfg["new_active"]], out.columns.get_loc("新增活跃")] = True
    return out


def build_ab_test(orders: pd.DataFrame) -> pd.DataFrame:
    """构造等规模测试组/对照组，并挂上活动行为标记。"""
    rng = np.random.default_rng(RANDOM_SEED + 1)
    target = orders[
        (orders["性别"] == "女")
        & (orders["年龄段"] == "50岁以上")
        & (orders["消费品类"].isin(TARGET_CATEGORIES))
    ]
    control_pool = orders[
        (orders["性别"] == "女")
        & (orders["年龄段"] == "50岁以上")
        & (~orders["消费品类"].isin(TARGET_CATEGORIES))
    ]

    n = min(len(target), len(control_pool))
    test = target.sample(n=n, random_state=RANDOM_SEED).copy()
    control = control_pool.sample(n=n, random_state=RANDOM_SEED + 2).copy()

    test = _assign_flags(test, AB_FLAGS["测试组"], rng)
    control = _assign_flags(control, AB_FLAGS["对照组"], rng)
    test["分组"], control["分组"] = "测试组", "对照组"
    return pd.concat([test, control], ignore_index=True)


def ab_metrics(ab: pd.DataFrame) -> pd.DataFrame:
    """计算教材要求的六项活动评估指标。"""
    rows = []
    for group in ("测试组", "对照组"):
        g = ab[ab["分组"] == group]
        participants = int(g["参与"].sum())
        converters = int(g["转化"].sum())
        new_users = int(g["新增用户"].sum())
        new_active = int(g["新增活跃"].sum())
        rows.append(
            {
                "分组": group,
                "组人数": len(g),
                "活动参与人数": participants,
                "参与率": participants / len(g),
                "转化人数": converters,
                "转化率": converters / participants if participants else 0.0,
                "新增用户数": new_users,
                "新增活跃用户数": new_active,
                "新增活跃率": new_active / new_users if new_users else 0.0,
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    o = build_orders()
    print(o.shape, o["性别"].value_counts(normalize=True).round(3).to_dict())
    ab = build_ab_test(o)
    print(ab_metrics(ab))
