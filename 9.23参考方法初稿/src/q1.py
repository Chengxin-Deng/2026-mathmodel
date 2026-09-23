"""Q1: single-area round trips, DEM-aware energy and deterministic batching."""
from __future__ import annotations

import itertools
import math

from model_core import FIG, RES, Terrain, endpoint, hav, inputs, max_elevation, num, save_json, trip, write_csv


def dem_trip(center, node, boxes, g, terrain, reserve=None):
    q = sum(b["mass"] for b in boxes)
    volume = sum(b["vol"] for b in boxes)
    home = endpoint(center, center["z"])
    target = endpoint(node, node["z"] + 30)
    d = hav(center, node)
    cruise = max_elevation(terrain, home, target) + 50
    climb = max(0, cruise - home["alt"])
    descend = max(0, cruise - target["alt"])
    speed = num(g["计划巡航速度（m/s）"])
    up, down = num(g["最大爬升速度（m/s）"]), num(g["最大下降速度（m/s）"])
    flight = 2 * d / speed + 2 * climb / up + 2 * descend / down
    hand = num(g["接收点基础交接时间（s）"]) + num(g["每箱增加交接时间（s）"]) * len(boxes)
    time = num(g["工位固定准备时间（s）"]) + num(g["每箱装载时间（s）"]) * len(boxes) + flight + hand
    capacity, l0, lf = num(g["最大载货质量（kg）"]), num(g["空载标准航程（m）"]), num(g["满载标准航程（m）"])
    usable = num(g["电池可用能量（kWh）"])
    lq = l0 - (l0 - lf) * (q / max(capacity, 1)) ** 1.5
    horizontal = usable * d / lq + usable * d / l0
    mass = num(g["含电池空载总质量（kg）"]) + q
    efficiency = max(num(g["爬升能耗效率"]), 0.01)
    climb_energy = mass * 9.81 * climb * 2 / (3.6e6 * efficiency)
    energy = horizontal + climb_energy
    min_soc = num(g["返航电量下限（%）"]) if reserve is None else reserve
    soc = 100 * (1 - energy / usable)
    return {"mass": q, "volume": volume, "distance": 2 * d, "time": time,
            "energy": energy, "soc": soc, "reserve": min_soc,
            "margin_kwh": usable * (soc - min_soc) / 100, "zcruise": cruise,
            "feasible_energy": soc >= min_soc}


def make_batches(center, nodes, boxes, types, terrain):
    by_area = {}
    for b in boxes:
        by_area.setdefault(b["area"], []).append(b)
    result = []
    tid = 1
    urgent_cycle = ["A", "A", "A", "A", "B", "B", "C", "C"]
    urgent_index = 0
    for area in sorted(by_area):
        urgent = [b for b in by_area[area] if b["first"] or b["type"] == "医疗物资"]
        rest = [b for b in by_area[area] if b not in urgent]
        packs = [urgent] if urgent else []
        while rest:
            batch, mass, vol = [], 0.0, 0.0
            for b in rest[:]:
                if mass + b["mass"] <= 80 and vol + b["vol"] <= 0.25:
                    batch.append(b); mass += b["mass"]; vol += b["vol"]; rest.remove(b)
            if not batch:
                batch = [rest.pop(0)]
            packs.append(batch)
        for index, batch in enumerate(packs):
            choices = []
            for kind, g in types.items():
                q, v = sum(b["mass"] for b in batch), sum(b["vol"] for b in batch)
                if q <= num(g["最大载货质量（kg）"]) and v <= num(g["可用装载体积（m³）"]):
                    metrics = dem_trip(center, nodes[area], batch, g, terrain)
                    if metrics["feasible_energy"]:
                        choices.append((kind, metrics))
            if not choices:
                raise RuntimeError(f"No feasible aircraft/batch: {area}")
            if index == 0:
                order = urgent_cycle[urgent_index % len(urgent_cycle):] + urgent_cycle[:urgent_index % len(urgent_cycle)]
                kind, metrics = next(((k, m) for preferred in order for k, m in choices if k == preferred), choices[0])
                urgent_index += 1
            else:
                kind, metrics = min(choices, key=lambda km: (km[1]["time"], km[1]["energy"]))
            result.append({"trip": f"P{tid:03d}", "area": area, "type": kind, "boxes": batch,
                           "metrics": metrics, "urgent": index == 0})
            tid += 1
    return result


def run():
    center, nodes, boxes, types, drones = inputs()
    terrain = Terrain()
    batches = make_batches(center, nodes, boxes, types, terrain)
    capacity_rows = []
    for area, node in sorted(nodes.items()):
        for kind, g in types.items():
            limit = min(num(g["最大载货质量（kg）"]), 80.0)
            lo, hi = 0.0, limit
            for _ in range(30):
                mid = (lo + hi) / 2
                metrics = dem_trip(center, node, [{"mass": mid, "vol": 0}], g, terrain)
                if metrics["soc"] >= num(g["返航电量下限（%）"]):
                    lo = mid
                else:
                    hi = mid
            capacity_rows.append({"area": area, "type": kind, "distance_m": round(hav(center, node), 1),
                                  "max_payload_kg": round(lo, 3), "type_limit_kg": num(g["最大载货质量（kg）"]),
                                  "terrain_peak_m": round(max_elevation(terrain, endpoint(center, center["z"]), endpoint(node, node["z"] + 30)), 1)})
    batch_rows = []
    for t in batches:
        m = t["metrics"]
        batch_rows.append({"trip": t["trip"], "area": t["area"], "type": t["type"],
                           "boxes": ",".join(b["id"] for b in t["boxes"]), "mass": round(m["mass"], 3),
                           "volume": round(m["volume"], 4), "time": round(m["time"], 2),
                           "energy": round(m["energy"], 5), "soc": round(m["soc"], 3),
                           "reserve": round(m["reserve"], 2), "margin_kwh": round(m["margin_kwh"], 4)})
    sensitivity = []
    for reserve in (15, 20, 25, 30, 35):
        feasible = 0
        max_load = {}
        for kind, g in types.items():
            values = []
            for area, node in nodes.items():
                lo, hi = 0.0, min(num(g["最大载货质量（kg）"]), 80.0)
                for _ in range(25):
                    mid = (lo + hi) / 2
                    if dem_trip(center, node, [{"mass": mid, "vol": 0}], g, terrain, reserve)["soc"] >= reserve:
                        lo = mid
                    else:
                        hi = mid
                values.append(lo)
            max_load[kind] = round(sum(values) / len(values), 3)
        for t in batches:
            g = types[t["type"]]
            if dem_trip(center, nodes[t["area"]], t["boxes"], g, terrain, reserve)["soc"] >= reserve:
                feasible += 1
        sensitivity.append({"reserve_pct": reserve, "feasible_batches": feasible, **{f"mean_payload_{k}_kg": v for k, v in max_load.items()}})
    write_csv("q1_capacity.csv", capacity_rows, list(capacity_rows[0]))
    write_csv("q1_batches.csv", batch_rows, list(batch_rows[0]))
    write_csv("q1_sensitivity.csv", sensitivity, list(sensitivity[0]))
    save_json("q1_summary.json", {"areas": len(nodes), "boxes": len(boxes), "trips": len(batches),
                                  "terrain": str(terrain.path), "dem_sampling_spacing_m": 30,
                                  "mass_kg": sum(b["mass"] for b in boxes),
                                  "energy_kwh": round(sum(t["metrics"]["energy"] for t in batches), 5),
                                  "min_soc_pct": round(min(t["metrics"]["soc"] for t in batches), 3),
                                  "all_batches_feasible": all(t["metrics"]["feasible_energy"] for t in batches)})
    print((RES / "q1_summary.json").read_text(encoding="utf-8"))
    return batches


if __name__ == "__main__":
    run()
