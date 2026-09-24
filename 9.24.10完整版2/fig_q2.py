# -*- coding: utf-8 -*-
"""问题二补充图（NSGA-II 为主方案）：
1) 逐箱送达时刻（strip + ECDF）  2) NSGA-II 收敛曲线  3) 方法对比柱状图
4) 电池利用率堆叠图             5) 四目标 Pareto 三维散点
"""
import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fig_style import set_style, save, PALETTE, C_MAIN, C_CMP

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
set_style()

# 主方案（NSGA-II）与对比方案（贪心）的汇总值（来自 *_summary.txt）
NSGA = dict(架次=29, 能耗=82.777, makespan=16683.6, 违约=0)
GREEDY = dict(架次=16, 能耗=58.179, makespan=10173.7, 违约=5)

# ---------------------------------------------------------------------------
# 图 1：逐箱送达时刻（(a) 按服务区分组 strip；(b) 送达时刻 ECDF）
# ---------------------------------------------------------------------------
bd = pd.read_csv(os.path.join(R, "q2_1_box_delivery.csv"), encoding="utf-8-sig")
svc_order = sorted(bd["服务区编号"].unique())

fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))

# (a) strip by 服务区
sns.stripplot(data=bd, x="服务区编号", y="实际送达时刻_s", hue="物资类型",
              order=svc_order, palette="Set2", size=4, jitter=0.25, ax=axes[0])
axes[0].axhline(NSGA["makespan"], ls="--", color="0.3", lw=1)
axes[0].text(14, NSGA["makespan"] + 500, f"完成时间 {NSGA['makespan']:.0f}s",
             ha="right", fontsize=8, color="0.3")
axes[0].set_xlabel("服务区")
axes[0].set_ylabel("实际送达时刻 (s)")
axes[0].set_title("(a) 逐箱送达时刻（按服务区）")
axes[0].tick_params(axis="x", rotation=45)
axes[0].legend(fontsize=7, ncol=2, loc="upper left")

# (b) ECDF（手写经验累积分布）
arr = np.sort(bd["实际送达时刻_s"].values)
axes[1].step(arr, np.arange(1, len(arr) + 1) / len(arr), where="post",
             color=C_MAIN, lw=2, label="实际送达 ECDF")
exp = bd["期望送达时间_s"].dropna().values
if len(exp):
    axes[1].axvline(np.median(exp), ls=":", color=C_CMP, lw=1.5,
                    label=f"期望送达中位数 {np.median(exp):.0f}s")
axes[1].set_xlabel("送达时刻 (s)")
axes[1].set_ylabel("累计比例")
axes[1].set_title("(b) 逐箱送达时刻经验累积分布 (ECDF)")
axes[1].legend(fontsize=9)
fig.suptitle("问题二主方案（NSGA-II，29 架次）逐箱送达时刻", y=1.02)
save(fig, "q2_extra_01_逐箱送达时刻.png")

# ---------------------------------------------------------------------------
# 图 2：NSGA-II 收敛曲线（从 run.log 解析）
# ---------------------------------------------------------------------------
log_path = os.path.join(R, "q2_1_run.log")
gens, feas = [], []
with open(log_path, encoding="utf-8") as f:
    for line in f:
        m = re.search(r"gen\s+(\d+)/(\d+)\]\s+用时=.*?可行解=(\d+)/(\d+)", line)
        if m and int(m.group(2)) == 80:  # 仅正式 80 代
            gens.append(int(m.group(1)))
            feas.append(int(m.group(3)) / int(m.group(4)))

fig, ax = plt.subplots(figsize=(6.0, 4.2))
ax.plot(gens, [v * 100 for v in feas], "o-", color=C_MAIN, lw=2, ms=3)
ax.set_xlabel("进化代数")
ax.set_ylabel("种群可行解占比 (%)")
ax.set_title("问题二 NSGA-II 收敛过程（可行解占比）")
ax.grid(alpha=0.3)
ax.annotate("第 25 代全部可行", xy=(25, 100), xytext=(12, 70),
            arrowprops=dict(arrowstyle="->", color="0.3"), fontsize=9)
save(fig, "q2_extra_02_NSGA2收敛曲线.png")

# ---------------------------------------------------------------------------
# 图 3：问题二两方法对比柱状图（架次/能耗/makespan/违约）
# ---------------------------------------------------------------------------
metrics = [("架次数", "架次"), ("总能耗(kWh)", "能耗"), ("完成时间(s)", "makespan"),
           ("硬约束违约", "违约")]
fig, axes = plt.subplots(1, 4, figsize=(12.5, 4.2))
for ax, (label, key) in zip(axes, metrics):
    vals = [GREEDY[key], NSGA[key]]
    bars = ax.bar(["贪心构造\n(16架次)", "NSGA-II\n(29架次)"], vals,
                  color=[C_CMP, C_MAIN], width=0.55, alpha=0.85)
    ax.set_title(label)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:g}",
                ha="center", va="bottom", fontsize=9)
    ax.tick_params(axis="x", labelsize=8)
fig.suptitle("问题二两种方法结果对比（主方案=NSGA-II 完全可行）", y=1.02)
fig.tight_layout()
save(fig, "q2_extra_03_方法对比柱状图.png")

# ---------------------------------------------------------------------------
# 图 4：电池利用率堆叠图（各电池飞行/充电时长）
# ---------------------------------------------------------------------------
rt = pd.read_csv(os.path.join(R, "q2_1_resource_timeline.csv"), encoding="utf-8-sig")
rt["dur"] = rt["结束_s"] - rt["开始_s"]
batt = rt[rt["资源类型"] == "电池"]
agg = batt.groupby(["资源编号", "事件类型"])["dur"].sum().unstack(fill_value=0)
agg = agg.reindex(sorted(agg.index, key=lambda s: int(re.search(r"\d+", s).group())))
if "充电" not in agg.columns:
    agg["充电"] = 0
if "飞行" not in agg.columns:
    agg["飞行"] = 0
agg = agg[["飞行", "充电"]]

fig, ax = plt.subplots(figsize=(7.0, 4.8))
y = np.arange(len(agg))
ax.barh(y, agg["飞行"], color=C_MAIN, label="飞行", height=0.6)
ax.barh(y, agg["充电"], left=agg["飞行"], color="#ffb347", label="充电", height=0.6)
ax.set_yticks(y)
ax.set_yticklabels(agg.index, fontsize=8)
ax.set_xlabel("累计时长 (s)")
ax.set_title("问题二共享电池飞行/充电时长构成")
ax.legend()
save(fig, "q2_extra_04_电池利用率.png")

# ---------------------------------------------------------------------------
# 图 5：四目标 Pareto 前沿三维散点
# ---------------------------------------------------------------------------
pf = pd.read_csv(os.path.join(R, "q2_1_pareto_front.csv"), encoding="utf-8-sig")
fig = plt.figure(figsize=(6.4, 5.2))
ax = fig.add_subplot(111, projection="3d")
p = ax.scatter(pf["f2_makespan_s"], pf["f3_总能耗_kWh"], pf["f4_架次数"],
               c=pf["f1_及时性"], cmap="viridis", s=50, depthshade=True)
ax.set_xlabel("完成时间 $f_2$ (s)")
ax.set_ylabel("总能耗 $f_3$ (kWh)")
ax.set_zlabel("架次数 $f_4$")
ax.set_title("问题二 NSGA-II 非支配前沿（色=及时性 $f_1$）")
fig.colorbar(p, ax=ax, shrink=0.6, label="及时性 $f_1$")
save(fig, "q2_extra_05_帕累托三维散点.png")

print("fig_q2 done")
