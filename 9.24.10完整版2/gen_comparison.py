# -*- coding: utf-8 -*-
"""生成全文模型方法对比总览图（2x2 多面板）。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

# 中文字体：SimSun
for fp in [r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\msyh.ttc"]:
    try:
        font_manager.fontManager.addfont(fp)
    except Exception:
        pass
plt.rcParams["font.sans-serif"] = ["SimSun", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 10.5

INK = "#1a1a2e"
BLUE = "#2c5f8a"
ORANGE = "#c96b16"
GREEN = "#1f7a5a"
MUTED = "#8a94a6"

fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.0))

# (a) 问题一：三方法收敛
ax = axes[0, 0]
methods = ["线性加权法", "Chebyshev妥协", "NSGA-II"]
N = [18, 18, 18]
E = [59.072, 59.072, 59.072]
x = np.arange(len(methods))
w = 0.38
b1 = ax.bar(x - w/2, N, w, color=BLUE, label="架次数 N")
b2 = ax.bar(x + w/2, [e/4 for e in E], w, color=ORANGE, label="能耗 E/4 (kWh/4)")
for r in b1:
    ax.text(r.get_x()+r.get_width()/2, r.get_height()+0.15, f"{int(r.get_height())}",
            ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(methods)
ax.set_ylabel("数值")
ax.set_title("(a) 问题一：三种方法收敛于同一方案", loc="left", fontsize=11, fontweight="bold")
ax.legend(frameon=False, fontsize=9)
ax.set_ylim(0, 22)
ax.grid(axis="y", alpha=0.3, ls="--")

# (b) 问题二：贪心 vs NSGA-II
ax = axes[0, 1]
labels = ["贪心合并(主)", "NSGA-II(对比)"]
sorties = [16, 29]
energy = [58.179, 82.777]
viol = [5, 0]
x = np.arange(2); w = 0.3
ax.bar(x - w, sorties, w, color=BLUE, label="架次数")
ax.bar(x, [e/3 for e in energy], w, color=ORANGE, label="能耗 E/3 (kWh/3)")
ax.bar(x + w, viol, w, color=GREEN, label="硬违约数")
for i, (s, v) in enumerate(zip(sorties, viol)):
    ax.text(x[i]-w, s+0.5, str(s), ha="center", fontsize=9)
    ax.text(x[i]+w, v+0.5, str(v), ha="center", fontsize=9, color=GREEN)
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel("数值")
ax.set_title("(b) 问题二：少架次节能 vs 严格可行", loc="left", fontsize=11, fontweight="bold")
ax.legend(frameon=False, fontsize=9)
ax.set_ylim(0, 33)
ax.grid(axis="y", alpha=0.3, ls="--")

# (c) 问题三：运输+中继架次构成
ax = axes[1, 0]
labels = ["贪心+中继(主)", "NSGA-II联合(对比)"]
transport = [16, 55]
relay = [13, 35]
x = np.arange(2); w = 0.38
ax.bar(x, transport, w, color=BLUE, label="运输架次")
ax.bar(x, relay, w, bottom=transport, color=ORANGE, label="中继架次")
for i in range(2):
    ax.text(x[i], transport[i]+relay[i]+1, f"{transport[i]+relay[i]}",
            ha="center", fontsize=9, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel("架次数")
ax.set_title("(c) 问题三：通信保障的架次代价", loc="left", fontsize=11, fontweight="bold")
ax.legend(frameon=False, fontsize=9)
ax.set_ylim(0, 100)
ax.grid(axis="y", alpha=0.3, ls="--")

# (d) 问题四：资源缺口对比
ax = axes[1, 1]
labels = ["完全枚举(精确)", "局部搜索(主)"]
gap_k2 = [1, 3]
gap_k3 = [1, 4]
x = np.arange(2); w = 0.38
ax.bar(x - w/2, gap_k2, w, color=BLUE, label="K=2 缺口")
ax.bar(x + w/2, gap_k3, w, color=ORANGE, label="K=3 缺口")
for i in range(2):
    ax.text(x[i]-w/2, gap_k2[i]+0.1, str(gap_k2[i]), ha="center", fontsize=9)
    ax.text(x[i]+w/2, gap_k3[i]+0.1, str(gap_k3[i]), ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel("资源缺口 (单位)")
ax.set_title("(d) 问题四：精确最优 vs 可扩展近似", loc="left", fontsize=11, fontweight="bold")
ax.legend(frameon=False, fontsize=9)
ax.set_ylim(0, 5)
ax.grid(axis="y", alpha=0.3, ls="--")

fig.suptitle("全文模型方法对比总览", fontsize=13, fontweight="bold", color=INK)
fig.tight_layout(rect=[0, 0, 1, 0.97])
fig.savefig("figures/14_模型方法对比总览.png", dpi=300, bbox_inches="tight", facecolor="white")
print("[saved] figures/14_模型方法对比总览.png")
