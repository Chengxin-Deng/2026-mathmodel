# -*- coding: utf-8 -*-
"""问题一补充图：支付表雷达图、qmax 小提琴图、数据相关性热力图。"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fig_style import set_style, save, PALETTE, C_MAIN, C_CMP

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
set_style()

qmax = pd.read_csv(os.path.join(R, "q1_1_qmax.csv"), encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# 图 1：支付表雷达图（三个单目标最优解 + 妥协解，逐维归一化）
# ---------------------------------------------------------------------------
# 支付表（q1_22_summary）: minN->(18,59.105,32807.7) minE->(19,58.975,34463.8) minT->(18,59.125,32801.7)
# 妥协解: (18, 59.072, 32801.7)
pay = {
    "单独最小化架次N": (18, 59.105, 32807.7),
    "单独最小化能耗E": (19, 58.975, 34463.8),
    "单独最小化时间T": (18, 59.125, 32801.7),
    "妥协解(等权)":     (18, 59.072, 32801.7),
}
# 归一化到 [0,1]，1 = 该维最优；N、E、T 均越小越优
Nlo, Nhi = 18, 19
Elo, Ehi = 58.975, 59.125
Tlo, Thi = 32801.7, 34463.8
def norm(v):
    n, e, t = v
    return [(Nhi - n) / (Nhi - Nlo), (Ehi - e) / (Ehi - Elo), (Thi - t) / (Thi - Tlo)]

labels = ["架次数 $N$", "总能耗 $E$", "累计时间 $T$"]
angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
angles += angles[:1]

fig = plt.figure(figsize=(6.2, 5.4))
ax = plt.subplot(111, polar=True)
colors = [C_MAIN, C_CMP, "#2ca02c", "#ff7f0e"]
for (name, v), c in zip(pay.items(), colors):
    vals = norm(v) + norm(v)[:1]
    ax.plot(angles, vals, "o-", color=c, lw=2, label=name)
    ax.fill(angles, vals, color=c, alpha=0.06)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(labels, fontsize=12)
ax.set_ylim(0, 1.05)
ax.set_yticks([0.25, 0.5, 0.75, 1.0])
ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=8, color="grey")
ax.set_rlabel_position(30)
ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.12), fontsize=9)
ax.set_title("问题一支付表与妥协解目标空间位置", pad=20)
save(fig, "q1_extra_01_支付表雷达图.png")

# ---------------------------------------------------------------------------
# 图 2：三种机型最大安全载荷小提琴图
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.0, 4.6))
order = ["A", "B", "C"]
sns.violinplot(data=qmax, x="机型编号", y="q_max_kg", order=order,
               inner="box", palette=["#1f77b4", "#2ca02c", "#ff7f0e"],
               linewidth=1.2, ax=ax, cut=0)
sns.stripplot(data=qmax, x="机型编号", y="q_max_kg", order=order,
              color="0.2", size=4, alpha=0.6, ax=ax)
ax.set_xlabel("机型")
ax.set_ylabel("最大安全载荷 $q_{\\max}$ (kg)")
ax.set_title("三种机型最大安全载荷分布")
# 标注均值
for i, g in enumerate(order):
    m = qmax[qmax["机型编号"] == g]["q_max_kg"].mean()
    ax.text(i, m + 2, f"均值 {m:.1f}", ha="center", fontsize=9, color="0.15")
save(fig, "q1_extra_02_qmax小提琴图.png")

# ---------------------------------------------------------------------------
# 图 3：数据特征相关性热力图
# ---------------------------------------------------------------------------
cols = ["水平距离_m", "巡航海拔_m", "q_max_kg", "往返总能耗_kWh_at_qmax"]
corr = qmax[cols].corr()
fig, ax = plt.subplots(figsize=(5.6, 4.6))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
            vmin=-1, vmax=1, square=True, linewidths=0.5,
            cbar_kws={"shrink": 0.8}, ax=ax,
            xticklabels=["水平距离", "巡航海拔", "最大载荷", "往返能耗"],
            yticklabels=["水平距离", "巡航海拔", "最大载荷", "往返能耗"])
ax.set_title("问题一关键变量相关系数")
save(fig, "q1_extra_03_相关性热力图.png")

print("fig_q1 done")
