"""Q3: DEM sampled two-way communications and relay candidate evaluation."""
from __future__ import annotations

import math

from model_core import RES, Terrain, communications, endpoint, endpoint_tx, hav, inputs, link, num, relay_data, save_json, write_csv
from q2 import run as run_q2


def device(category, comm):
    return endpoint_tx(category, comm)


def flight_positions(center, node, drone_params, terrain, spacing=500):
    start = endpoint(center, center["z"])
    finish = endpoint(node, node["z"] + 30)
    d = hav(center, node)
    cruise = max(terrain.profile(center, node)[1][i][2] or 0 for i in range(len(terrain.profile(center, node)[1])) if terrain.profile(center, node)[1][i][2] is not None) + 50
    horizontal = max(2, int(math.ceil(d / spacing)))
    climb = max(0, cruise - start["alt"])
    descend = max(0, cruise - finish["alt"])
    t_up = climb / num(drone_params["最大爬升速度（m/s）"])
    t_cruise = d / num(drone_params["计划巡航速度（m/s）"])
    t_down = descend / num(drone_params["最大下降速度（m/s）"])
    pos = []
    for j in range(horizontal + 1):
        f = j / horizontal
        lon = start["lon"] + f * (finish["lon"] - start["lon"])
        lat = start["lat"] + f * (finish["lat"] - start["lat"])
        outbound_alt = min(start["alt"] + f * horizontal * 0 + cruise, cruise)
        if f < 0.08:
            alt = start["alt"] + (cruise - start["alt"]) * f / 0.08
        elif f > 0.92:
            alt = cruise - (cruise - finish["alt"]) * (f - 0.92) / 0.08
        else:
            alt = cruise
        pos.append({"lon": lon, "lat": lat, "alt": alt, "fraction": f, "leg": "outbound"})
    for p in reversed(pos[:-1]):
        p = dict(p); p["leg"] = "return"
        pos.append(p)
    duration = t_up + t_cruise + t_down + t_down + t_cruise + t_up
    return pos, duration, cruise


def candidate_points(center, nodes, terrain, max_agl):
    base = [center, *nodes.values()]
    for a, b in zip(nodes.values(), list(nodes.values())[1:]):
        base.append({"lon": (a["lon"] + b["lon"]) / 2, "lat": (a["lat"] + b["lat"]) / 2, "id": "mid"})
    unique = {}
    for p in base:
        ground = terrain.pixel(p["lon"], p["lat"])
        if ground is None:
            continue
        for agl in (100, 200, max_agl):
            if agl <= max_agl:
                key = (round(p["lon"], 7), round(p["lat"], 7), agl)
                unique[key] = {"lon": p["lon"], "lat": p["lat"], "ground": ground,
                               "alt": ground + agl, "agl": agl}
    return list(unique.values())


def run():
    center, nodes, boxes, types, drones = inputs()
    transport, box_rows = run_q2()
    terrain = Terrain()
    comm = communications()
    relay_params, relays, relay_stock = relay_data()
    g01 = endpoint(center, center["z"] + comm[("固定网关 G01", "天线离地高度（m）")])
    tx_u = device("运输无人机", comm)
    tx_ra = device("中继接入端", comm)
    tx_rb = device("中继回传端", comm)
    tx_g = device("固定网关 G01", comm)
    max_agl = num(relay_params["最大悬停离地高度（m）"])
    candidates = candidate_points(center, nodes, terrain, max_agl)
    trip_by_id = {r["trip"]: r for r in transport}
    trajectories = {}
    direct_rows = []
    for tr in transport:
        area = tr["route"].split(">")[1]
        pos, _, cruise = flight_positions(center, nodes[area], types[tr["type"]], terrain)
        trajectories[tr["trip"]] = pos
        direct_bad = 0
        worst_margin = float("inf")
        for p in pos:
            obs = endpoint(p, p["alt"])
            r = link(terrain, obs, g01, tx_u, tx_g, comm)
            direct_bad += not r["available"]
            worst_margin = min(worst_margin, r["margin_db"])
        direct_rows.append({"trip": tr["trip"], "area": area, "samples": len(pos),
                            "direct_unavailable_samples": direct_bad, "direct_worst_margin_db": round(worst_margin, 3),
                            "cruise_alt_m": round(cruise, 2), "direct_continuous": direct_bad == 0})
    uncovered = [r for r in direct_rows if not r["direct_continuous"]]
    candidate_scores = []
    scored = []
    for cidx, cand in enumerate(candidates):
        failed = 0
        minimum = float("inf")
        covered_trips = 0
        for row in uncovered:
            all_ok = True
            for p in trajectories[row["trip"]]:
                obs = endpoint(p, p["alt"])
                access = link(terrain, obs, cand, tx_u, tx_ra, comm)
                backhaul = link(terrain, cand, g01, tx_rb, tx_g, comm)
                margin = min(access["margin_db"], backhaul["margin_db"])
                minimum = min(minimum, margin)
                if not (access["available"] and backhaul["available"]):
                    failed += 1
                    all_ok = False
            covered_trips += all_ok
        score = (failed, -covered_trips, -minimum, cand["agl"])
        scored.append((score, cand, failed, covered_trips, minimum))
    scored.sort(key=lambda item: item[0])
    chosen = scored[0][1] if scored else None
    comm_rows, link_rows = [], []
    for row in direct_rows:
        mode = "直连"
        relay_id = ""
        min_margin = row["direct_worst_margin_db"]
        if not row["direct_continuous"]:
            mode = "通信中断"
            if chosen:
                ok = True
                margins = []
                for p in trajectories[row["trip"]]:
                    obs = endpoint(p, p["alt"])
                    access = link(terrain, obs, chosen, tx_u, tx_ra, comm)
                    backhaul = link(terrain, chosen, g01, tx_rb, tx_g, comm)
                    margins.extend([access["margin_db"], backhaul["margin_db"]])
                    ok = ok and access["available"] and backhaul["available"]
                if ok:
                    mode, relay_id = "中继候选可覆盖", "R01"
                    min_margin = min(margins)
            comm_rows.append({"trip": row["trip"], "stage": "完整往返轨迹", "start": trip_by_id[row["trip"]]["start"],
                              "end": trip_by_id[row["trip"]]["return"], "mode": mode, "relay_trip": relay_id,
                              "continuous_verified": mode == "中继候选可覆盖"})
        else:
            comm_rows.append({"trip": row["trip"], "stage": "完整往返轨迹", "start": trip_by_id[row["trip"]]["start"],
                              "end": trip_by_id[row["trip"]]["return"], "mode": "直连", "relay_trip": "",
                              "continuous_verified": True})
        link_rows.append({**row, "selected_mode": mode, "minimum_path_margin_db": round(min_margin, 3)})
    relay_rows = []
    if chosen and any(r["mode"] == "中继候选可覆盖" for r in comm_rows):
        service_end = max(r["end"] for r in comm_rows if r["relay_trip"])
        d = hav(center, chosen)
        cruise = max_elev = max(terrain.profile(center, chosen)[1][i][2] or 0 for i in range(len(terrain.profile(center, chosen)[1])) if terrain.profile(center, chosen)[1][i][2] is not None) + 50
        climb = max(0, cruise - center["z"])
        down = max(0, cruise - chosen["alt"])
        flight_s = 2 * d / num(relay_params["计划巡航速度（m/s）"]) + 2 * climb / num(relay_params["最大爬升速度（m/s）"]) + 2 * down / num(relay_params["最大下降速度（m/s）"])
        flight_kwh = 2 * d / num(relay_params["计划巡航速度（m/s）"]) * num(relay_params["巡航功率（kW）"]) / 3600
        flight_kwh += 2 * num(relay_params["计划起飞总质量（kg）"]) * 9.81 * climb / (3.6e6 * max(num(relay_params["爬升能耗效率"]), 0.01))
        fixed_s = num(relay_params["工位固定准备时间（s）"]) + num(relay_params["建链时间（s）"])
        p_hover = num(relay_params["悬停功率（kW）"]) + num(relay_params["通信附加功率（kW）"])
        max_hover_h = max(0, (num(relay_params["能源组件可用能量（kWh）"]) * (1-num(relay_params["返航电量下限（%）"])/100) - flight_kwh) / p_hover)
        sortie_capacity = max(1.0, max_hover_h * 3600)
        start_service = min(r["start"] for r in comm_rows if r["relay_trip"])
        remaining = max(0, service_end - start_service)
        sorties = max(1, math.ceil(remaining / sortie_capacity))
        per_sortie_service = remaining / sorties
        total_energy = sorties * (flight_kwh + per_sortie_service * p_hover / 3600)
        for i in range(sorties):
            s0 = start_service + i * per_sortie_service
            s1 = min(service_end, s0 + per_sortie_service)
            relay_rows.append({"relay_trip": f"R{i+1:03d}", "relay_drone": relays[i % len(relays)][0],
                               "energy_unit": f"R-E{(i % relay_stock.get('R', 1))+1:02d}", "start": round(max(0,s0-flight_s-fixed_s),2),
                               "lon": round(chosen["lon"],7), "lat": round(chosen["lat"],7), "alt": round(chosen["alt"],2),
                               "link": round(s0,2), "service_end": round(s1,2), "return": round(s1+flight_s,2),
                               "energy": round(flight_kwh+per_sortie_service*p_hover/3600,4),
                               "service_s": round(s1-s0,2)})
    for row in comm_rows:
        if row["relay_trip"]:
            row["relay_trip"] = "R001"
    write_csv("q3_path_checks.csv", link_rows, list(link_rows[0]))
    write_csv("q3_comm.csv", comm_rows, list(comm_rows[0]))
    write_csv("q3_relay.csv", relay_rows, list(relay_rows[0]) if relay_rows else
              ["relay_trip","relay_drone","energy_unit","start","lon","lat","alt","link","service_end","return","energy","service_s"])
    write_csv("q3_candidates.csv", [{"rank": i+1, "lon": s[1]["lon"], "lat": s[1]["lat"], "alt": s[1]["alt"],
                                     "agl": s[1]["agl"], "uncovered_samples": s[2], "covered_trips": s[3],
                                     "worst_margin_db": s[4]} for i,s in enumerate(scored[:20])],
              ["rank","lon","lat","alt","agl","uncovered_samples","covered_trips","worst_margin_db"])
    summary = {"direct_continuous_trips": sum(r["direct_continuous"] for r in direct_rows),
               "direct_incomplete_trips": sum(not r["direct_continuous"] for r in direct_rows),
               "relay_continuous_trips": sum(r["mode"] == "中继候选可覆盖" for r in comm_rows),
               "communication_disruptions": sum(not r["continuous_verified"] for r in comm_rows),
               "relay_sorties": len(relay_rows), "relay_candidate": chosen,
               "dem_sample_spacing_m": 30, "trajectory_spacing_m": 500,
               "relay_aircraft_inventory": len(relays), "relay_energy_inventory": relay_stock,
               "limitations": ["relay position is a static candidate selected over sampled trajectories",
                               "relay sortie/component continuity requires independent audit",
                               "terrain model uses raster elevations without curvature/refraction"],
               "communication_all_continuous": all(r["continuous_verified"] for r in comm_rows)}
    save_json("q3_summary.json", summary)
    print((RES / "q3_summary.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    run()
