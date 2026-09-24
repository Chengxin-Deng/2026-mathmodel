# -*- coding: utf-8 -*-
"""补充高级多面板可视化 —— 仅增强，不改动任何数据/模型/结论。
读取求解代码输出的 CSV，绘制 seaborn/matplotlib 多面板图，SimSun 中文字体，DPI>=300。
"""
import os, warnings
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import seaborn as sns
warnings.filterwarnings("ignore")

# ---- 路径（使用 24404 别名以规避 os 层路径漂移）----
SRC = r"C:\Users\24404\PycharmProjects\pythonProject1\2026年研赛D题"
OUT = r"C:\Users\24404\MathModel Projects\SADSDAD\figures"
if not os.path.isdir(SRC):
    SRC = r"C:\Users\24404\PycharmProjects\pythonProject1\2026年研赛D题"
if not os.path.isdir(OUT):
    OUT = r"C:\Users\24404\MathModel Projects\SADSDAD\figures"

def rd(name):
    return pd.read_csv(os.path.join(SRC, name), encoding="utf-8-sig")

# ---- 全局样式 ----
mpl.font_manager.fontManager.addfont(r"C:\Windows\Fonts\simsun.ttc")
sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams.update({
    "font.sans-serif": ["SimSun"], "font.serif": ["SimSun"], "axes.unicode_minus": False,
    "font.size": 12, "axes.titlesize": 13, "axes.labelsize": 12,
    "figure.dpi": 120, "savefig.dpi": 320, "savefig.bbox": "tight",
})
PAL = sns.color_palette("deep")
CMAP_TYPE = {"A": PAL[0], "B": PAL[1], "C": PAL[3]}

def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name)

def panel_label(ax, s):
    ax.text(-0.08, 1.06, s, transform=ax.transAxes, fontsize=14,
            fontweight="bold", va="bottom", ha="right")

# ================= 图 A：问题一 最大安全载荷多维透视 =================
def fig_q1():
    df = rd("q1_1_qmax.csv")
    df.columns = ["机型","服务区","qmax","体积","限制","距离","海拔","能耗","能量上限"]
    df["距离km"] = df["距离"]/1000.0
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.6))

    # (a) 分组箱线+蜂群：q_max by 机型
    ax = axes[0,0]
    sns.boxplot(data=df, x="机型", y="qmax", hue="机型", palette=CMAP_TYPE,
                width=0.55, showcaps=True, fliersize=0, legend=False, ax=ax)
    sns.swarmplot(data=df, x="机型", y="qmax", color=".2", size=4, ax=ax)
    ax.set_xlabel("机型"); ax.set_ylabel("最大安全载荷 / kg")
    ax.set_title("各机型最大安全载荷分布"); panel_label(ax, "(a)")

    # (b) 气泡散点：能耗 vs 距离，size=q_max，hue=机型
    ax = axes[0,1]
    for g in ["A","B","C"]:
        s = df[df["机型"]==g]
        ax.scatter(s["距离km"], s["能耗"], s=s["qmax"]*4+15,
                   color=CMAP_TYPE[g], alpha=0.7, edgecolor="white", lw=0.6, label=g)
    ax.set_xlabel("往返水平距离 / km"); ax.set_ylabel("满载往返能耗 / kWh")
    ax.set_title("能耗—距离关系（气泡大小∝载荷）")
    ax.legend(title="机型", fontsize=10); panel_label(ax, "(b)")

    # (c) 限制因素堆叠计数
    ax = axes[1,0]
    ct = df.assign(限制=df["限制"].map({"mass_cap":"质量受限","energy_margin":"能量受限",
                                        "energy_cap":"能量受限"})) \
           .groupby(["机型","限制"]).size().unstack(fill_value=0)
    for c in ["质量受限","能量受限"]:
        if c not in ct: ct[c]=0
    ct = ct[["质量受限","能量受限"]]
    bottom = np.zeros(len(ct))
    cols = {"质量受限":PAL[2], "能量受限":PAL[3]}
    for c in ct.columns:
        ax.bar(ct.index, ct[c], bottom=bottom, label=c, color=cols[c], width=0.55)
        bottom += ct[c].values
    ax.set_xlabel("机型"); ax.set_ylabel("服务区数量")
    ax.set_title("载荷受限类型构成"); ax.legend(fontsize=10); panel_label(ax, "(c)")

    # (d) 平行坐标：标准化 距离/海拔/q_max
    ax = axes[1,1]
    sub = df[["距离km","海拔","qmax","机型"]].copy()
    norm = sub.copy()
    for c in ["距离km","海拔","qmax"]:
        norm[c] = (sub[c]-sub[c].min())/(sub[c].max()-sub[c].min()+1e-9)
    xs = [0,1,2]; labels=["水平距离","巡航海拔","安全载荷"]
    for _, r in norm.iterrows():
        ax.plot(xs, [r["距离km"],r["海拔"],r["qmax"]], color=CMAP_TYPE[r["机型"]],
                alpha=0.5, lw=1.1)
    ax.set_xticks(xs); ax.set_xticklabels(labels)
    ax.set_ylabel("归一化数值 (0–1)")
    ax.set_title("载荷—地形平行坐标")
    ax.legend(handles=[Patch(color=CMAP_TYPE[g], label=g) for g in ["A","B","C"]],
              title="机型", fontsize=10); panel_label(ax, "(d)")

    fig.tight_layout()
    save(fig, "adv_q1.png")

# ================= 图 B：问题二 调度结构与 Pareto =================
def fig_q2():
    pf = rd("q2_1_pareto_front.csv")
    pf.columns = ["f1","makespan","energy","N","viol"]
    st = rd("q2_1_sorties.csv")
    st.columns = ["架次","机型","无人机","电池","起飞","返航","停靠"]
    st["时长"] = st["返航"]-st["起飞"]
    st["停靠数"] = st["停靠"].str.count("S")

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.6))

    # (a) Pareto 前沿：makespan vs energy, 颜色=架次, 大小=及时性
    ax = axes[0,0]
    sc = ax.scatter(pf["makespan"]/3600, pf["energy"], c=pf["N"], s=90,
                    cmap="viridis", edgecolor="white", lw=0.7)
    ax.set_xlabel("完工时间 / h"); ax.set_ylabel("总能耗 / kWh")
    ax.set_title("四目标 Pareto 前沿投影")
    cb = fig.colorbar(sc, ax=ax); cb.set_label("架次数 N")
    panel_label(ax, "(a)")

    # (b) 架次时长分布 violin by 机型
    ax = axes[0,1]
    order = [g for g in ["A","B","C"] if g in st["机型"].unique()]
    sns.violinplot(data=st, x="机型", y="时长", order=order, hue="机型",
                   palette=CMAP_TYPE, inner="quartile", legend=False, ax=ax)
    sns.stripplot(data=st, x="机型", y="时长", order=order, color=".2", size=4, ax=ax)
    ax.set_xlabel("机型"); ax.set_ylabel("单架次作业时长 / s")
    ax.set_title("架次时长分布"); panel_label(ax, "(b)")

    # (c) 每机型架次数与停靠构成
    ax = axes[1,0]
    g = st.groupby(["机型","停靠数"]).size().unstack(fill_value=0)
    g.plot(kind="bar", stacked=True, ax=ax, colormap="crest", width=0.6)
    ax.set_xlabel("机型"); ax.set_ylabel("架次数")
    ax.set_title("架次数与停靠点数构成")
    ax.legend(title="停靠服务区数", fontsize=9)
    ax.tick_params(axis="x", rotation=0); panel_label(ax, "(c)")

    # (d) 能耗 vs 时长 气泡，hue=机型 size=停靠
    ax = axes[1,1]
    st["能耗近似"] = st["时长"]  # 仅用于占位若无列
    for gk in order:
        s = st[st["机型"]==gk]
        ax.scatter(s["时长"], s["停靠数"]+np.random.RandomState(0).uniform(-0.05,0.05,len(s)),
                   s=60, color=CMAP_TYPE[gk], alpha=0.7, edgecolor="white", label=gk)
    ax.set_xlabel("单架次时长 / s"); ax.set_ylabel("停靠服务区数")
    ax.set_title("时长—停靠关系"); ax.legend(title="机型", fontsize=10)
    panel_label(ax, "(d)")

    fig.tight_layout()
    save(fig, "adv_q2.png")

# ================= 图 C：问题三 通信保障与联合调度 =================
def fig_q3():
    rt = rd("q3_1_routes.csv")
    rt.columns = ["路线","机型","停靠","箱数","质量","体积","能耗","时长","通信","货箱"]
    rt["通信"] = rt["通信"].astype(str).str.startswith("直连").map({True:"直连", False:"中继"})
    rs = rd("q3_1_relay_sorties.csv")
    rs.columns = ["架次","无人机","能源","关联机型","关联停靠","经度","纬度","AGL","起飞","到位","撤离","返航","E","达标"]

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.6))

    # (a) 通信方式构成 (donut)
    ax = axes[0,0]
    comp = rt["通信"].value_counts()
    cols = sns.color_palette("Set2", len(comp))
    w,_,_ = ax.pie(comp.values, labels=comp.index, autopct=lambda p: f"{p*sum(comp)/100:.0f}",
                   colors=cols, wedgeprops=dict(width=0.42, edgecolor="white"),
                   textprops={"fontsize":11})
    ax.set_title("运输路线通信保障方式构成"); panel_label(ax, "(a)")

    # (b) 路线能耗 vs 时长, hue=通信
    ax = axes[0,1]
    for m,c in zip(rt["通信"].unique(), sns.color_palette("Set2")):
        s = rt[rt["通信"]==m]
        ax.scatter(s["时长"]/3600, s["能耗"], s=s["箱数"]*14+18, color=c,
                   alpha=0.75, edgecolor="white", label=m)
    ax.set_xlabel("路线时长 / h"); ax.set_ylabel("路线能耗 / kWh")
    ax.set_title("路线能耗—时长（气泡∝箱数）")
    ax.legend(title="通信方式", fontsize=10); panel_label(ax, "(b)")

    # (c) 中继悬停 AGL 分布
    ax = axes[1,0]
    sns.histplot(rs["AGL"], bins=8, kde=True, color=PAL[4], edgecolor="white", ax=ax)
    ax.set_xlabel("中继悬停离地高度 AGL / m"); ax.set_ylabel("架次数")
    ax.set_title("中继悬停高度分布"); panel_label(ax, "(c)")

    # (d) 中继架次能耗 vs 服务时长（撤离-到位）
    ax = axes[1,1]
    rs["服务时长"] = (rs["撤离"]-rs["到位"])/60.0
    sc = ax.scatter(rs["服务时长"], rs["E"], c=rs["AGL"], s=70, cmap="rocket_r",
                    edgecolor="white", lw=0.6)
    ax.set_xlabel("中继在位服务时长 / min"); ax.set_ylabel("中继架次能耗 / kWh")
    ax.set_title("中继能耗—服务时长")
    cb = fig.colorbar(sc, ax=ax); cb.set_label("AGL / m")
    panel_label(ax, "(d)")

    fig.tight_layout()
    save(fig, "adv_q3.png")

# ================= 图 D：问题四 分区权衡与搜索 =================
def fig_q4():
    ap = rd("q4_1_all_partitions.csv")
    ap.columns = ["K","编码","缺口","总规模","均衡","冗余"]
    w2 = rd("q4_1_workload_K2.csv"); w3 = rd("q4_1_workload_K3.csv")
    w2.columns = ["组","服务区","运输架次","中继架次","箱数","质量","运输能耗","中继能耗","时长"]
    w3.columns = w2.columns
    sh = rd("q4_2_search_history.csv")

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.6))

    # (a) 所有分区：均衡 vs 总规模，颜色=缺口，分 K 标记
    ax = axes[0,0]
    for k,mk in zip([2,3],["o","^"]):
        s = ap[ap["K"]==k]
        sc = ax.scatter(s["总规模"], s["均衡"], c=s["缺口"], marker=mk, s=32,
                        cmap="magma_r", alpha=0.7, edgecolor="none", label=f"K={k}")
    ax.set_xlabel("资源配置总规模"); ax.set_ylabel("工作量均衡系数 (CV)")
    ax.set_title("分区方案权衡空间")
    cb = fig.colorbar(sc, ax=ax); cb.set_label("资源缺口")
    ax.legend(fontsize=10); panel_label(ax, "(a)")

    # (b) 组间工作量均衡：分组柱（K2 vs K3）
    ax = axes[0,1]
    d2 = w2[["组","时长"]].assign(方案="K=2", 时长h=w2["时长"]/3600)
    d3 = w3[["组","时长"]].assign(方案="K=3", 时长h=w3["时长"]/3600)
    dd = pd.concat([d2,d3])
    sns.barplot(data=dd, x="方案", y="时长h", hue="组", palette="crest", ax=ax)
    ax.set_xlabel(""); ax.set_ylabel("任务组作业时长 / h")
    ax.set_title("组间作业时长均衡对比")
    ax.legend(title="任务组", fontsize=9); panel_label(ax, "(b)")

    # (c) 运输/中继能耗构成（堆叠）K2 vs K3
    ax = axes[1,0]
    rows=[]
    for tag,w in [("K=2",w2),("K=3",w3)]:
        for _,r in w.iterrows():
            rows.append((f"{tag}-G{int(r['组'])}", r["运输能耗"], r["中继能耗"]))
    ce = pd.DataFrame(rows, columns=["组","运输","中继"]).set_index("组")
    ce.plot(kind="bar", stacked=True, ax=ax, color=[PAL[0],PAL[3]], width=0.6)
    ax.set_xlabel(""); ax.set_ylabel("能耗 / kWh")
    ax.set_title("各任务组能耗构成")
    ax.legend(title="能耗类型", fontsize=9)
    ax.tick_params(axis="x", rotation=30); panel_label(ax, "(c)")

    # (d) 局部搜索收敛
    ax = axes[1,1]
    for k,c in zip([2,3],[PAL[0],PAL[3]]):
        s = sh[sh["K"]==k]
        ax.plot(s["iter"], s["scalar_score"], color=c, lw=1.6, label=f"K={k}")
    ax.set_yscale("log")
    ax.set_xlabel("迭代步"); ax.set_ylabel("标量化目标（对数轴）")
    ax.set_title("局部搜索收敛曲线")
    ax.legend(fontsize=10); panel_label(ax, "(d)")

    fig.tight_layout()
    save(fig, "adv_q4.png")

if __name__ == "__main__":
    fig_q1(); fig_q2(); fig_q3(); fig_q4()
    print("ALL DONE")
