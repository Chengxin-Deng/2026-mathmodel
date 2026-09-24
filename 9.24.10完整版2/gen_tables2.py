# -*- coding: utf-8 -*-
"""生成问题一/问题四核心结果明细表。"""
import os
import pandas as pd

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables")
os.makedirs(OUT, exist_ok=True)


def write(name, body):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(body)
    print("[table]", name)


# ---------------------------------------------------------------------------
# 1) 问题一：45 组最大安全载荷（15 服务区 x 3 机型）
# ---------------------------------------------------------------------------
qmax = pd.read_csv(os.path.join(R, "q1_1_qmax.csv"), encoding="utf-8-sig")
piv = qmax.pivot_table(index="服务区编号", columns="机型编号", values="q_max_kg")
lim = qmax.pivot_table(index="服务区编号", columns="机型编号", values="限制因素", aggfunc="first")
rows = []
for s in sorted(piv.index):
    cells = []
    for g in ["A", "B", "C"]:
        v = piv.loc[s, g]
        f = lim.loc[s, g]
        tag = "质量" if f == "mass_cap" else "能量"
        cells.append(f"{v:.2f}({tag})")
    rows.append(f"{s} & {cells[0]} & {cells[1]} & {cells[2]} \\\\")
body = (
    "\\begin{center}\\small\\renewcommand{\\arraystretch}{1.05}\n"
    "\\begin{longtable}{lccc}\n"
    "\\caption{问题一 45 组最大安全载荷 $q_{\\max}(g,i)$（kg，括号为限制因素）}\\label{tab:q1_qmax_all}\\\\\n"
    "\\hline 服务区 & A 型 & B 型 & C 型 \\\\\\hline\\endfirsthead\n"
    "\\hline 服务区 & A 型 & B 型 & C 型 \\\\\\hline\\endhead\n"
    + "\n".join(rows) + "\n\\hline\\end{longtable}\\end{center}\n"
)
write("q1_qmax.tex", body)

# ---------------------------------------------------------------------------
# 2) 问题一：组批明细（18 批次）
# ---------------------------------------------------------------------------
bt = pd.read_csv(os.path.join(R, "q1_21_batches.csv"), encoding="utf-8-sig")
rows = []
for _, r in bt.iterrows():
    rows.append(
        f"{r['批次编号']} & {r['服务区编号']} & {r['机型编号']} & {int(r['箱数'])} & "
        f"{r['总质量_kg']:.0f} & {r['总体积_m3']:.3f} & {r['E_batch_kWh']:.2f} & {r['T_batch_s']:.0f} \\\\"
    )
body = (
    "\\begin{center}\\small\\renewcommand{\\arraystretch}{1.05}\n"
    "\\begin{longtable}{lllccccc}\n"
    "\\caption{问题一组批方案明细（均衡权重解，18 批次）}\\label{tab:q1_batches}\\\\\n"
    "\\hline 批次 & 服务区 & 机型 & 箱数 & 质量(kg) & 体积($m^3$) & 能耗(kWh) & 时间(s) \\\\\\hline\\endfirsthead\n"
    "\\hline 批次 & 服务区 & 机型 & 箱数 & 质量(kg) & 体积($m^3$) & 能耗(kWh) & 时间(s) \\\\\\hline\\endhead\n"
    + "\n".join(rows) + "\n\\hline\\end{longtable}\\end{center}\n"
)
write("q1_batches.tex", body)

# ---------------------------------------------------------------------------
# 3) 问题四：精确枚举分区方案（K=2 / K=3）
# ---------------------------------------------------------------------------
def partition_table(f, k, label):
    df = pd.read_csv(os.path.join(R, f), encoding="utf-8-sig")
    groups = sorted(df["任务组"].unique())
    rows = []
    for g in groups:
        sub = df[df["任务组"] == g]
        areas = "、".join(sorted({a for s in sub["服务区列表"] for a in s.split(",")}))
        rows.append(f"{g} & {areas} \\\\")
    return (
        "\\begin{table}[htbp]\n\\centering\\small\n"
        f"\\caption{{问题四精确枚举 K={k} 分区方案}}\\label{{{label}}}\n"
        "\\begin{tabular}{cl}\n\\toprule 任务组 & 服务区 \\\\\\midrule\n"
        + "\n".join(rows) + "\\bottomrule\\end{tabular}\\end{table}\n"
    )
write("q4_partition_k2.tex", partition_table("q4_1_partition_K2.csv", 2, "tab:q4_partition_k2"))
write("q4_partition_k3.tex", partition_table("q4_1_partition_K3.csv", 3, "tab:q4_partition_k3"))

print("gen_tables2 done")
