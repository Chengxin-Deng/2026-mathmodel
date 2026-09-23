"""Q2: event-driven heterogeneous drone and shared-battery scheduling."""
from __future__ import annotations

from model_core import RES, inputs, num, save_json, transport_stock, write_csv
from q1 import run as run_q1


def charge_seconds(full_time, soc_pct):
    x = max(0.0, min(100.0, soc_pct))
    if x < 90:
        return full_time * (0.65 * (90 - x) / 90 + 0.35)
    return full_time * 0.35 * (100 - x) / 10


def run():
    center, nodes, boxes, types, drones = inputs()
    batches = run_q1()
    drone_free = {d["id"]: 0.0 for d in drones}
    stocks = transport_stock()
    battery_free = {kind: [0.0] * count for kind, count in stocks.items()}
    charge_full = {"A": 1800.0, "B": 2400.0, "C": 3000.0}
    ordered = sorted(batches, key=lambda t: (not t["urgent"],
                       min((b["expect"] for b in t["boxes"]), default=1e12),
                       -t["metrics"]["distance"]))
    trip_rows, box_rows, event_rows = [], [], []
    late_soft = 0
    for t in ordered:
        kind = t["type"]
        candidates = [d for d in drones if d["type"] == kind]
        if not candidates:
            raise RuntimeError(f"No physical aircraft of type {kind}")
        drone = min(candidates, key=lambda d: drone_free[d["id"]])
        bi = min(range(len(battery_free[kind])), key=lambda i: battery_free[kind][i])
        start = max(drone_free[drone["id"]], battery_free[kind][bi])
        m = t["metrics"]
        end = start + m["time"]
        soc = m["soc"]
        delivery = end - num(types[kind]["接收点基础交接时间（s）"]) - num(types[kind]["每箱增加交接时间（s）"]) * (len(t["boxes"]) - 1)
        drone_free[drone["id"]] = end + 120
        battery_end = end + charge_seconds(charge_full[kind], soc)
        battery_free[kind][bi] = battery_end
        batch = {**t, "drone": drone["id"], "battery": f"{kind}-B{bi + 1:02d}",
                 "start": start, "end": end, "delivery": delivery, "soc": soc}
        trip_rows.append({"trip": t["trip"], "drone": drone["id"], "type": kind,
                          "battery": batch["battery"], "start": round(start, 2),
                          "route": f"O01>{t['area']}>O01", "return": round(end, 2),
                          "energy": round(m["energy"], 5), "soc": round(soc, 3),
                          "boxes": len(t["boxes"]), "mass": round(m["mass"], 3), "volume": round(m["volume"], 4),
                          "battery_ready": round(battery_end, 2)})
        event_rows.append({"resource_type": "aircraft", "resource": drone["id"], "trip": t["trip"],
                           "occupy_start": round(start, 2), "occupy_end": round(end + 120, 2), "ready": round(end + 120, 2)})
        event_rows.append({"resource_type": "battery", "resource": batch["battery"], "trip": t["trip"],
                           "occupy_start": round(start, 2), "occupy_end": round(end, 2), "ready": round(battery_end, 2)})
        for b in t["boxes"]:
            box_rows.append({"box": b["id"], "trip": t["trip"], "area": t["area"], "type": b["type"],
                             "first": b["first"], "deadline": b["deadline"], "expect": b["expect"],
                             "delivery": round(delivery, 2), "late": delivery > b["expect"]})
            if not b["first"] and b["type"] != "医疗物资" and delivery > b["expect"]:
                late_soft += 1
    trip_rows.sort(key=lambda r: r["trip"])
    box_rows.sort(key=lambda r: r["box"])
    event_rows.sort(key=lambda r: (r["occupy_start"], r["resource_type"], r["resource"]))
    first_violations = sum(1 for b in box_rows if b["first"] and b["deadline"] is not None and b["delivery"] > b["deadline"])
    medical_violations = sum(1 for b in box_rows if b["type"] == "医疗物资" and b["delivery"] > b["expect"])
    coverage = len(box_rows) == len(boxes) and len({r["box"] for r in box_rows}) == len(boxes)
    physical_feasible = all(r["soc"] >= num(types[r["type"]]["返航电量下限（%）"]) for r in trip_rows)
    write_csv("q2_trips.csv", trip_rows, list(trip_rows[0]))
    write_csv("q2_boxes.csv", box_rows, list(box_rows[0]))
    write_csv("q2_resources.csv", event_rows, list(event_rows[0]))
    summary = {"boxes": len(box_rows), "unique_boxes": len({r["box"] for r in box_rows}),
               "trips": len(trip_rows), "total_energy_kwh": round(sum(r["energy"] for r in trip_rows), 5),
               "makespan_s": round(max(r["return"] for r in trip_rows), 2),
               "minimum_return_soc_pct": round(min(r["soc"] for r in trip_rows), 3),
               "first_deadline_violations": first_violations,
               "medical_expectation_violations": medical_violations,
               "soft_expected_late_boxes": late_soft,
               "coverage_unique": coverage, "energy_feasible": physical_feasible,
               "resource_counts": {"aircraft": {k: sum(d["type"] == k for d in drones) for k in types},
                                   "batteries": stocks},
               "algorithm": "deterministic event-driven heuristic; no global optimality claim",
               "hard_constraints_pass": coverage and physical_feasible and first_violations == 0 and medical_violations == 0}
    save_json("q2_summary.json", summary)
    print((RES / "q2_summary.json").read_text(encoding="utf-8"))
    return trip_rows, box_rows


if __name__ == "__main__":
    run()
