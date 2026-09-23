"""Render manuscript figures only from archived reference JSON and Q4 TEX values."""
from __future__ import annotations

import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
REF = ROOT / "results" / "reference"
BG = "#fcfcfb"
INK = "#0b0b0b"
SECOND = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BLUE, ORANGE, TEAL, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"
)
COLORS = {"A": BLUE, "B": ORANGE, "C": TEAL, "direct": BLUE, "relay": ORANGE, "K=2": BLUE, "K=3": ORANGE}
FONT_PATH = ROOT / "simsun.ttf"


def load(name: str):
    return json.loads((REF / f"{name}.json").read_text(encoding="utf-8"))


def font(size: int):
    return ImageFont.truetype(str(FONT_PATH), size)


def canvas(title: str, subtitle: str = ""):
    im = Image.new("RGB", (1800, 1080), BG)
    d = ImageDraw.Draw(im)
    d.text((110, 54), title, font=font(42), fill=INK)
    if subtitle:
        d.text((112, 112), subtitle, font=font(25), fill=SECOND)
    return im, d


def axes(d, box, xmin, xmax, ymin, ymax, xlabel, ylabel, xticks=5, yticks=5,
         xfmt=None, yfmt=None, ytick_values=None):
    x0, y0, x1, y1 = box
    d.line((x0, y0, x0, y1, x1, y1), fill=SECOND, width=2)
    for i in range(xticks + 1):
        v = xmin + (xmax - xmin) * i / xticks
        x = x0 + (x1 - x0) * i / xticks
        d.line((x, y0, x, y1), fill=GRID, width=1)
        label = (xfmt or (lambda a: f"{a:g}"))(v)
        bb = d.textbbox((0, 0), label, font=font(20))
        if label:
            d.text((x - (bb[2] - bb[0]) / 2, y1 + 14), label, font=font(20), fill=SECOND)
    values = ytick_values if ytick_values is not None else [
        ymin + (ymax - ymin) * i / yticks for i in range(yticks + 1)
    ]
    for v in values:
        y = y1 - (y1 - y0) * (v - ymin) / (ymax - ymin)
        d.line((x0, y, x1, y), fill=GRID, width=1)
        label = (yfmt or (lambda a: f"{a:g}"))(v)
        bb = d.textbbox((0, 0), label, font=font(20))
        d.text((x0 - (bb[2] - bb[0]) - 15, y - 13), label, font=font(20), fill=SECOND)
    bbx = d.textbbox((0, 0), xlabel, font=font(23))
    d.text(((x0 + x1 - (bbx[2] - bbx[0])) / 2, y1 + 55), xlabel, font=font(23), fill=INK)
    d.text((30, y0 - 38), ylabel, font=font(23), fill=INK)
    return lambda x: x0 + (x - xmin) / (xmax - xmin) * (x1 - x0), lambda y: y1 - (y - ymin) / (ymax - ymin) * (y1 - y0)


def legend(d, entries, x, y, gap=210):
    for label, color in entries:
        d.rounded_rectangle((x, y + 4, x + 22, y + 24), radius=4, fill=color)
        d.text((x + 32, y), label, font=font(21), fill=SECOND)
        x += gap


def save(im, name):
    path = FIG / name
    im.save(path, dpi=(300, 300), optimize=True)


def bar_chart(name, title, labels, values, ylabel, color_values=None, ymax=None, subtitle=""):
    im, d = canvas(title, subtitle)
    raw_ymax = ymax or max(values) * 1.15 or 1
    if raw_ymax <= 0.5:
        tick_step = 0.1
    elif raw_ymax <= 2:
        tick_step = 0.5
    elif raw_ymax <= 5:
        tick_step = 1
    elif raw_ymax <= 10:
        tick_step = 2
    elif raw_ymax <= 20:
        tick_step = 5
    else:
        tick_step = math.ceil(raw_ymax / 5)
    ymax = math.ceil(raw_ymax / tick_step) * tick_step
    ytick_values = [i * tick_step for i in range(int(round(ymax / tick_step)) + 1)]
    yfmt = (lambda v: f"{v:.1f}") if tick_step < 1 else (lambda v: f"{v:.0f}")
    X, Y = axes(d, (190, 210, 1700, 850), 0, len(values), 0, ymax, "", ylabel,
                xticks=len(values), xfmt=lambda v: "", yfmt=yfmt, ytick_values=ytick_values)
    step = (1700 - 190) / len(values)
    for i, (label, value) in enumerate(zip(labels, values)):
        x0, x1 = 190 + i * step + step * .18, 190 + (i + 1) * step - step * .18
        d.rounded_rectangle((x0, Y(value), x1, Y(0)), radius=5, fill=(color_values or [BLUE] * len(values))[i])
        val = f"{value:.2f}" if isinstance(value, float) else str(value)
        bb = d.textbbox((0, 0), val, font=font(18))
        d.text(((x0 + x1 - bb[2] + bb[0]) / 2, Y(value) - 30), val, font=font(18), fill=INK)
        label_box = d.textbbox((0, 0), label, font=font(20))
        center = (x0 + x1) / 2
        d.text((center - (label_box[2] - label_box[0]) / 2, 870), label, font=font(20), fill=SECOND)
    save(im, name)


def line_chart(name, title, series, xlabel, ylabel, xlim=None, ylim=None, subtitle=""):
    im, d = canvas(title, subtitle)
    xs = [float(x) for _, points, _ in series for x, _ in points]
    ys = [float(y) for _, points, _ in series for _, y in points]
    xmin, xmax = xlim or (min(xs), max(xs))
    ymin, ymax = ylim or (min(0, min(ys)), max(ys) * 1.12 if max(ys) else 1)
    X, Y = axes(d, (190, 210, 1700, 850), xmin, xmax, ymin, ymax, xlabel, ylabel,
                xfmt=lambda v: f"{v:.0f}", yfmt=lambda v: f"{v:.1f}")
    legend(d, [(name, color) for name, _, color in series], 1040, 145, 220)
    for _, points, color in series:
        p = [(X(float(x)), Y(float(y))) for x, y in points]
        for a, b in zip(p, p[1:]):
            d.line((a, b), fill=color, width=4)
        for x, y in p:
            d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color, outline=BG, width=2)
    save(im, name)


def stacked_type_chart(name, title, categories, values_by_type, ylabel):
    im, d = canvas(title)
    totals = [sum(values_by_type[t][i] for t in "ABC") for i in range(len(categories))]
    ymax = max(totals) * 1.18
    X, Y = axes(d, (190, 210, 1700, 850), 0, len(categories), 0, ymax, "", ylabel,
                xticks=len(categories), xfmt=lambda v: "", yfmt=lambda v: f"{v:.1f}")
    legend(d, [(f"{t} 型", COLORS[t]) for t in "ABC"], 1070, 145, 185)
    step = (1700 - 190) / len(categories)
    for i in range(len(categories)):
        base = 0
        for t in "ABC":
            val = values_by_type[t][i]
            x0, x1 = 190 + i * step + step * .18, 190 + (i + 1) * step - step * .18
            d.rectangle((x0, Y(base + val), x1, Y(base)), fill=COLORS[t], outline=BG, width=2)
            base += val
        label = categories[i]
        bb = d.textbbox((0, 0), label, font=font(18))
        d.text((190 + (i + .5) * step - (bb[2] - bb[0]) / 2, 870), label, font=font(18), fill=SECOND)
    save(im, name)


def main():
    FIG.mkdir(exist_ok=True)
    q1, q2, q3 = load("problem1_exact"), load("problem2_exact"), load("problem3_exact")
    q4 = {
        "k2": {"gap": 3, "groups": [5, 10], "peak": [1, 2, 3, 1, 4, 4, 4, 4]},
        "k3": {"gap": 4, "groups": [3, 8, 4], "peak": [1, 2, 3, 1, 4, 5, 4, 4]},
    }
    q1trips = [t for area in q1["zones"].values() for t in area["trips"]]
    # 1. Payload capacity heatmap by area and aircraft.
    im, d = canvas("分区安全载荷", "每格为该服务区单点往返安全载荷（kg）；数值来源：参考解")
    areas = sorted(q1["safe_payload"])
    left, top, cellw, cellh = 340, 210, 400, 43
    for j, typ in enumerate("ABC"):
        d.text((left + j * cellw + 170, top - 48), f"{typ} 型", font=font(25), fill=INK)
    vals = [q1["safe_payload"][a][t] for a in areas for t in "ABC"]
    vmax = max(vals)
    for i, area in enumerate(areas):
        y = top + i * cellh
        d.text((170, y + 7), area, font=font(20), fill=SECOND)
        for j, typ in enumerate("ABC"):
            v = q1["safe_payload"][area][typ]
            frac = v / vmax
            # Sequential blue ramp with value labels.
            c = (int(205 - 175 * frac), int(226 - 105 * frac), int(251 - 20 * frac))
            x = left + j * cellw
            d.rectangle((x, y, x + cellw - 7, y + cellh - 4), fill=c, outline=BG, width=2)
            d.text((x + 145, y + 7), f"{v:.1f}", font=font(20), fill=INK)
    save(im, "fig_q1_payload_heatmap.png")
    # 2. Q1 trips by aircraft type.
    counts = [sum(t["aircraft_type"] == typ for t in q1trips) for typ in "ABC"]
    bar_chart("fig_q1_type_count.png", "问题一机型架次", list("ABC"), counts, "架次（次）", [COLORS[t] for t in "ABC"], subtitle="单服务区组批；参考解共 18 架次")
    # 3. Q1 energy by area.
    energy_by_area = {a: sum(t["energy"] for t in z["trips"]) for a, z in q1["zones"].items()}
    bar_chart("fig_q1_area_energy.png", "问题一分区运输能耗", areas, [energy_by_area[a] for a in areas], "能耗（kWh）", [TEAL] * len(areas))
    # 4. Sensitivity.
    reserves = sorted(float(k) for k in q1["reserve_sensitivity"])
    sens_series = [(f"{t} 型", [(100 * r, sum(q1["reserve_sensitivity"][str(r)][a][t] for a in areas) / len(areas)) for r in reserves], COLORS[t]) for t in "ABC"]
    line_chart("fig_q1_reserve_sensitivity.png", "返航储备敏感性", sens_series, "返航储备率（%）", "平均安全载荷（kg）", xlim=(min(100*r for r in reserves), max(100*r for r in reserves)))
    # 5. Q2 Gantt by drone.
    im, d = canvas("问题二运输时序", "实体无人机任务区间；颜色区分机型，区间端点为起飞与返航（s）")
    rows = sorted(q2["trips"], key=lambda t: (t["drone"], t["start"]))
    drones = sorted({t["drone"] for t in rows})
    x0, x1, y0 = 270, 1690, 235
    ymax = max(t["end"] for t in rows)
    for i, drone in enumerate(drones):
        y = y0 + i * 68
        d.text((165, y + 8), drone, font=font(21), fill=SECOND)
        d.line((x0, y + 34, x1, y + 34), fill=GRID, width=1)
    for t in rows:
        y = y0 + drones.index(t["drone"]) * 68 + 10
        xa = x0 + (x1 - x0) * t["start"] / ymax
        xb = x0 + (x1 - x0) * t["end"] / ymax
        d.rounded_rectangle((xa, y, max(xa + 3, xb), y + 25), radius=4, fill=COLORS[t["aircraft_type"]])
    for k in range(6):
        xx = x0 + (x1 - x0) * k / 5
        d.line((xx, y0 - 12, xx, y0 + 68 * len(drones)), fill=GRID, width=1)
        d.text((xx - 20, y0 + 68 * len(drones) + 5), f"{ymax*k/5:.0f}", font=font(18), fill=SECOND)
    legend(d, [(f"{t} 型", COLORS[t]) for t in "ABC"], 1110, 155, 175)
    d.text((720, 990), "仿真时间（s）", font=font(23), fill=INK)
    save(im, "fig_q2_gantt.png")
    # 6. Q2 energy by type.
    energy_type = {t: sum(x["energy"] for x in q2["trips"] if x["aircraft_type"] == t) for t in "ABC"}
    bar_chart("fig_q2_type_energy.png", "问题二机型能耗", list("ABC"), [energy_type[t] for t in "ABC"], "能耗（kWh）", [COLORS[t] for t in "ABC"])
    # 7. Delivery ECDF.
    deliveries = sorted((float(t["start"]) + float(t["delivery_offsets"][str(idx)]) for t in q2["trips"] for idx in t["box_indices"]))
    points = [(v, 100 * (i + 1) / len(deliveries)) for i, v in enumerate(deliveries)]
    line_chart("fig_q2_delivery_ecdf.png", "逐箱交付累计曲线", [("累计交付", points, TEAL)], "仿真时间（s）", "累计交付（%）", xlim=(0, q2["makespan_s"]), ylim=(0, 100), subtitle="共计 80 箱；按参考解交付时刻排序")
    # 8. Q2 aircraft mix by trips and energy (separate bars in one figure, grouped).
    counts = {t: sum(x["aircraft_type"] == t for x in q2["trips"]) for t in "ABC"}
    im, d = canvas("问题二机型结构", "机型架次与对应能耗分图列示，避免双纵轴")
    for panel, title, vals, unit, maxv in [(0, "架次（次）", counts, "架次", max(counts.values())), (1, "能耗（kWh）", energy_type, "能耗", max(energy_type.values()))]:
        left = 180 + panel * 820
        d.text((left, 195), title, font=font(27), fill=INK)
        base_y = 830
        for i, typ in enumerate("ABC"):
            x = left + 90 + i * 220
            v = vals[typ]
            h = 500 * v / (maxv * 1.1)
            d.rectangle((x, base_y - h, x + 125, base_y), fill=COLORS[typ])
            d.text((x + 43, base_y - h - 32), f"{v:.1f}" if isinstance(v, float) else str(v), font=font(20), fill=INK)
            d.text((x + 45, base_y + 15), typ, font=font(22), fill=SECOND)
        d.line((left + 50, base_y, left + 760, base_y), fill=SECOND, width=2)
    save(im, "fig_q2_aircraft_mix.png")
    # 9. Q3 mode composition.
    mode_counts = [sum(o["mode"] == mode for o in q3["options"]) for mode in ("direct", "relay")]
    bar_chart("fig_q3_mode_count.png", "问题三通信方式", ["直连", "中继"], mode_counts, "运输架次（次）", [BLUE, ORANGE], subtitle="通信模式沿用给定参考解；候选数 64")
    # 10. Q3 relay energy per mission.
    missions = q3["relay_missions"]
    relay_values = [m["energy"] for m in missions]
    bar_chart("fig_q3_relay_energy.png", "中继任务能耗", [m["mission_id"] for m in missions], relay_values, "能耗（kWh）", [ORANGE] * len(missions), ymax=0.4)
    # 11. Q4 stock gap comparison, source is user-provided updated TEX.
    im, d = canvas("两种分区资源缺口", "缺口按用户提供的新版 Q4 TEX；不从旧 Q4 JSON 取值")
    labels = ["运输机", "电池", "中继机", "总缺口"]
    vals = {"K=2": [1, 0, 2, 3], "K=3": [1, 1, 2, 4]}
    X, Y = axes(d, (220, 250, 1690, 850), 0, 4, 0, 4, "", "缺口单位（个）", xticks=4, yticks=4, xfmt=lambda v: "", yfmt=lambda v: f"{v:.0f}", ytick_values=[0, 1, 2, 3, 4])
    legend(d, [(k, COLORS[k]) for k in vals], 1110, 165, 200)
    step = (1690 - 220) / 4
    for i, label in enumerate(labels):
        center = 220 + (i + .5) * step
        for j, k in enumerate(("K=2", "K=3")):
            v = vals[k][i]
            xx0 = center - 75 + j * 78
            d.rectangle((xx0, Y(v), xx0 + 62, Y(0)), fill=COLORS[k])
            d.text((xx0 + 20, Y(v) - 28), str(v), font=font(19), fill=INK)
        bb = d.textbbox((0, 0), label, font=font(20))
        d.text((center - (bb[2] - bb[0]) / 2, 870), label, font=font(20), fill=SECOND)
    save(im, "fig_q4_gap_comparison.png")
    # 12. Q4 independent peak fleet by group.
    im, d = canvas("K=2 分区运输工作量", "每组服务区数；分区来自用户提供的新版 Q4 TEX")
    k2labels = ["G1", "G2"]
    bar_chart("fig_q4_k2_groups.png", "K=2 分区规模", k2labels, q4["k2"]["groups"], "服务区数量（个）", [BLUE, BLUE])
    # Replace last chart title with meaningful K=3 group chart; produce both figures.
    bar_chart("fig_q4_k3_groups.png", "K=3 分区规模", ["G1", "G2", "G3"], q4["k3"]["groups"], "服务区数量（个）", [ORANGE] * 3)
    # A 13th plot summarizes peak inventory by resource for both K settings.
    resources = ["A机", "B机", "C机", "A电池", "B电池", "C电池", "中继机", "中继组件"]
    im, d = canvas("两种分区峰值配置", "各组独立任务时序的峰值并发需求合计；取自新版 Q4 TEX")
    X, Y = axes(d, (250, 250, 1690, 850), 0, 8, 0, 5, "", "峰值配置（个）", xticks=8, yticks=5, xfmt=lambda v: "", yfmt=lambda v: f"{v:.0f}", ytick_values=[0, 1, 2, 3, 4, 5])
    legend(d, [(k, COLORS[k]) for k in ("K=2", "K=3")], 1120, 165, 200)
    step = (1690 - 250) / 8
    for i, label in enumerate(resources):
        center = 250 + (i + .5) * step
        for j, k in enumerate(("k2", "k3")):
            v = q4[k]["peak"][i]
            xx0 = center - 62 + j * 62
            d.rectangle((xx0, Y(v), xx0 + 48, Y(0)), fill=COLORS["K=2"] if k == "k2" else COLORS["K=3"])
        bb = d.textbbox((0, 0), label, font=font(17))
        d.text((center - (bb[2] - bb[0]) / 2, 870), label, font=font(17), fill=SECOND)
    save(im, "fig_q4_peak_resources.png")
    names = sorted(p.name for p in FIG.glob("fig_q*.png"))
    print("\\n".join(names))
    print(f"count={len(names)}")


if __name__ == "__main__":
    main()
