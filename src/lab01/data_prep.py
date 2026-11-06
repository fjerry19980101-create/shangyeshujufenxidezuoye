"""lab01 模拟数据生成：内容产品注册同期群与留存行为。

教材案例只给出结论（3 月 8 日免费注册活动新增 +32.5%，该群组次日留存 32%，
其他群组次日留存 44%），未附原始数据，因此这里按结论反向构造数据：

1. 2 月 1 日至 3 月 31 日，每日自然新增约 800 人（±5% 随机波动）；
2. 3 月 8 日活动日新增量 = 基线 × 1.325（即 +32.5%）；
3. 活动群组留存显著偏低：D1=32%、D3=22%、D5=17%、D7=14%；
   其他群组：D1=44%、D3=31%、D5=25%、D7=21%。

为了结果稳定可复现，不直接按概率抽样，而是对每个群组按"留存倾向分"排序后
取固定人数，使各群组的留存率精确命中设定值。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# 活动日与基线
ACTIVITY_DATE = pd.Timestamp("2024-03-08")
START_DATE = pd.Timestamp("2024-02-01")
END_DATE = pd.Timestamp("2024-03-31")
BASE_NEW_USERS = 800          # 自然日新增基线
ACTIVITY_LIFT = 0.325         # 活动带来的新增增幅
RANDOM_SEED = 42

# 留存率设定（观测日）
RETENTION_DAYS = (1, 3, 5, 7)
NORMAL_RATES = {1: 0.44, 3: 0.31, 5: 0.25, 7: 0.21}
ACTIVITY_RATES = {1: 0.32, 3: 0.22, 5: 0.17, 7: 0.14}


def build_cohort_users() -> pd.DataFrame:
    """生成用户表：user_id / register_date / 各观测日是否留存。"""
    rng = np.random.default_rng(RANDOM_SEED)
    dates = pd.date_range(START_DATE, END_DATE, freq="D")

    sizes = []
    for d in dates:
        if d == ACTIVITY_DATE:
            sizes.append(int(round(BASE_NEW_USERS * (1 + ACTIVITY_LIFT))))
        else:
            # ±5% 的自然波动
            sizes.append(int(round(BASE_NEW_USERS * rng.uniform(0.95, 1.05))))

    records = []
    uid = 1
    for d, n in zip(dates, sizes):
        rates = ACTIVITY_RATES if d == ACTIVITY_DATE else NORMAL_RATES
        # 每个用户一个"留存倾向分"，倾向分越低越可能留存
        tendency = rng.uniform(0, 1, size=n)
        order = np.argsort(tendency)
        flags = {}
        for day, rate in rates.items():
            k = int(round(n * rate))
            mask = np.zeros(n, dtype=bool)
            mask[order[:k]] = True
            flags[f"retained_d{day}"] = mask
        coh = pd.DataFrame(flags)
        coh.insert(0, "register_date", d)
        coh.insert(0, "user_id", range(uid, uid + n))
        uid += n
        records.append(coh)

    users = pd.concat(records, ignore_index=True)
    users["register_date"] = pd.to_datetime(users["register_date"])
    return users


def cohort_size(users: pd.DataFrame) -> pd.DataFrame:
    """各注册日新增人数。"""
    return (
        users.groupby("register_date")
        .size()
        .reset_index(name="new_users")
        .sort_values("register_date")
    )


def cohort_retention(users: pd.DataFrame) -> pd.DataFrame:
    """各注册日群组在 D1/D3/D5/D7 的留存率（宽表）。"""
    out = users.groupby("register_date")[
        [f"retained_d{d}" for d in RETENTION_DAYS]
    ].mean()
    out.columns = [f"D{d}" for d in RETENTION_DAYS]
    return out.sort_index()


if __name__ == "__main__":
    u = build_cohort_users()
    print(u.shape)
    print(cohort_size(u).tail())
