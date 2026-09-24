# -*- coding: utf-8 -*-
"""问题四补充图（精确枚举为主方案）：
1) 枚举 vs 局部搜索对比柱状图  2) 模拟退火收敛曲线  3) 枚举规模 Bell 数增长
"""
import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fig_style import set_style, save, PALETTE, C_MAIN, C_CMP

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
set_style()

enum = pd.read_csv(os.path.join(R, "q4_1_comparison.csv"), encoding="utf-8-sig")
ls = pd.read_csv(os.path.join(R, "q4_2_comparison.csv"), encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# 图 1：枚举 vs 局部搜索（K=2 / K=3），指标：总规模/均衡系数/缺口
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2))
pairs = [
    ("资源配置总规模", "资源配置总规模", axes[0]),
    ("工作量均衡系数", "工作量均衡系数", axes[1]),
    ("资源缺口", "资源缺口", axes[2]),
]
for (ek, lk, ax) in pairs:
    x = np.arange(2)
    w = 0.36
    e_vals = [enum.loc[enum["K"] == 2, ek].values[0], enum.loc[enum["K"] == 3, ek].values[0]]
    l_vals = [ls.loc[ls["K"] == 2, lk].values[0], ls.loc[ls["K"] == 3, lk].values[0]]
    b1 = ax.bar(x - w / 2, e_vals, w, label="精确枚举", color=C_MAIN, alpha=0.85)
    b2 = ax.bar(x + w / 2, l_vals, w, label="局部搜索", color=C_CMP, alpha=0.85)
    for b in list(b1) + list(b2):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                f"{b.get_height():g}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(["K=2", "K=3"])
    ax.set_title(ek)
fig.suptitle("问题四精确枚举 vs 局部搜索（K=2/3）", y=1.02)
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02))
fig.tight_layout()
save(fig, "q4_extra_01_枚举vs局部搜索.png")

# ---------------------------------------------------------------------------
# 图 2：模拟退火收敛曲线（scalar_score 与 gap）
# ---------------------------------------------------------------------------
hist = pd.read_csv(os.path.join(R, "q4_2_search_history.csv"), encoding="utf-8-sig")
fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2))
for K, c in [(2, C_MAIN), (3, C_CMP)]:
    sub = hist[hist["K"] == K]
    axes[0].plot(sub["iter"], sub["scalar_score"], lw=1.5, color=c,
                 label=f"K={K}")
    axes[1].plot(sub["iter"], sub["gap"], lw=1.5, color=c, label=f"K={K}")
axes[0].set_xlabel("迭代轮次")
axes[0].set_ylabel("标量得分")
axes[0].set_title("(a) 标量得分收敛")
axes[0].legend()
axes[1].set_xlabel("迭代轮次")
axes[1].set_ylabel("资源缺口")
axes[1].set_title("(b) 资源缺口收敛")
axes[1].legend()
fig.suptitle("问题四模拟退火局部搜索收敛过程", y=1.02)
fig.tight_layout()
save(fig, "q4_extra_02_SA收敛曲线.png")

# ---------------------------------------------------------------------------
# 图 3：无标签分区数（第二类 Stirling 数 S(13,K)）随 K 的增长
# ---------------------------------------------------------------------------
def S2(n, k):
    dp = [[0] * (k + 1) for _ in range(n + 1)]
    dp[0][0] = 1
    for i in range(1, n + 1):
        for j in range(1, min(i, k) + 1):
            dp[i][j] = j * dp[i - 1][j] + dp[i - 1][j - 1]
    return dp[n][k]

Ks = list(range(2, 8))
vals = [S2(13, k) for k in Ks]
fig, ax = plt.subplots(figsize=(6.0, 4.4))
ax.semilogy(Ks, vals, "o-", color=C_MAIN, lw=2, ms=6)
for k, v in zip(Ks, vals):
    ax.text(k, v * 1.5, f"{v:.0f}", ha="center", fontsize=8)
ax.axhline(261625, ls=":", color=C_CMP, lw=1)
ax.text(2.1, 261625 * 0.3, "K=3 已枚举 26.2 万", color=C_CMP, fontsize=8)
ax.set_xlabel("任务组数 K")
ax.set_ylabel("无标签分区数 S(13,K)（对数轴）")
ax.set_title("问题四精确枚举复杂度随 K 增长")
save(fig, "q4_extra_03_枚举复杂度.png")

print("fig_q4 done")
