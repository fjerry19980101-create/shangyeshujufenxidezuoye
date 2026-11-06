"""lab10 模型：傅里叶周期项 + 线性趋势的加法/乘法效应分解预测。

教材 10.2 的效应分解法把序列写成 趋势 + 周期 + 随机：
- 加法模型  y = T + S + R
- 乘法模型  y = T × S × R（实际用对数变成 log y = log T + log S + log R）

做法与 Power BI 演示一致：趋势用线性项，周期用傅里叶级数（月度数据年度周期，
取 K=5 阶），用最小二乘（等价于教材的 MSE + L-BFGS 优化）求解；
预测区间按残差标准差与设计矩阵计算 95% 置信区间。
"""

from __future__ import annotations

import numpy as np

PERIOD = 12  # 月度数据的年度周期（12 个月）
K = 5        # 傅里叶阶数


def _design(t: np.ndarray) -> np.ndarray:
    """t 以"年"为单位：截距 + 二次趋势 + 年度傅里叶项。"""
    cols = [np.ones_like(t), t, t ** 2]
    for k in range(1, K + 1):
        cols.append(np.sin(2 * np.pi * k * t))
        cols.append(np.cos(2 * np.pi * k * t))
    return np.column_stack(cols)


def fit(y: np.ndarray, t: np.ndarray, log: bool = False) -> dict:
    z = np.log(y) if log else y
    X = _design(t)
    beta, *_ = np.linalg.lstsq(X, z, rcond=None)
    resid = z - X @ beta
    dof = max(len(z) - X.shape[1], 1)
    sigma = float(np.sqrt(np.sum(resid ** 2) / dof))
    xtx_inv = np.linalg.pinv(X.T @ X)
    return {"beta": beta, "sigma": sigma, "xtx_inv": xtx_inv,
            "log": log, "resid": resid}


def predict(model: dict, t: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """返回 (点预测, 95% 下界, 95% 上界)，已变换回原始量纲。"""
    X = _design(t)
    mu = X @ model["beta"]
    se = model["sigma"] * np.sqrt(1 + np.einsum("ij,jk,ik->i", X, model["xtx_inv"], X))
    lo, hi = mu - 1.96 * se, mu + 1.96 * se
    if model["log"]:
        return np.exp(mu), np.exp(lo), np.exp(hi)
    return mu, lo, hi


def metrics(actual: np.ndarray, pred: np.ndarray) -> dict:
    err = pred - actual
    return {
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "MAPE": float(np.mean(np.abs(err / actual))),
    }
