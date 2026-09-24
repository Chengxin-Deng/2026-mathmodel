# -*- coding: utf-8 -*-
"""全文统一绘图样式：seaborn + matplotlib，宋体(SimSun)，DPI>=300，统一配色。"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

_BASE = os.path.dirname(os.path.abspath(__file__))
_FIG = os.path.join(_BASE, "figures")
os.makedirs(_FIG, exist_ok=True)

# 注册 Windows 系统宋体（含本地 ttf 兜底），避免方框乱码
for _fp in (r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\msyh.ttc",
            os.path.join(_BASE, "simsun.ttf"), os.path.join(_BASE, "SimHei.ttf")):
    if os.path.exists(_fp):
        try:
            fm.fontManager.addfont(_fp)
        except Exception:
            pass

# 统一调色板
PALETTE = sns.color_palette("Set2", 8)
C_MAIN = "#1f77b4"   # 主方案蓝
C_CMP = "#d62728"    # 对比方案红
C_GRN = "#2ca02c"
C_ORG = "#ff7f0e"


def set_style():
    # 注意：sns.set_theme 会重置 font.sans-serif，故字体设置须在其后
    sns.set_theme(style="whitegrid", context="notebook", palette="Set2")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["SimSun", "Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "legend.fontsize": 10,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
    })


def save(fig, name):
    out = os.path.join(_FIG, name)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("[saved]", name)
