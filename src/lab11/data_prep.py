"""lab11 数据：信用卡日消费额（2013-03-03 ~ 2013-03-16，共 14 天）。

教材 10.3（PDF p303-307）用 Excel 演示"业务假设驱动的日度预测"：
先只用 2013-03-03 ~ 03-09 这一周的 7 天消费额预测下一周，
拿到下一周实际值后再滚动修正假设。

数据说明：教材正文已给出两周每日数值，本实验直接录入，不做模拟。
单位：万元（与教材口径一致）。
"""

from __future__ import annotations

import pandas as pd

# 第一周：建模样本（教材 p303-305 表格）
FIRST_WEEK = [
    ("2013-03-03", 183.49, ""),
    ("2013-03-04", 182.75, ""),
    ("2013-03-05", 174.73, ""),
    ("2013-03-06", 177.70, ""),
    ("2013-03-07", 177.08, ""),
    ("2013-03-08", 182.08, "妇女节当日"),
    ("2013-03-09", 239.16, "节后高峰"),
]

# 第二周：验证样本（教材 p306-307 表格）
SECOND_WEEK = [
    ("2013-03-10", 188.17, ""),
    ("2013-03-11", 191.31, ""),
    ("2013-03-12", 174.99, ""),
    ("2013-03-13", 175.14, ""),
    ("2013-03-14", 171.66, ""),
    ("2013-03-15", 174.31, ""),
    ("2013-03-16", 196.42, ""),
]

# 第一周预测值（教材 p305-306），用于逐日核对
BOOK_FORECAST = [182.77, 182.77, 176.50, 176.50, 176.50, 182.77, 210.62]

# 教材给出的妇女节效应（万元）
BOOK_HOLIDAY_EFFECT = 51.20


def build_frame() -> pd.DataFrame:
    """把两周数据整理成长表：date / weekday / actual / holiday_note / phase。"""
    rows = []
    for phase, block in (("首轮样本", FIRST_WEEK), ("验证周", SECOND_WEEK)):
        for ds, value, note in block:
            rows.append(
                {
                    "date": pd.to_datetime(ds),
                    "actual": float(value),
                    "holiday_note": note,
                    "phase": phase,
                }
            )
    df = pd.DataFrame(rows)
    df["weekday"] = df["date"].dt.day_of_week.map(
        {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
    )
    return df.sort_values("date").reset_index(drop=True)


if __name__ == "__main__":
    df = build_frame()
    print(df.to_string(index=False))
