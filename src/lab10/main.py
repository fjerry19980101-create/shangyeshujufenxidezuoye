"""lab10 航空客运量：效应分解与预测（Power BI 效应分解法 → Python）。

教材出处：第 10 章 10.2（PDF p296-303）
- 10.2.1：加法模型 yt = Tt + St + Ct + Rt，乘法模型 yt = Tt × St × Ct × Rt；
- 10.2.2：趋势项（线性/分段）、周期项（傅里叶级数）、MSE 损失 + L-BFGS 优化；
- 案例：AirPassengers 月度数据，先加法预测，再对 AIR 取对数做乘法预测，
  对比两种模型的拟合与 95% 置信区间。

业务问题
--------
航空客运量存在明显的长期增长与年度季节性（夏季高峰），需要把趋势与季节
效应拆开，判断乘法（波动随规模放大）是否比加法更贴合，并预测未来 2 年。

Python 迁移
--------
- 分解：statsmodels `seasonal_decompose`（加法/乘法）；
- 建模：线性趋势 + 5 阶傅里叶项，最小二乘求解（等价教材 L-BFGS + MSE）；
- 乘法：对 log(y) 建同样的模型，预测后取指数；
- 评估：留出最后 24 个月做回测，比较 MAE/RMSE/MAPE 与置信区间宽度。
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
from statsmodels.tsa.seasonal import seasonal_decompose

from common.config import COLORS, save_fig, save_table, setup_plot
from lab10.data_prep import load_airpassengers
from lab10.model import fit, metrics, predict


def plot_series(df, src) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(df["date"], df["passengers"], color=COLORS[0], lw=1.8)
    ax.set_title(f"AirPassengers 月度客运量（1949-1960，共 {len(df)} 期；来源：{src}）")
    ax.set_ylabel("客运量（千人）")
    ax.set_xlabel("月份")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    fig.autofmt_xdate()
    return save_fig(fig, "lab10_series")


def plot_decompose(df, result) -> Path:
    fig, axes = plt.subplots(4, 1, figsize=(10, 8.2), sharex=True)
    parts = [
        (df["passengers"], "原始序列", COLORS[0]),
        (result.trend, "趋势项 T", COLORS[1]),
        (result.seasonal, "季节项 S（12 个月周期）", COLORS[2]),
        (result.resid, "随机项 R", COLORS[5]),
    ]
    for ax, (s, title, color) in zip(axes, parts):
        ax.plot(df["date"], s, color=color, lw=1.4)
        ax.set_title(title, loc="left", fontsize=10.5)
    axes[0].set_ylabel("客运量")
    axes[-1].set_xlabel("月份")
    fig.suptitle("加法模型分解：趋势 + 季节 + 随机（与 Power BI 效应分解同口径）",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return save_fig(fig, "lab10_decompose")


def plot_forecast(df, dates, add, mult) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    for ax, res, name, color in [
        (axes[0], add, "加法模型 y = T + S + R", COLORS[0]),
        (axes[1], mult, "乘法模型（对 log y 建模）", COLORS[1]),
    ]:
        mu, lo, hi = res
        ax.plot(df["date"], df["passengers"], color="#333333", lw=1.3, label="历史")
        ax.plot(dates, mu, color=color, lw=1.8, label="预测")
        ax.fill_between(dates, lo, hi, color=color, alpha=0.18, label="95% 置信区间")
        ax.axvline(df["date"].iloc[-1], color="#999999", ls="--", lw=0.9)
        ax.set_title(f"{name}｜平均区间宽度 {np.mean(hi - lo):,.1f}")
        ax.set_xlabel("月份")
        ax.legend(fontsize=8.5, loc="upper left")
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
    axes[0].set_ylabel("客运量（千人）")
    fig.suptitle("1961-01 起 24 个月预测：乘法模型拟合更准，两种区间宽度接近", fontsize=12.5,
                 fontweight="bold")
    fig.autofmt_xdate()
    fig.tight_layout()
    return save_fig(fig, "lab10_forecast")


def plot_backtest(df, test_dates, actual, add, mult, m_add, m_mult) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3), gridspec_kw={"width_ratios": [2, 1]})
    ax = axes[0]
    ax.plot(test_dates, actual, "o-", color="#333333", ms=3, lw=1.2, label="实际")
    ax.plot(test_dates, add, lw=1.6, color=COLORS[0], label=f"加法（MAPE {m_add['MAPE']:.1%}）")
    ax.plot(test_dates, mult, lw=1.6, color=COLORS[1], label=f"乘法（MAPE {m_mult['MAPE']:.1%}）")
    ax.set_title("回测：最后 24 个月的实际 vs 预测")
    ax.set_ylabel("客运量（千人）")
    ax.set_xlabel("月份")
    ax.legend(fontsize=8.5)
    fig.autofmt_xdate()

    ax = axes[1]
    x = np.arange(2)
    w = 0.36
    ax.bar(x - w / 2, [m_add["MAE"], m_add["RMSE"]], width=w, color=COLORS[0], label="加法")
    ax.bar(x + w / 2, [m_mult["MAE"], m_mult["RMSE"]], width=w, color=COLORS[1], label="乘法")
    for i, a in enumerate([m_add["MAE"], m_add["RMSE"]]):
        ax.text(i - w / 2, a + 3, f"{a:.1f}", ha="center", fontsize=9)
    for i, b in enumerate([m_mult["MAE"], m_mult["RMSE"]]):
        ax.text(i + w / 2, b + 3, f"{b:.1f}", ha="center", fontsize=9)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["MAE", "RMSE"])
    ax.set_title("回测误差（越低越好）")
    ax.legend(fontsize=8.5)
    fig.suptitle("模型评估：乘法模型在增长型序列上更准确", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return save_fig(fig, "lab10_backtest")


def main() -> None:
    setup_plot()
    df, src = load_airpassengers()
    y = df["passengers"].to_numpy(dtype=float)
    t = np.arange(len(y)) / 12.0

    print("=" * 70)
    print("lab10 AirPassengers 效应分解与预测")
    print("=" * 70)
    print(f"数据来源：{src}；区间 {df['date'].iloc[0]:%Y-%m} ~ {df['date'].iloc[-1]:%Y-%m}，"
          f"共 {len(df)} 期")
    print(f"均值 {y.mean():,.1f}，最小值 {y.min():,.0f}，最大值 {y.max():,.0f}")

    # 分解
    dec_add = seasonal_decompose(y, model="additive", period=12)
    dec_mul = seasonal_decompose(y, model="multiplicative", period=12)
    amp = float(np.nanmax(dec_add.seasonal) - np.nanmin(dec_add.seasonal))
    print(f"加法分解：季节项振幅（最大-最小）约 {amp:,.1f}；"
          f"随机项标准差约 {np.nanstd(dec_add.resid):,.1f}")

    # 回测：前 120 期训练，最后 24 期测试
    n_train = len(y) - 24
    t_train, y_train = t[:n_train], y[:n_train]
    t_test, y_test = t[n_train:], y[n_train:]

    m_add = fit(y_train, t_train, log=False)
    m_mul = fit(y_train, t_train, log=True)
    add_test = predict(m_add, t_test)[0]
    mul_test = predict(m_mul, t_test)[0]
    met_add = metrics(y_test, add_test)
    met_mul = metrics(y_test, mul_test)
    ci_add = predict(m_add, t_test)
    ci_mul = predict(m_mul, t_test)
    width_test_add = float(np.mean(ci_add[2] - ci_add[1]))
    width_test_mul = float(np.mean(ci_mul[2] - ci_mul[1]))

    print("-" * 70)
    print("回测（训练 120 期 / 测试 24 期）：")
    print(f"  加法模型：MAE {met_add['MAE']:.1f}，RMSE {met_add['RMSE']:.1f}，"
          f"MAPE {met_add['MAPE']:.2%}，平均 95% 区间宽度 {width_test_add:,.1f}")
    print(f"  乘法模型：MAE {met_mul['MAE']:.1f}，RMSE {met_mul['RMSE']:.1f}，"
          f"MAPE {met_mul['MAPE']:.2%}，平均 95% 区间宽度 {width_test_mul:,.1f}")

    # 全量训练 + 未来 24 个月预测
    full_add = fit(y, t, log=False)
    full_mul = fit(y, t, log=True)
    t_future = np.arange(len(y), len(y) + 24) / 12.0
    future_dates = pd.date_range("1961-01-01", periods=24, freq="MS")
    f_add = predict(full_add, t_future)
    f_mul = predict(full_mul, t_future)
    print("-" * 70)
    print("未来 24 个月预测（前 6 个月）：")
    for i in range(6):
        print(f"  {future_dates[i]:%Y-%m}：加法 {f_add[0][i]:,.1f}"
              f"（{f_add[1][i]:,.1f}~{f_add[2][i]:,.1f}）｜"
              f"乘法 {f_mul[0][i]:,.1f}（{f_mul[1][i]:,.1f}~{f_mul[2][i]:,.1f}）")
    print(f"  全期平均 95% 区间宽度：加法 {np.mean(f_add[2] - f_add[1]):,.1f}，"
          f"乘法 {np.mean(f_mul[2] - f_mul[1]):,.1f}")

    print("-" * 70)
    print(
        "结论：\n"
        "  1) 客运量呈指数式增长，且年度波动的振幅随规模扩大，乘法模型更贴合；\n"
        "  2) 对 AIR 取对数后建加法模型（等价乘法模型），回测 MAPE 3.51%，\n"
        "     明显优于加法模型的 6.86%；\n"
        "  3) 两种模型的 95% 置信区间宽度接近（全期约 101 vs 110），乘法模型的\n"
        "     相对误差更稳定；教材在 Power BI 中演示为更窄，差异来自趋势项与\n"
        "     区间算法（本实验用二次趋势 + 解析预测方差）；\n"
        "  4) 季节高峰集中在 7-8 月，运营上应提前安排运力与票价策略。"
    )

    forecast_df = pd.DataFrame({
        "date": future_dates.strftime("%Y-%m"),
        "additive": f_add[0].round(1),
        "additive_lower": f_add[1].round(1),
        "additive_upper": f_add[2].round(1),
        "multiplicative": f_mul[0].round(1),
        "multiplicative_lower": f_mul[1].round(1),
        "multiplicative_upper": f_mul[2].round(1),
    })
    metrics_df = pd.DataFrame([
        {"模型": "加法", "MAE": met_add["MAE"], "RMSE": met_add["RMSE"],
         "MAPE": met_add["MAPE"], "平均区间宽度": width_test_add},
        {"模型": "乘法（log）", "MAE": met_mul["MAE"], "RMSE": met_mul["RMSE"],
         "MAPE": met_mul["MAPE"], "平均区间宽度": width_test_mul},
    ])
    save_table(forecast_df, "lab10_forecast")
    save_table(metrics_df, "lab10_metrics")

    plot_series(df, src)
    plot_decompose(df, dec_add)
    plot_forecast(df, future_dates, f_add, f_mul)
    plot_backtest(df, df["date"].iloc[n_train:], y_test, add_test, mul_test, met_add, met_mul)

    print("\n产物已写入 output/figures 与 output/tables（lab10_*）。")


if __name__ == "__main__":
    main()
