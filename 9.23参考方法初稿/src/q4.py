"""Q4: fixed-plan spatial partition and independent resource requirement."""
from __future__ import annotations

import itertools
import math

from model_core import RES, inputs, num, relay_data, save_json, transport_stock, write_csv
from q2 import run as run_q2
from q3 import run as run_q3


def union_find_groups(areas, edges, k):
    parent = {a: a for a in areas}
    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in edges:
        ra, rb = root(a), root(b)
        if ra != rb:
            parent[rb] = ra
    comps = {}
    for a in areas:
        comps.setdefault(root(a), []).append(a)
    components = list(comps.values())
    if len(components) > k:
        raise ValueError(f"Fixed multi-area trips create {len(components)} components, cannot partition into K={k}")
    groups = [list(c) for c in components]
    while len(groups) < k:
        idx = max(range(len(groups)), key=lambda i: (len(groups[i]), groups[i]))
        g = groups.pop(idx)
        if len(g) < 2:
            raise ValueError("Cannot split components to requested K")
        midpoint = len(g) // 2
        groups.extend([g[:midpoint], g[midpoint:]])
    return groups


def peak_concurrent(rows, start_key, end_key):
    events = []
    for r in rows:
        events.append((r[start_key], 1))
        events.append((r[end_key], -1))
    events.sort(key=lambda e: (e[0], e[1]))
    active = peak = 0
    for _, delta in events:
        active += delta
        peak = max(peak, active)
    return peak


def run():
    center, nodes, boxes, types, drones = inputs()
    trips, box_rows = run_q2()
    q3.run()
    comm_rows = list(__import__("csv").DictReader(open(RES / "q3_comm.csv", encoding="utf-8-sig")))
    relay_rows = list(__import__("csv").DictReader(open(RES / "q3_relay.csv", encoding="utf-8-sig")))
    _, relay_units, relay_stock = relay_data()
    battery_stock = transport_stock()
    edges = []
    for tr in trips:
        route = tr["route"].split(">")
        visit = [x for x in route if x.startswith("S")]
        edges.extend(zip(visit, visit[1:]))
    area_times = {a: max((r["return"] for r in trips if r["route"].split(">")[1] == a), default=0) for a in nodes}
    metric_by_trip = {r["trip"]: r for r in trips}
    demand_by_area = {a: sum(b["mass"] for b in boxes if b["area"] == a) for a in nodes}
    outputs, summaries = [], []
    for k in (2, 3):
        groups = union_find_groups(sorted(nodes), edges, k)
        records = []
        for j, areas in enumerate(groups, 1):
            area_set = set(areas)
            assigned = [t for t in trips if t["route"].split(">")[1] in area_set]
            by_type = {kind: [t for t in assigned if t["type"] == kind] for kind in types}
            drone_peak, battery_peak = {}, {}
            for kind, trlist in by_type.items():
                # The fixed assignment uses the existing schedule identity; peak concurrency is a lower bound
                # for independent resource needs when trip times are left unchanged.
                drone_peak[kind] = peak_concurrent(trlist, "start", "return")
                bat_events = []
                for t in trlist:
                    ready = float(t["battery_ready"])
                    bat_events.append({"start": float(t["start"]), "ready": ready})
                battery_peak[kind] = peak_concurrent(bat_events, "start", "ready") if bat_events else 0
            relay_assigned = [r for r in relay_rows if any(c["relay_trip"] and c["trip"] in {t["trip"] for t in assigned} for c in comm_rows)]
            relay_n = min(len(relay_units), peak_concurrent(relay_assigned, "start", "return")) if relay_assigned else 0
            energy_n = min(relay_stock.get("R", 0), peak_concurrent(relay_assigned, "start", "return")) if relay_assigned else 0
            group_rec = {"K": k, "group": j, "areas": areas,
                         "aircraft_A": drone_peak.get("A",0), "aircraft_B": drone_peak.get("B",0), "aircraft_C": drone_peak.get("C",0),
                         "battery_A": battery_peak.get("A",0), "battery_B": battery_peak.get("B",0), "battery_C": battery_peak.get("C",0),
                         "relay_aircraft": relay_n, "relay_energy": energy_n,
                         "box_count": sum(1 for b in boxes if b["area"] in area_set),
                         "mass_kg": round(sum(demand_by_area[a] for a in areas), 3),
                         "energy_kwh": round(sum(t["energy"] for t in assigned), 5),
                         "makespan_s": round(max((t["return"] for t in assigned), default=0), 2),
                         "first_deadline_violations": sum(1 for b in box_rows if b["area"] in area_set and b["first"] and b["deadline"] is not None and b["delivery"] > b["deadline"]),
                         "medical_violations": sum(1 for b in box_rows if b["area"] in area_set and b["type"] == "医疗物资" and b["delivery"] > b["expect"])}
            for kind in ("A", "B", "C"):
                group_rec[f"aircraft_gap_{kind}"] = max(0, group_rec[f"aircraft_{kind}"] - sum(d["type"] == kind for d in drones))
                group_rec[f"battery_gap_{kind}"] = max(0, group_rec[f"battery_{kind}"] - battery_stock.get(kind,0))
            group_rec["relay_aircraft_gap"] = max(0, relay_n - len(relay_units))
            group_rec["relay_energy_gap"] = max(0, energy_n - relay_stock.get("R",0))
            records.append(group_rec)
            outputs.append({"K": k, "group": j, "areas": ",".join(areas),
                            "A": group_rec["aircraft_A"], "B": group_rec["aircraft_B"], "C": group_rec["aircraft_C"],
                            "A_battery": group_rec["battery_A"], "B_battery": group_rec["battery_B"], "C_battery": group_rec["battery_C"],
                            "relay": relay_n, "relay_energy": energy_n})
        summaries.append({"K":k,"groups":records,"max_group_makespan_s":max(r["makespan_s"] for r in records),
                          "group_mass_cv":(math.sqrt(sum((r["mass_kg"]-sum(x["mass_kg"] for x in records)/k)**2 for r in records)/k)/(sum(x["mass_kg"] for x in records)/k)) if sum(x["mass_kg"] for x in records) else 0,
                          "q3_inherited_communication_disruptions":sum(not r["continuous_verified"] for r in comm_rows)})
    write_csv("q4_partition.csv", outputs, list(outputs[0]))
    save_json("q4_summary.json", {"partition_method":"geographic component split; keeps every multi-area trip intact",
                                   "fixed_plan_inherited":True,"partitions":summaries,
                                   "resource_rule":"independent concurrent peak counts from fixed Q2/Q3 schedule; no cross-group sharing",
                                   "communication_feasible":all(s["q3_inherited_communication_disruptions"] == 0 for s in summaries)})
    print((RES / "q4_summary.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    run()
