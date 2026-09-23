"""Shared deterministic data and physics helpers for the four questions."""
from __future__ import annotations

import json
import math
import runpy
from pathlib import Path

from PIL import Image

WORK = Path(__file__).resolve().parents[1]
BASE = runpy.run_path(str(WORK / "src" / "build_solution.py"))
ROOT, DATA = BASE["ROOT"], BASE["DATA"]
RES, FIG = WORK / "results", WORK / "figures"
RES.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)


def inputs():
    return BASE["read_inputs"]()


def xlsx_sheets(path):
    return BASE["xlsx_sheets"](path)


def num(value, default=0.0):
    return BASE["f"](value, default)


def hav(a, b):
    return BASE["hav"](a, b)


def trip(center, node, boxes, params, seq=0, start=0):
    return BASE["model_trip"](center, node, boxes, params, seq, start)


def write_csv(name, rows, fields):
    BASE["write_csv"](RES / name, rows, fields)


def save_json(name, payload):
    (RES / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def communications():
    rows = xlsx_sheets(DATA / "通信链路参数.xlsx")["数据"][2:]
    result = {}
    for row in rows:
        if len(row) >= 5 and row[1]:
            result[(row[0], row[1])] = num(row[4])
    return result


def relay_data():
    rows = xlsx_sheets(DATA / "中继无人机数据.xlsx")["数据"]
    model = dict(zip(rows[1], rows[2]))
    relay_units = [(row[0], row[1], row[2]) for row in rows[6:8] if row and row[0]]
    stock = {row[0]: int(num(row[1])) for row in rows[11:] if row and row[0]}
    return model, relay_units, stock


def transport_stock():
    rows = xlsx_sheets(DATA / "运输无人机数据.xlsx")["数据"]
    stock = {row[0]: int(num(row[1])) for row in rows[19:] if row and row[0] in {"A", "B", "C"}}
    return stock


class Terrain:
    """WGS84 north-up GeoTIFF sampler using its embedded affine tags."""

    def __init__(self):
        candidates = list((ROOT / "数据" / "镇龙乡地理空间数据").rglob("镇龙乡及周边30米DEM.tif"))
        if not candidates:
            raise FileNotFoundError("30 m DEM GeoTIFF not found")
        self.path = candidates[0]
        self.image = Image.open(self.path)
        self.scale = self.image.tag_v2[33550]
        self.tie = self.image.tag_v2[33922]
        self.lon0, self.lat0 = self.tie[3], self.tie[4]
        self.dx, self.dy = self.scale[0], self.scale[1]

    def pixel(self, lon, lat):
        col = int(math.floor((lon - self.lon0) / self.dx))
        row = int(math.floor((self.lat0 - lat) / self.dy))
        if not (0 <= col < self.image.width and 0 <= row < self.image.height):
            return None
        return self.image.getpixel((col, row))

    def profile(self, a, b, spacing=30.0):
        distance = hav(a, b)
        count = max(2, int(math.ceil(distance / spacing)) + 1)
        points = []
        for i in range(count):
            t = i / (count - 1)
            lon = a["lon"] + (b["lon"] - a["lon"]) * t
            lat = a["lat"] + (b["lat"] - a["lat"]) * t
            points.append((t, distance * t, self.pixel(lon, lat)))
        return distance, points


def endpoint(node, alt):
    return {"lon": node["lon"], "lat": node["lat"], "alt": alt}


def max_elevation(terrain, a, b):
    _, points = terrain.profile(a, b)
    values = [p[2] for p in points if p[2] is not None]
    if not values:
        raise ValueError("DEM profile outside raster coverage")
    return max(values)


def link(terrain, a, b, tx, rx, comm, loss_extra=0.0):
    """Return a symmetric two-way link decision with sampled terrain LOS."""
    d, samples = terrain.profile({"lon": a["lon"], "lat": a["lat"]},
                                 {"lon": b["lon"], "lat": b["lat"]})
    blocked_at = None
    for _, along, ground in samples[1:-1]:
        if ground is None:
            continue
        fraction = along / d if d else 0.5
        ray = a["alt"] + fraction * (b["alt"] - a["alt"])
        if ground >= ray:
            blocked_at = along
            break
    f_mhz = comm[("传播参数", "载波频率（MHz）")]
    fspl = 32.44 + 20 * math.log10(max(d / 1000.0, 1e-9)) + 20 * math.log10(f_mhz)
    obs = comm[("传播参数", "地形遮挡附加损耗（dB）")] + loss_extra if blocked_at is not None else loss_extra
    system = comm[("传播参数", "系统损耗（dB）")]
    sensitivity = comm[("接收参数", "接收灵敏度（dBm）")]
    fade = comm[("接收参数", "衰落裕量（dB）")]
    loss_ab = fspl + obs + system
    p_ab = tx["power"] + tx["gain"] + rx["gain"] - loss_ab
    p_ba = rx["power"] + rx["gain"] + tx["gain"] - loss_ab
    threshold = sensitivity + fade
    margin = min(p_ab, p_ba) - threshold
    return {"distance_m": d, "samples": len(samples), "blocked": blocked_at is not None,
            "blocked_at_m": blocked_at, "fspl_db": fspl, "total_loss_db": loss_ab,
            "rx_ab_dbm": p_ab, "rx_ba_dbm": p_ba, "threshold_dbm": threshold,
            "margin_db": margin, "available": margin >= 0}


def endpoint_tx(category, comm):
    return {"power": comm[(category, "发射功率（dBm）")], "gain": comm[(category, "天线增益（dBi）")]}
