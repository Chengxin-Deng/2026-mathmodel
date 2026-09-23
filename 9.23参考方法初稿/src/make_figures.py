"""Generate consistent 300-DPI paper figures with Pillow."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from model_core import FIG, RES, inputs

BG = "#fcfcfb"
INK = "#0b0b0b"
SECONDARY = "#52514e"
GRID = "#e1e0d9"
BLUE, ORANGE, TEAL, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948")
COLORS = {"A": BLUE, "B": ORANGE, "C": TEAL, "直连": BLUE, "中继": ORANGE,
          "通信中断": RED, "K=2": BLUE, "K=3": ORANGE}


def csv_rows(filename):
    with (RES / filename).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_font(size):
    path = Path(__file__).resolve().parents[1] / "simsun.ttf"
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def canvas(title, subtitle=""):
    im = Image.new("RGB", (1500, 900), BG)
    draw = ImageDraw.Draw(im)
    draw.text((90, 38), title, fill=INK, font=load_font(34))
    if subtitle:
        draw.text((92, 84), subtitle, fill=SECONDARY, font=load_font(22))
    return im, draw, (130, 150, 1410, 790)


def axes(draw, box, y_max, y_label, x_labels=None, x_label=""):
    x0, y0, x1, y1 = box
    draw.line((x0, y0, x0, y1), fill="#c3c2b7", width=2)
    draw.line((x0, y1, x1, y1), fill="#c3c2b7", width=2)
    for k in range(6):
        y = y1 - (y1-y0)*k/5
        draw.line((x0, y, x1, y), fill=GRID, width=1)
        draw.text((42, y-11), f"{y_max*k/5:,.0f}", fill=SECONDARY, font=load_font(17))
    draw.text((25, y0-32), y_label, fill=SECONDARY, font=load_font(19))
    if x_labels:
        step = (x1-x0)/max(1, len(x_labels)-1)
        for i, label in enumerate(x_labels):
            draw.text((x0+step*i-20, y1+13), str(label), fill=SECONDARY, font=load_font(16))
    if x_label:
        draw.text(((x0+x1)//2-70, y1+50), x_label, fill=SECONDARY, font=load_font(19))


def legend(draw, entries, x, y):
    for label, color in entries:
        draw.rounded_rectangle((x, y, x+20, y+15), radius=4, fill=color)
        draw.text((x+28, y-4), label, fill=SECONDARY, font=load_font(18))
        x += 160


def finish(im, name):
    path = FIG / name
    im.save(path, dpi=(300, 300))
    return path


def line_chart(name, title, xlabels, series, ylabel, ymax, xlabel="架次序号"):
    im, d, box = canvas(title)
    axes(d, box, ymax, ylabel, xlabels, xlabel)
    x0, y0, x1, y1 = box
    entries = []
    for label, values, color in series:
        entries.append((label, color))
        points = []
        for i, value in enumerate(values):
            x = x0+(x1-x0)*i/max(1,len(values)-1)
            y = y1-(y1-y0)*value/ymax
            points.append((x,y))
        for a,b in zip(points,points[1:]): d.line((a,b), fill=color, width=3)
        for x,y in points[::max(1,len(points)//20)]: d.ellipse((x-5,y-5,x+5,y+5), fill=color, outline=BG, width=2)
    legend(d, entries, 980, 105)
    finish(im,name)


def bars(name, title, labels, values, ylabel, ymax, color=BLUE):
    im,d,box=canvas(title)
    axes(d,box,ymax,ylabel,labels,"服务区 / 参数")
    x0,y0,x1,y1=box
    step=(x1-x0)/len(values)
    for i,v in enumerate(values):
        x=x0+i*step+step*.22
        y=y1-(y1-y0)*v/ymax
        d.rounded_rectangle((x,y,x+step*.56,y1),radius=4,fill=color)
    finish(im,name)


def gantt():
    rows=csv_rows("q2_trips.csv")
    im,d=canvas("运输机任务时序","每条横线表示一个架次；横轴为仿真时间")
    left,top,right,bottom=270,150,1410,790
    max_t=max(float(r["return"]) for r in rows)
    drone_names=sorted({r["drone"] for r in rows})
    for i,name in enumerate(drone_names):
        y=top+i*min(52,(bottom-top)/len(drone_names))
        d.text((95,y),name,fill=SECONDARY,font=load_font(18))
        d.line((left,y+25,right,y+25),fill=GRID,width=1)
    for r in rows:
        i=drone_names.index(r["drone"])
        y=top+i*min(52,(bottom-top)/len(drone_names))+9
        x0=left+(right-left)*float(r["start"])/max_t
        x1=left+(right-left)*float(r["return"])/max_t
        d.rounded_rectangle((x0,y,x1,y+22),radius=4,fill=COLORS[r["type"]])
    for k in range(6):
        x=left+(right-left)*k/5
        d.line((x,top,x,bottom),fill=GRID,width=1)
        d.text((x-20,bottom+12),f"{max_t*k/5:.0f}",fill=SECONDARY,font=load_font(16))
    legend(d,[(k,COLORS[k]) for k in "ABC"],1000,105)
    finish(im,"fig_q2_gantt.png")


def map_dem():
    center,nodes,boxes,types,drones=inputs()
    from model_core import Terrain
    terrain=Terrain()
    im,d,box=canvas("服务区地形与节点","背景为30 m DEM；点位按需求人口分级")
    x0,y0,x1,y1=box
    w,h=terrain.image.size
    thumbnail=terrain.image.convert("L").resize((x1-x0,y1-y0))
    # Contrast is intentionally subdued so node symbols remain legible.
    thumbnail=thumbnail.point(lambda p:int(218+(p-60)*0.05))
    im.paste(thumbnail.convert("RGB"),(x0,y0))
    d=ImageDraw.Draw(im)
    lonmin,lonmax=terrain.lon0,terrain.lon0+w*terrain.dx
    latmax,latmin=terrain.lat0,terrain.lat0-h*terrain.dy
    def xy(p): return (x0+(p["lon"]-lonmin)/(lonmax-lonmin)*(x1-x0),y0+(latmax-p["lat"])/(latmax-latmin)*(y1-y0))
    p=xy(center); d.ellipse((p[0]-9,p[1]-9,p[0]+9,p[1]+9),fill=RED,outline=BG,width=3); d.text((p[0]+12,p[1]-18),"O01",fill=INK,font=load_font(18))
    pop=[v["pop"] for v in nodes.values()]
    for a,node in nodes.items():
        p=xy(node); radius=5+int(9*node["pop"]/max(pop))
        d.ellipse((p[0]-radius,p[1]-radius,p[0]+radius,p[1]+radius),fill=BLUE,outline=BG,width=2)
        d.text((p[0]+7,p[1]-10),a[1:],fill=INK,font=load_font(15))
    finish(im,"fig_q1_dem_nodes.png")


def generate():
    cap=csv_rows("q1_capacity.csv")
    areas=sorted({r["area"] for r in cap})
    for kind in "ABC":
        rows=[r for r in cap if r["type"]==kind]
        bars(f"fig_q1_capacity_{kind}.png",f"{kind}型无人机单点安全载荷",[r["area"] for r in rows],
             [float(r["max_payload_kg"]) for r in rows],"安全载荷（kg）",max(float(r["max_payload_kg"]) for r in rows)*1.1,COLORS[kind])
    batches=csv_rows("q1_batches.csv")
    line_chart("fig_q1_batch_soc.png","组批返航SOC",[r["trip"] for r in batches],
               [("SOC",[float(r["soc"]) for r in batches],BLUE),("安全线",[20]*len(batches),RED)],"SOC（%）",100)
    sens=csv_rows("q1_sensitivity.csv")
    line_chart("fig_q1_reserve_sensitivity.png","返航储备敏感性",[r["reserve_pct"] for r in sens],
               [(f"{k}型平均安全载荷",[float(r[f"mean_payload_{k}_kg"]) for r in sens],COLORS[k]) for k in "ABC"],"平均安全载荷（kg）",80,"返航储备比例（%）")
    trips=csv_rows("q2_trips.csv")
    line_chart("fig_q2_energy_soc.png","架次能耗与返航SOC",[r["trip"] for r in trips],
               [("能耗",[float(r["energy"]) for r in trips],BLUE)],"能耗（kWh）",max(float(r["energy"]) for r in trips)*1.15)
    box=csv_rows("q2_boxes.csv")
    delivery=sorted(float(r["delivery"]) for r in box)
    ecdf=[(i+1)/len(delivery)*100 for i in range(len(delivery))]
    line_chart("fig_q2_delivery_ecdf.png","逐箱交付经验分布",list(range(1,len(delivery)+1)),[("累计比例",ecdf,TEAL)],"累计交付比例（%）",100,"交付时间排序")
    gantt()
    comm=csv_rows("q3_path_checks.csv")
    line_chart("fig_q3_link_margin.png","运输路径直连链路最差裕量",[r["trip"] for r in comm],
               [("最差接收裕量",[float(r["direct_worst_margin_db"]) for r in comm],BLUE),("接收门限",[0]*len(comm),RED)],"裕量（dB）",max(20,max(float(r["direct_worst_margin_db"]) for r in comm)*1.1)
    partitions=csv_rows("q4_partition.csv")
    groups=sorted({f"K{r['K']}-G{r['group']}" for r in partitions})
    for kind in "ABC":
        bars(f"fig_q4_aircraft_{kind}.png",f"分区{kind}型运输机独立峰值",[f"K{r['K']}-G{r['group']}" for r in partitions],
             [int(r[kind]) for r in partitions],"运输机数量（架）",max(2,max(int(r[kind]) for r in partitions)+1),COLORS[kind])
    map_dem()
    # Separate mass and energy so there is no misleading dual axis.
    area_mass={}
    center,nodes,boxes,types,drones=inputs()
    for b in boxes: area_mass[b["area"]]=area_mass.get(b["area"],0)+b["mass"]
    labels=sorted(area_mass)
    bars("fig_q1_demand_mass.png","服务区物资质量需求",labels,[area_mass[a] for a in labels],"需求质量（kg）",max(area_mass.values())*1.15,TEAL)
    return sorted(p.name for p in FIG.glob("fig_*.png"))


if __name__ == "__main__":
    print("\n".join(generate()))
