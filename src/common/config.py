"""实验公共配置：路径、中文字体、图表与表格落盘。

所有实验脚本通过 `sys.path` 注入 src 目录后 `from common.config import ...` 使用，
保证无论从仓库根目录还是 lab 目录运行，输出路径都一致。
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")

# 仓库根目录（T/），本文件位于 T/src/common/config.py
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
OUT_FIG = BASE_DIR / "output" / "figures"
OUT_TAB = BASE_DIR / "output" / "tables"

# 教材图表风格：白底、弱网格、无多余边框
COLORS = ["#2E5C8A", "#D98C3F", "#4C9A6A", "#B23A48", "#7A6FA8", "#8C8C8C"]


def ensure_dirs() -> None:
    for d in (DATA_RAW, DATA_PROCESSED, OUT_FIG, OUT_TAB):
        d.mkdir(parents=True, exist_ok=True)


def setup_plot() -> None:
    """统一样式，并解决中文与负号显示。"""
    plt.rcParams.update(
        {
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "figure.dpi": 120,
            "savefig.dpi": 200,
            "savefig.bbox": "tight",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": "--",
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "figure.facecolor": "white",
        }
    )


def save_fig(fig: plt.Figure, name: str) -> Path:
    ensure_dirs()
    path = OUT_FIG / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def save_table(df: pd.DataFrame, name: str, index: bool = False) -> Path:
    ensure_dirs()
    path = OUT_TAB / f"{name}.csv"
    df.to_csv(path, index=index, encoding="utf-8-sig")
    return path
