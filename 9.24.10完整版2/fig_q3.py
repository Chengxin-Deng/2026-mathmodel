# -*- coding: utf-8 -*-
"""问题三补充图：
1) 能耗与架次流向 Sankey  2) 方法对比柱状图  3) 中继悬停高度与空间分布
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fig_style import set_style, save, PALETTE, C_MAIN, C_CMP

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
set_style()

# 主方案 q3_2（贪心+中继）：运输16+中继13=29架次，能耗67.387(运输58.179+中继9.208)
# 对比 q3_1（NSGA-II联合）：运输55+中继35=90架次，能耗135.639(运输110.856+中继24.782)
Q32 = dict(架次=29, 能耗=67.387, makespan=19379.4, 违约=18, 运=16, 中=13)
Q31 = dict(架次=90, 能耗=135.639, makespan=54352.2, 违约=12, 运=55, 中=35)

# ---------------------------------------------------------------------------
# 图 1：Sankey 流向图（能耗构成 + 架次构成）
# ---------------------------------------------------------------------------
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle


def mini_sankey(ax, source_label, targets, title):
    """极简桑基图：左侧一个源节点，右侧若干目标节点，按值成比例。"""
    total = sum(v for _, v, _ in targets)
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, total * 1.02)
    ax.axis("off")
    # 源节点（左）
    ax.add_patch(Rectangle((0.06, 0), 0.06, total, facecolor="0.35",
                           edgecolor="none", alpha=0.9))
    ax.text(0.03, total / 2, source_label, ha="center", va="center",
            fontsize=10, rotation=90)
    # 目标节点（右）自底向上堆叠
    acc = 0.0
    for label, v, c in targets:
        ax.add_patch(Rectangle((0.88, acc), 0.06, v, facecolor=c,
                               edgecolor="none", alpha=0.9))
        ax.text(0.945, acc + v / 2, label, ha="left", va="center", fontsize=10)
        # 流向带：源(右缘) -> 目标(左缘)，起点取源底部向上累计对应段
        s_top, s_bot = acc + v, acc
        verts = [
            (0.12, s_top), (0.5, s_top), (0.5, s_top), (0.88, s_top),
            (0.88, s_bot), (0.5, s_bot), (0.5, s_bot), (0.12, s_bot),
            (0.12, s_top),
        ]
        codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
                 Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
                 Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), facecolor=c, alpha=0.45,
                               edgecolor="none"))
        acc += v
    ax.set_title(title, pad=10)


fig = plt.figure(figsize=(11.0, 4.4))
ax1 = fig.add_subplot(1, 2, 1)
mini_sankey(ax1, "总能耗\n67.4 kWh",
            [("运输\n58.2 kWh", 58.179, C_MAIN), ("中继\n9.2 kWh", 9.208, C_CMP)],
            "(a) 能耗流向")
ax2 = fig.add_subplot(1, 2, 2)
mini_sankey(ax2, "总架次\n29",
            [("运输\n16 架次", 16, C_MAIN), ("中继\n13 架次", 13, C_CMP)],
            "(b) 架次流向")
fig.suptitle("问题三主方案能耗与架次流向", y=1.02)
save(fig, "q3_extra_01_能耗架次Sankey.png")

# ---------------------------------------------------------------------------
# 图 2：问题三两方法对比柱状图
# ---------------------------------------------------------------------------
metrics = [("架次数\n(运+中)", "架次"), ("总能耗(kWh)\n(运+中)", "能耗"),
           ("完成时间(s)", "makespan"), ("硬约束违约", "违约")]
fig, axes = plt.subplots(1, 4, figsize=(12.5, 4.2))
for ax, (label, key) in zip(axes, metrics):
    vals = [Q32[key], Q31[key]]
    bars = ax.bar(["主方案\n贪心+中继", "对比\nNSGA-II联合"], vals,
                  color=[C_MAIN, C_CMP], width=0.55, alpha=0.85)
    ax.set_title(label, fontsize=11)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:g}",
                ha="center", va="bottom", fontsize=8)
    ax.tick_params(axis="x", labelsize=8)
fig.suptitle("问题三两种方法结果对比", y=1.02)
fig.tight_layout()
save(fig, "q3_extra_02_方法对比柱状图.png")

# ---------------------------------------------------------------------------
# 图 3：中继悬停高度分布 + 悬停点空间分布
# ---------------------------------------------------------------------------
relay = pd.read_csv(os.path.join(R, "q3_1_relay_sorties.csv"), encoding="utf-8-sig")
fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
sns.histplot(relay["悬停AGL_m"], bins=12, color=C_MAIN, kde=True, ax=axes[0])
axes[0].set_xlabel("中继悬停离地高度 AGL (m)")
axes[0].set_ylabel("架次数")
axes[0].set_title("(a) 中继悬停高度分布")

sc = axes[1].scatter(relay["悬停经度"], relay["悬停纬度"], c=relay["悬停AGL_m"],
                     cmap="viridis", s=45, edgecolor="k", linewidth=0.4)
axes[1].set_xlabel("经度 (°)")
axes[1].set_ylabel("纬度 (°)")
axes[1].set_title("(b) 中继悬停点空间分布（色=高度）")
fig.colorbar(sc, ax=axes[1], shrink=0.8, label="AGL (m)")
fig.suptitle("问题三中继无人机悬停位置特征", y=1.02)
fig.tight_layout()
save(fig, "q3_extra_03_中继悬停特征.png")

print("fig_q3 done")
