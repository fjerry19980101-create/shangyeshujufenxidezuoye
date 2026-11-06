"""lab11 业务假设驱动的信用卡日消费额预测（Excel → Python）。

教材出处：第 10 章 10.3 时间序列预测（PDF p303-307，Excel 实现）

业务问题
--------
某银行只有 2013-03-03 ~ 03-09 这一周的信用卡日消费额，需要预测下一周
（03-10 ~ 03-16）的每日消费额，并在拿到实际值后滚动修正假设。
教材不使用复杂模型，而是先提出"哪几天消费行为相似"的业务假设，
再用同类日期的均值做预测，最后用实际值检验并修正。

Python 迁移
--------
- 分组规则、预测、误差、节日效应见 `model.py`；
- 首轮预测值与教材 p305-306 的 7 个预测值逐日核对（容差 0.01）；
- 妇女节效应按教材口径计算，核对书中 51.20；
- 用两周实际值滚动重估，给出 03-17 ~ 03-23 的修正预测。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common.config import COLORS, save_fig, save_table, setup_plot
from lab11.data_prep import BOOK_FORECAST, BOOK_HOLIDAY_EFFECT, build_frame
from lab11.model import GROUPS, detail, evaluate, fit, forecast, holiday_effect

TOL = 0.011


def plot_forecast(df: pd.DataFrame, week2: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.plot(df["date"], df["actual"], color=COLORS[0], lw=1.8, marker="o", label="实际消费额")
    ax.plot(
        week2["date"],
        week2["forecast"],
        color=COLORS[1],
        lw=1.6,
        ls="--",
        marker="s",
        label="首轮预测（仅用 03-03~03-09）",
    )
    ax.axvline(pd.Timestamp("2013-03-10"), color=COLORS[5], lw=1, ls=":")
    ax.text(
        pd.Timestamp("2013-03-10"),
        ax.get_ylim()[1],
        " 预测起点",
        va="top",
        fontsize=9,
        color=COLORS[5],
    )
    for ds, note in (("2013-03-08", "妇女节"), ("2013-03-09", "节后高峰")):
        ax.axvspan(
            pd.Timestamp(ds) - pd.Timedelta(hours=9),
            pd.Timestamp(ds) + pd.Timedelta(hours=9),
            color=COLORS[3],
            alpha=0.10,
        )
        ax.text(
            pd.Timestamp(ds),
            206,
            note,
            ha="center",
            va="center",
            rotation=90,
            fontsize=8,
            color=COLORS[3],
        )

    ax.set_title("信用卡日消费额：首轮预测与实际值（2013-03-03 ~ 03-16）")
    ax.set_ylabel("消费额（万元）")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.legend(loc="upper left", fontsize=9)
    save_fig(fig, "lab11_forecast")
    return ROOT


def plot_hypothesis(df: pd.DataFrame, model: dict) -> Path:
    """把三条分组假设画出来：同类日期的实际值围绕组均值波动。"""
    first = df[df["phase"] == "首轮样本"].copy()
    first["group"] = first["weekday"].map(GROUPS)

    labels = ["平稳日", "低谷日", "高峰日"]
    means = [
        model["group_means"]["平稳日"],
        model["group_means"]["低谷日"],
        model["peak"],
    ]
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    ax.bar(labels, means, color=[COLORS[0], COLORS[2], COLORS[1]], width=0.52, alpha=0.85)
    for i, m in enumerate(means):
        ax.text(i, m + 3, f"{m:.2f}", ha="center", fontsize=10, fontweight="bold")

    rng = np.random.default_rng(42)
    group_points = {
        "平稳日": first.loc[first["group"] == "平稳日", "actual"].to_numpy(),
        "低谷日": first.loc[first["group"] == "低谷日", "actual"].to_numpy(),
        # 高峰日均值 = 最近一个周五与周六的平均，因此散点画这两个日期
        "高峰日": np.array(
            [
                first.loc[first["weekday"] == "周五", "actual"].iloc[-1],
                first.loc[first["weekday"] == "周六", "actual"].iloc[-1],
            ]
        ),
    }
    for i, g in enumerate(labels):
        vals = group_points[g]
        ax.scatter(
            i + rng.uniform(-0.14, 0.14, len(vals)),
            vals,
            color="white",
            edgecolor=COLORS[3],
            s=36,
            zorder=3,
        )
    ax.set_ylim(150, 260)
    ax.set_title("首轮分组假设：同类日期的消费水平（白点为该组实际值）")
    ax.set_ylabel("消费额（万元）")
    save_fig(fig, "lab11_hypothesis")
    return ROOT


def plot_errors(first: pd.DataFrame, corrected: pd.DataFrame, m1: dict, m2: dict) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.4))
    x = np.arange(len(first))
    w = 0.38
    ax.bar(x - w / 2, first["abs_error"], width=w, color=COLORS[0], label=f"首轮 MAE={m1['MAE']:.2f}")
    ax.bar(
        x + w / 2,
        corrected["abs_error"],
        width=w,
        color=COLORS[1],
        label=f"修正后回看 MAE={m2['MAE']:.2f}",
    )
    ax.set_xticks(x, [f"{d:%m-%d}\n{w}" for d, w in zip(first["date"], first["weekday"])], fontsize=8.5)
    ax.set_title("第 2 周逐日绝对误差：首轮 vs 修正后回看")
    ax.set_ylabel("|实际 - 预测|（万元）")
    ax.legend(fontsize=9)
    save_fig(fig, "lab11_errors")
    return ROOT


def main() -> None:
    setup_plot()
    df = build_frame()

    first = df[df["phase"] == "首轮样本"].copy()
    week2 = df[df["phase"] == "验证周"].copy()

    # 1) 首轮：仅用第一周建模型，预测第二周
    model1 = fit(first)
    pred1 = forecast(model1, week2["weekday"].tolist())
    week2 = detail(week2, pred1)

    diff = np.abs(week2["forecast"].to_numpy() - np.array(BOOK_FORECAST))
    assert diff.max() < TOL, f"与教材预测值不符：{diff}"
    assert week2["forecast"].round(2).tolist() == BOOK_FORECAST

    m1 = evaluate(week2["actual"], week2["forecast"])

    # 2) 妇女节效应（教材口径）
    friday_forecast = float(week2.loc[week2["weekday"] == "周五", "forecast"].iloc[0])
    next_friday_actual = float(week2.loc[week2["weekday"] == "周五", "actual"].iloc[0])
    holiday_sat = float(first.loc[first["weekday"] == "周六", "actual"].iloc[0])
    next_sat = float(week2.loc[week2["weekday"] == "周六", "actual"].iloc[0])
    effect = holiday_effect(friday_forecast, next_friday_actual, holiday_sat, next_sat)
    assert abs(effect["合计"] - BOOK_HOLIDAY_EFFECT) < 0.02, effect

    # 3) 滚动修正：用两周实际值重估分组均值，预测第 3 周
    model2 = fit(df)
    pred2 = forecast(model2, week2["weekday"].tolist())
    corrected = detail(week2, pred2)
    m2 = evaluate(week2["actual"], corrected["forecast"])

    dates3 = pd.date_range("2013-03-17", periods=7, freq="D")
    wd3 = dates3.day_of_week.map(
        {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
    )
    pred3 = forecast(model2, wd3.tolist())
    week3 = pd.DataFrame(
        {
            "date": dates3,
            "weekday": wd3,
            "group": wd3.map(GROUPS),
            "forecast": np.round(pred3, 2),
        }
    )

    # 4) 落盘
    forecast_tbl = week2[
        ["date", "weekday", "group", "actual", "forecast", "error", "abs_error", "ape_pct", "holiday_note"]
    ].copy()
    forecast_tbl.insert(1, "phase", "验证周")
    save_table(forecast_tbl, "lab11_forecast")

    metrics_tbl = pd.DataFrame(
        [
            {"口径": "首轮（仅第1周训练，预测第2周）", **m1},
            {"口径": "修正后回看（含第2周实际值，样本内）", **m2},
        ]
    ).round(2)
    save_table(metrics_tbl, "lab11_metrics", index=False)

    save_table(week3, "lab11_week3_forecast")

    holiday_tbl = pd.DataFrame(
        [
            {"项目": "本周五（03-08）首轮预测", "数值": friday_forecast},
            {"项目": "下周五（03-15）实际", "数值": next_friday_actual},
            {"项目": "本周六（03-09）实际", "数值": holiday_sat},
            {"项目": "下周六（03-16）实际", "数值": next_sat},
            {"项目": "妇女节效应合计", "数值": effect["合计"]},
        ]
    )
    save_table(holiday_tbl, "lab11_holiday")

    # 5) 图
    plot_forecast(df, week2)
    plot_hypothesis(df, model1)
    plot_errors(week2, corrected, m1, m2)

    # 6) 控制台报告
    print("=" * 68)
    print("首轮分组基准：平稳日 {:.2f} | 低谷日 {:.2f} | 高峰日 {:.2f}".format(
        model1["group_means"]["平稳日"], model1["group_means"]["低谷日"], model1["peak"]
    ))
    print("-" * 68)
    print(week2[["date", "weekday", "group", "actual", "forecast", "error", "ape_pct"]].to_string(index=False))
    print("-" * 68)
    print(f"首轮误差：MAE={m1['MAE']:.2f}  RMSE={m1['RMSE']:.2f}  MAPE={m1['MAPE']:.2f}%  BIAS={m1['BIAS']:.2f}")
    print(f"妇女节效应：周五 {effect['周五抬升']:.2f} + 周六 {effect['周六抬升']:.2f} = {effect['合计']:.2f}")
    print("-" * 68)
    print("滚动修正后的分组基准：平稳日 {:.2f} | 低谷日 {:.2f} | 高峰日 {:.2f}".format(
        model2["group_means"]["平稳日"], model2["group_means"]["低谷日"], model2["peak"]
    ))
    print(f"修正后回看误差：MAE={m2['MAE']:.2f}  RMSE={m2['RMSE']:.2f}  MAPE={m2['MAPE']:.2f}%")
    print("-" * 68)
    print("第 3 周（03-17 ~ 03-23）修正预测：")
    print(week3.to_string(index=False))
    print("=" * 68)


if __name__ == "__main__":
    main()
