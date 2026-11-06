"""lab10 数据：AirPassengers 月度航空客运量（1949-01 ~ 1960-12，144 条）。

教材 10.2 用 Power BI 的"效应分解法"演示时间序列的趋势/周期分解与预测，
数据为经典的 AirPassengers 数据集（DATE + AIR 两列）。

获取顺序：
1. 读取 data/raw/airline-passengers.csv（首次运行已缓存）；
2. 缺失时尝试从公开地址下载；
3. 仍失败则按"指数增长 + 振幅扩大的年度周期"生成同结构模拟数据（标注模拟）。
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
CSV_PATH = BASE_DIR / "data" / "raw" / "airline-passengers.csv"
URL = "https://raw.githubusercontent.com/jbrownlee/Datasets/master/airline-passengers.csv"


def _simulate(n: int = 144) -> pd.DataFrame:
    """回退方案：生成与 AirPassengers 同结构的模拟序列。"""
    rng = np.random.default_rng(42)
    months = pd.date_range("1949-01-01", periods=n, freq="MS")
    t = np.arange(n) / 12.0
    trend = 110 * np.exp(0.12 * t)
    seasonal = 1 + (0.10 + 0.02 * t) * np.sin(2 * np.pi * (months.month - 3) / 12)
    noise = rng.normal(0, 0.03, n)
    y = np.round(trend * seasonal * (1 + noise)).astype(int)
    return pd.DataFrame({"date": months, "passengers": y})


def load_airpassengers() -> tuple[pd.DataFrame, str]:
    """返回 (date/passengers 两列数据, 数据来源说明)。"""
    if not CSV_PATH.exists():
        CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            urllib.request.urlretrieve(URL, CSV_PATH)
        except Exception:
            return _simulate(), "网络不可达，按 AirPassengers 结构模拟"

    df = pd.read_csv(CSV_PATH)
    df.columns = ["date", "passengers"]
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True), f"公开数据 {CSV_PATH.name}"


if __name__ == "__main__":
    df, src = load_airpassengers()
    print(src, df.shape)
    print(df.head())
    print(df.tail())
