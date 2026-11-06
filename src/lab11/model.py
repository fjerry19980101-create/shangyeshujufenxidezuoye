"""lab11 模型：业务假设驱动的日度预测与滚动修正。

教材 10.3 的核心不是拟合一条回归曲线，而是把"日消费额"按业务规律分组：
同类日期的消费水平相近，用同类样本的均值作为预测，再根据新一周的实际值
更新（滚动修正）。本模块把这条规则显式化，便于与书中数值逐日核对。

五条业务假设（写入代码即作为模型口径）
--------------------------------------
H1 周日、周一、周五消费行为相近 → 归为"平稳日"；
H2 周二、周三、周四消费行为相近 → 归为"低谷日"；
H3 周六为消费高峰，周五是高峰前奏 → 用最近一个周五与周六的均值预测周六；
H4 节假日（妇女节）会抬高峰值，属于一次性事件，不进入常态基线；
H5 每周滚动：拿到新一周实际值后重估各分组均值，修正下一周预测。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# H1 / H2 / H3 的分组口径
GROUPS = {
    "周日": "平稳日",
    "周一": "平稳日",
    "周五": "平稳日",
    "周二": "低谷日",
    "周三": "低谷日",
    "周四": "低谷日",
    "周六": "高峰日",
}


def fit(df: pd.DataFrame) -> dict:
    """按业务假设估计各组的日消费水平。

    返回 group_means（平稳日/低谷日）与 peak（高峰日）三个基准值。
    高峰日不取历史全部周六的均值，而取"最近一个周五 + 最近一个周六"的均值，
    因为周五的消费会向周六延伸（H3）。
    """
    group_means = {
        g: float(df.loc[df["weekday"].map(GROUPS) == g, "actual"].mean())
        for g in ("平稳日", "低谷日")
    }

    friday = df.loc[df["weekday"] == "周五", "actual"]
    saturday = df.loc[df["weekday"] == "周六", "actual"]
    peak = float((friday.iloc[-1] + saturday.iloc[-1]) / 2)

    return {"group_means": group_means, "peak": peak}


def forecast(model: dict, weekdays: list[str]) -> np.ndarray:
    """按日期对应的分组给出预测值。"""
    out = []
    for wd in weekdays:
        group = GROUPS[wd]
        out.append(model["peak"] if group == "高峰日" else model["group_means"][group])
    return np.array(out, dtype=float)


def evaluate(actual, pred) -> dict:
    """误差指标：MAE、RMSE、MAPE（%）。"""
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    err = pred - actual
    return {
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err**2))),
        "MAPE": float(np.mean(np.abs(err / actual)) * 100),
        "BIAS": float(np.mean(err)),
    }


def detail(df: pd.DataFrame, pred) -> pd.DataFrame:
    """逐日对照表：实际、预测、误差、绝对百分比误差。"""
    out = df.copy()
    out["forecast"] = np.round(np.asarray(pred, dtype=float), 2)
    out["error"] = np.round(out["actual"] - out["forecast"], 2)
    out["abs_error"] = np.round(out["error"].abs(), 2)
    out["ape_pct"] = np.round(out["error"].abs() / out["actual"] * 100, 2)
    out["group"] = out["weekday"].map(GROUPS)
    return out


def holiday_effect(
    friday_forecast: float,
    next_friday_actual: float,
    holiday_saturday_actual: float,
    next_saturday_actual: float,
) -> dict:
    """妇女节效应（教材口径）。

    效应 = (本周五常态预测 - 下周实际) + (节后周六实际 - 下周周六实际)，
    即把"本周五、本周六相对下周同期的抬升"相加。
    """
    friday_part = friday_forecast - next_friday_actual
    saturday_part = holiday_saturday_actual - next_saturday_actual
    return {
        "周五抬升": round(friday_part, 2),
        "周六抬升": round(saturday_part, 2),
        "合计": round(friday_part + saturday_part, 2),
    }
