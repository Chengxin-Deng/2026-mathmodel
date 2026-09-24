# -*- coding: utf-8 -*-
"""从结果 CSV 生成 LaTeX 表格片段（longtable），保证结果正确、无手抄错误。"""
import os
import pandas as pd

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables")
os.makedirs(OUT, exist_ok=True)


def esc(s):
    return str(s).replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")


def write(name, body):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(body)
    print("[table]", name)


# ---------------------------------------------------------------------------
# 1) 问题二 NSGA-II 主方案：29 条运输路线
# ---------------------------------------------------------------------------
routes = pd.read_csv(os.path.join(R, "q2_1_routes.csv"), encoding="utf-8-sig")
rows = []
for _, r in routes.iterrows():
    rows.append(
        f"{r['路线编号']} & {r['机型编号']} & {esc(r['停靠序列'])} & "
        f"{int(r['箱数'])} & {r['总质量_kg']:.0f} & {r['总体积_m3']:.3f} & "
        f"{r['E_route_kWh']:.2f} & {r['T_route_s']:.0f} \\\\"
    )
body = (
    "\\begin{center}\\small\\renewcommand{\\arraystretch}{1.05}\n"
    "\\begin{longtable}{lllccccc}\n"
    "\\caption{问题二主方案（NSGA-II）运输路线明细}\\\\\n"
    "\\hline\n"
    "编号 & 机型 & 停靠序列 & 箱数 & 总质量(kg) & 总体积($m^3$) & 能耗(kWh) & 时间(s) \\\\\n"
    "\\hline\\endfirsthead\n"
    "\\hline 编号 & 机型 & 停靠序列 & 箱数 & 总质量(kg) & 总体积($m^3$) & 能耗(kWh) & 时间(s) \\\\\\hline\\endhead\n"
    + "\n".join(rows) +
    "\n\\hline\\end{longtable}\\end{center}\n"
)
write("q2_routes.tex", body)

# ---------------------------------------------------------------------------
# 2) 问题二 NSGA-II 主方案：80 箱逐箱送达时刻
# ---------------------------------------------------------------------------
boxes = pd.read_csv(os.path.join(R, "q2_1_box_delivery.csv"), encoding="utf-8-sig")
rows = []
for _, b in boxes.iterrows():
    hard = b["硬约束时限_s"]
    hard_s = f"{hard:.0f}" if pd.notna(hard) else "—"
    over = "是" if b["是否硬约束超时"] else "否"
    rows.append(
        f"{esc(b['货箱编号'])} & {b['服务区编号']} & {b['物资类型']} & "
        f"{b['期望送达时间_s']:.0f} & {hard_s} & {b['实际送达时刻_s']:.0f} & {over} \\\\"
    )
body = (
    "\\begin{center}\\small\\renewcommand{\\arraystretch}{1.05}\n"
    "\\begin{longtable}{llllccc}\n"
    "\\caption{问题二主方案（NSGA-II）逐箱送达时刻}\\\\\n"
    "\\hline\n"
    "货箱编号 & 服务区 & 物资类型 & 期望(s) & 硬时限(s) & 实际送达(s) & 超时 \\\\\n"
    "\\hline\\endfirsthead\n"
    "\\hline 货箱编号 & 服务区 & 物资类型 & 期望(s) & 硬时限(s) & 实际送达(s) & 超时 \\\\\\hline\\endhead\n"
    + "\n".join(rows) +
    "\n\\hline\\end{longtable}\\end{center}\n"
)
write("q2_boxes.tex", body)

# ---------------------------------------------------------------------------
# 3) 问题二 NSGA-II 主方案：架次安排
# ---------------------------------------------------------------------------
sorties = pd.read_csv(os.path.join(R, "q2_1_sorties.csv"), encoding="utf-8-sig")
rows = []
for _, s in sorties.iterrows():
    rows.append(
        f"{s['架次编号']} & {s['机型编号']} & {s['无人机编号']} & {s['电池编号']} & "
        f"{s['起飞时刻_s']:.0f} & {s['返航时刻_s']:.0f} & {esc(s['停靠序列'])} \\\\"
    )
body = (
    "\\begin{center}\\small\\renewcommand{\\arraystretch}{1.05}\n"
    "\\begin{longtable}{llllccl}\n"
    "\\caption{问题二主方案（NSGA-II）架次安排与资源分配}\\\\\n"
    "\\hline\n"
    "架次 & 机型 & 无人机 & 电池 & 起飞(s) & 返航(s) & 停靠序列 \\\\\n"
    "\\hline\\endfirsthead\n"
    "\\hline 架次 & 机型 & 无人机 & 电池 & 起飞(s) & 返航(s) & 停靠序列 \\\\\\hline\\endhead\n"
    + "\n".join(rows) +
    "\n\\hline\\end{longtable}\\end{center}\n"
)
write("q2_sorties.tex", body)

# ---------------------------------------------------------------------------
# 4) 问题三主方案（q3_2）中继架次
# ---------------------------------------------------------------------------
try:
    relay = pd.read_csv(os.path.join(R, "q3_2_relay_sorties.csv"), encoding="utf-8-sig")
    cols = list(relay.columns)
    rows = []
    for _, r in relay.iterrows():
        def g(*names):
            for n in names:
                if n in cols:
                    v = r[n]
                    return f"{v:.4f}" if isinstance(v, float) else str(v)
            return "—"
        rows.append(
            f"{g('架次编号','中继架次编号')} & {g('无人机编号','中继无人机编号')} & "
            f"{g('能源组件编号')} & {g('悬停经度')} & {g('悬停纬度')} & "
            f"{g('悬停AGL_m','悬停高度m','悬停离地高度m')} & {g('E_kWh','中继能耗kWh','能耗kWh')} \\\\"
        )
    body = (
        "\\begin{center}\\small\n"
        "\\begin{longtable}{lllcccc}\n"
        "\\caption{问题三主方案中继架次明细}\\\\\n"
        "\\hline 架次 & 中继机 & 能源组件 & 经度 & 纬度 & AGL(m) & 能耗(kWh) \\\\\\hline\\endfirsthead\n"
        "\\hline 架次 & 中继机 & 能源组件 & 经度 & 纬度 & AGL(m) & 能耗(kWh) \\\\\\hline\\endhead\n"
        + "\n".join(rows) + "\n\\hline\\end{longtable}\\end{center}\n"
    )
    write("q3_relay.tex", body)
except Exception as e:
    print("q3 relay table skipped:", e)

print("gen_tables done")
