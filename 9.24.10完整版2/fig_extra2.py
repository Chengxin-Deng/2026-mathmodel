# -*- coding: utf-8 -*-
"""第二组补充图（多样化）：
1) Q2 配送及时性分析  2) Q2 服务区送达时序热力图  3) Q3 通信覆盖构成
4) Q1 组批机型热力图  5) Q4 资源缺口热力图
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fig_style import set_style, save, C_MAIN, C_CMP

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
set_style()

# ---------------------------------------------------------------------------
# 1) Q2 配送及时性：迟到量分布（soft）+ 各服务区迟到量
# ---------------------------------------------------------------------------
bd = pd.read_csv(os.path.join(R, "q2_1_box_delivery.csv"), encoding="utf-8-sig")
bd["迟到量_s"] = (bd["实际送达时刻_s"] - bd["期望送达时间_s"]).clip(lower=0)

fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
type_order = sorted(bd["物资类型"].unique())
sns.violinplot(data=bd, x="物资类型", y="迟到量_s", order=type_order,
               inner="box", palette="Set2", cut=0, ax=axes[0])
axes[0].set_xlabel("物资类型")
axes[0].set_ylabel("迟到量 (s)")
axes[0].set_title("(a) 各物资类型迟到量分布")
axes[0].tick_params(axis="x", rotation=20)

svc_delay = bd.groupby("服务区编号")["迟到量_s"].mean().reindex(
    sorted(bd["服务区编号"].unique()))
axes[1].bar(svc_delay.index, svc_delay.values, color=C_MAIN, alpha=0.85)
axes[1].set_xlabel("服务区")
axes[1].set_ylabel("平均迟到量 (s)")
axes[1].set_title("(b) 各服务区平均迟到量")
axes[1].tick_params(axis="x", rotation=45)
fig.suptitle("问题二主方案配送及时性（软迟到，硬约束违反=0）", y=1.02)
fig.tight_layout()
save(fig, "q2_extra_06_配送及时性分析.png")

# ---------------------------------------------------------------------------
# 2) Q2 服务区 x 物资类型 平均送达时刻热力图
# ---------------------------------------------------------------------------
piv = bd.pivot_table(index="服务区编号", columns="物资类型",
                     values="实际送达时刻_s", aggfunc="mean")
piv = piv.reindex(sorted(piv.index))
fig, ax = plt.subplots(figsize=(7.2, 4.8))
sns.heatmap(piv, annot=True, fmt=".0f", cmap="YlOrRd", linewidths=0.5,
            cbar_kws={"label": "平均送达时刻 (s)"}, ax=ax)
ax.set_title("问题二主方案各服务区各物资平均送达时刻")
ax.set_ylabel("服务区")
ax.set_xlabel("物资类型")
save(fig, "q2_extra_07_服务区送达时序热力图.png")

# ---------------------------------------------------------------------------
# 3) Q3 通信覆盖构成（直连/中继/缺口）
# ---------------------------------------------------------------------------
cats = ["直连", "中继覆盖", "通信缺口"]
q32 = [3, 13, 0]      # 主方案（贪心+中继，16 条路线）
q31 = [20, 35, 0]     # 对比（NSGA-II 联合，55 条路线）
x = np.arange(len(cats)); w = 0.38
fig, ax = plt.subplots(figsize=(6.2, 4.4))
b1 = ax.bar(x - w/2, q32, w, label="主方案（16 条路线）", color=C_MAIN)
b2 = ax.bar(x + w/2, q31, w, label="对比（55 条路线）", color=C_CMP)
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width()/2, b.get_height(),
            str(int(b.get_height())), ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(cats)
ax.set_ylabel("路线数")
ax.set_title("问题三通信覆盖方式构成")
ax.legend(fontsize=9)
save(fig, "q3_extra_04_通信覆盖构成.png")

# ---------------------------------------------------------------------------
# 4) Q1 组批机型 x 服务区 批次数热力图
# ---------------------------------------------------------------------------
bt = pd.read_csv(os.path.join(R, "q1_21_batches.csv"), encoding="utf-8-sig")
piv = bt.pivot_table(index="服务区编号", columns="机型编号", values="批次编号",
                     aggfunc="count", fill_value=0)
for c in ["A", "B", "C"]:
    if c not in piv.columns:
        piv[c] = 0
piv = piv[["A", "B", "C"]].reindex(sorted(piv.index))
fig, ax = plt.subplots(figsize=(6.4, 4.8))
sns.heatmap(piv, annot=True, fmt="d", cmap="Blues", linewidths=0.5,
            cbar_kws={"label": "批次数"}, ax=ax)
ax.set_title("问题一组批方案机型—服务区批次数")
ax.set_ylabel("服务区")
ax.set_xlabel("机型")
save(fig, "q1_extra_04_组批机型热力图.png")

# ---------------------------------------------------------------------------
# 5) Q4 资源缺口热力图（枚举：资源 x K）
# ---------------------------------------------------------------------------
def load_res(f):
    df = pd.read_csv(os.path.join(R, f), encoding="utf-8-sig")
    g = df.groupby("资源")["K组总需求"].max().reset_index()
    g["库存"] = df.groupby("资源")["现有库存"].max().values
    g["缺口"] = (g["K组总需求"] - g["库存"]).clip(lower=0)
    return g.set_index("资源")["缺口"]

k2 = load_res("q4_1_resources_K2.csv")
k3 = load_res("q4_1_resources_K3.csv")
res = sorted(set(k2.index) | set(k3.index))
mat = pd.DataFrame({"K=2": [k2.get(r, 0) for r in res],
                    "K=3": [k3.get(r, 0) for r in res]}, index=res)
fig, ax = plt.subplots(figsize=(5.6, 4.4))
sns.heatmap(mat, annot=True, fmt="d", cmap="Reds", linewidths=0.5,
            cbar_kws={"label": "资源缺口"}, ax=ax)
ax.set_title("问题四精确枚举资源缺口（K=2/3）")
ax.set_ylabel("资源类型")
ax.set_xlabel("")
save(fig, "q4_extra_04_资源缺口热力图.png")

print("fig_extra2 done")
