"""lab02 模拟数据：广告用户行为漏斗。

教材 2.1.2 给出的是各环节转化率，而非原始曝光明细，因此这里按教材口径构造
一条完整漏斗（触达 100 万人）：

    广告触达 1,000,000
      → 查看广告      10%（触达转化率）
      → 跳转商品介绍页 20%（跳转转化率）
      → 点击立即购买   60%（购买意愿转化率）
      → 购买成功       90%（购买转化率）
    总体转化率 = 1.08%

另构造"优化实施后"的漏斗（触达 20%、跳转 50%、购买意愿 60%、支付 86.7%），
总体转化率 5.2%，对应教材结尾"改进后整体转化率提升至 5.2%"。
"""

from __future__ import annotations

import pandas as pd

# 教材原始漏斗
BASELINE_TOUCH = 1_000_000
BASELINE_RATES = {
    "触达转化率": 0.10,
    "跳转转化率": 0.20,
    "购买意愿转化率": 0.60,
    "购买转化率": 0.90,
}

# 改进后漏斗（人数直接给定，反推各环节转化率）
IMPROVED_COUNTS = [1_000_000, 200_000, 100_000, 60_000, 52_000]

STAGE_NAMES = ["广告触达人数", "查看广告人数", "跳转商品介绍页人数", "点击立即购买人数", "购买成功人数"]
RATE_NAMES = ["—", "触达转化率", "跳转转化率", "购买意愿转化率", "购买转化率"]

# 行业参考值（教材 2.1.2）
INDUSTRY = pd.DataFrame(
    {
        "环节": ["触达转化率", "跳转转化率"],
        "本项目": [0.10, 0.20],
        "行业均值": [0.20, 0.50],
        "行业最高": [0.35, 0.65],
    }
)


def build_funnel() -> pd.DataFrame:
    """按教材转化率逐级计算原始漏斗。"""
    users = [BASELINE_TOUCH]
    for rate in BASELINE_RATES.values():
        users.append(int(round(users[-1] * rate)))
    return _to_frame(users)


def build_improved_funnel() -> pd.DataFrame:
    """改进实施后的漏斗（对应教材 5.2%）。"""
    return _to_frame(IMPROVED_COUNTS)


def _to_frame(users: list[int]) -> pd.DataFrame:
    rates = [None] + [users[i] / users[i - 1] for i in range(1, len(users))]
    return pd.DataFrame(
        {
            "环节": STAGE_NAMES,
            "人数": users,
            "环节转化率": rates,
            "累计转化率": [u / users[0] for u in users],
            "转化率名称": RATE_NAMES,
        }
    )


def scenario_table() -> pd.DataFrame:
    """优化情景：单因素提升与双因素提升。"""
    fixed = {"购买意愿转化率": 0.60, "购买转化率": 0.90}
    rows = [
        {"情景": "现状（教材原始）", "触达转化率": 0.10, "跳转转化率": 0.20, **fixed},
        {"情景": "仅跳转提升至行业均值", "触达转化率": 0.10, "跳转转化率": 0.50, **fixed},
        {"情景": "仅触达提升至行业均值", "触达转化率": 0.20, "跳转转化率": 0.20, **fixed},
        {"情景": "双提升（教材测算）", "触达转化率": 0.20, "跳转转化率": 0.50, **fixed},
    ]
    df = pd.DataFrame(rows)
    df["总体转化率"] = (
        df["触达转化率"] * df["跳转转化率"] * df["购买意愿转化率"] * df["购买转化率"]
    )
    return df


if __name__ == "__main__":
    f = build_funnel()
    print(f)
    print(scenario_table())
