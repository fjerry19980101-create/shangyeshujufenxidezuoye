"""lab03 模拟数据：线上超市 2017-2020 分省月度收入。

教材 3.4.1 只给出趋势结论（未附数据）：2017 年起年度收入持续增长；
2020 下半年增长放缓，9-11 月不理想、11 月出现负增长；11 月多个省份负增长；
四川省全年几乎每月负增长，7/9/11 月最差，原因是本地竞品冲击。

这里按上述结论反向构造"省份 × 月份"的面板数据（固定随机种子）：
- 2018 年同比约 +14%、2019 年约 +11%；
- 2020 年上半年同比 +6.5%~+9%，下半年快速回落，11 月全国同比转负；
- 四川全年同比为负，7/9/11 月跌幅最大；
- 另有 8 个省份在 2020 年 11 月同比为负，复现"多个省份负增长"。

数据为模拟还原，不代表平台真实业绩。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RANDOM_SEED = 2024
BASE_ANNUAL_REVENUE = 1_200_000.0  # 2017 年全国年度收入（万元）

# 省份及 2017 年收入权重（近似市场结构，合计归一化）
PROVINCE_WEIGHTS = {
    "广东": 11.0, "江苏": 9.0, "山东": 8.0, "浙江": 7.0, "河南": 5.0,
    "四川": 4.5, "北京": 4.0, "上海": 4.0, "湖北": 4.0, "湖南": 4.0,
    "河北": 3.5, "福建": 3.5, "安徽": 3.5, "辽宁": 3.0, "陕西": 2.5,
    "江西": 2.5, "重庆": 2.5, "广西": 2.0, "云南": 2.0, "山西": 2.0,
    "内蒙古": 1.5, "贵州": 1.5, "黑龙江": 1.5, "天津": 1.5, "吉林": 1.2,
    "新疆": 1.0, "甘肃": 0.8, "海南": 0.6, "宁夏": 0.4, "青海": 0.3,
    "西藏": 0.2,
}

# 月度季节指数（11 月双十一、12 月年末促销为高峰）
SEASONAL = {
    1: 0.92, 2: 0.85, 3: 0.95, 4: 0.98, 5: 1.02, 6: 1.05,
    7: 0.98, 8: 1.00, 9: 0.99, 10: 1.02, 11: 1.28, 12: 1.15,
}

# 2020 年常规省份的月度同比
DEFAULT_2020_YOY = {
    1: 0.090, 2: 0.085, 3: 0.080, 4: 0.075, 5: 0.070, 6: 0.065,
    7: 0.030, 8: 0.025, 9: 0.010, 10: 0.008, 11: 0.015, 12: 0.015,
}

# 2020 年 11 月同比为负的省份（叠加在默认值上）
NOV_DECLINE = {
    "重庆": -0.050, "云南": -0.045, "贵州": -0.060, "湖北": -0.055,
    "湖南": -0.040, "陕西": -0.065, "广西": -0.048, "山西": -0.052,
}

# 四川省 2020 年全年月度同比（全部为负，7/9/11 月最差）
SICHUAN_2020_YOY = {
    1: -0.020, 2: -0.025, 3: -0.030, 4: -0.040, 5: -0.050, 6: -0.060,
    7: -0.100, 8: -0.070, 9: -0.090, 10: -0.080, 11: -0.120, 12: -0.060,
}


def _season_factor(month: int) -> float:
    """季节指数归一化到全年合计 12。"""
    return SEASONAL[month] * 12 / sum(SEASONAL.values())


def build_panel() -> pd.DataFrame:
    """生成 省份 × 年月 的收入面板（按同月同比递推，保留季节波动）。"""
    rng = np.random.default_rng(RANDOM_SEED)
    total_weight = sum(PROVINCE_WEIGHTS.values())
    records = []

    for prov, weight in PROVINCE_WEIGHTS.items():
        base_month = BASE_ANNUAL_REVENUE * weight / total_weight / 12
        values = {}

        for month in range(1, 13):
            values[(2017, month)] = base_month * _season_factor(month) * rng.normal(1, 0.01)

        for year in (2018, 2019, 2020):
            for month in range(1, 13):
                if year == 2018:
                    yoy = 0.14 + rng.normal(0, 0.004)
                elif year == 2019:
                    yoy = 0.11 + rng.normal(0, 0.004)
                elif prov == "四川":
                    yoy = SICHUAN_2020_YOY[month] + rng.normal(0, 0.004)
                elif month == 11 and prov in NOV_DECLINE:
                    yoy = NOV_DECLINE[prov] + rng.normal(0, 0.004)
                else:
                    yoy = DEFAULT_2020_YOY[month] + rng.normal(0, 0.004)
                values[(year, month)] = values[(year - 1, month)] * (1 + yoy)

        for (year, month), revenue in values.items():
            records.append(
                {"省份": prov, "年份": year, "月份": month, "收入": revenue}
            )

    panel = pd.DataFrame(records)
    panel["日期"] = pd.to_datetime(dict(year=panel["年份"], month=panel["月份"], day=1))
    panel["收入"] = panel["收入"].round(2)
    return panel[["省份", "日期", "年份", "月份", "收入"]].sort_values(
        ["日期", "省份"], ignore_index=True
    )


def annual_revenue(panel: pd.DataFrame) -> pd.DataFrame:
    """年度收入与同比。"""
    annual = panel.groupby("年份", as_index=False)["收入"].sum()
    annual["同比"] = annual["收入"].pct_change()
    return annual


def yoy_by_month(panel: pd.DataFrame, year: int = 2020, province: str | None = None) -> pd.DataFrame:
    """指定年份的月度收入与同比（可按省份下钻）。"""
    df = panel if province is None else panel[panel["省份"] == province]
    cur = df[df["年份"] == year].groupby("月份")["收入"].sum()
    prev = df[df["年份"] == year - 1].groupby("月份")["收入"].sum()
    out = pd.DataFrame({"本月收入": cur, "去年同月收入": prev})
    out["同比"] = out["本月收入"] / out["去年同月收入"] - 1
    out.index.name = "月份"
    return out.reset_index()


def province_yoy(panel: pd.DataFrame, year: int = 2020, month: int = 11) -> pd.DataFrame:
    """指定年月各省份收入与同比。"""
    cur = panel[(panel["年份"] == year) & (panel["月份"] == month)].set_index("省份")["收入"]
    prev = panel[(panel["年份"] == year - 1) & (panel["月份"] == month)].set_index("省份")["收入"]
    out = pd.DataFrame({"本月收入": cur, "去年同月收入": prev})
    out["同比"] = out["本月收入"] / out["去年同月收入"] - 1
    return out.sort_values("同比").reset_index()


if __name__ == "__main__":
    p = build_panel()
    print(p.shape)
    print(annual_revenue(p))
    print(province_yoy(p).head(10))
