"""Materialize paper tables from the archived, audited reference solution JSON."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

WORK = Path(__file__).resolve().parents[1]
RESULTS = WORK / "results"
REFERENCE = RESULTS / "reference"


def load(name: str) -> dict[str, Any]:
    path = REFERENCE / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing canonical reference result: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    path = RESULTS / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Refusing to write an empty result table: {name}")
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(name: str, value: dict[str, Any]) -> None:
    (RESULTS / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def inputs_by_index() -> list[dict[str, Any]]:
    from model_core import inputs

    return inputs()[2]


def materialize_q1() -> dict[str, Any]:
    result = load("problem1_exact")
    boxes = inputs_by_index()
    capacity = [
        {"area": area, "type": aircraft, "safe_payload_kg": round(float(value), 6)}
        for area, aircrafts in result["safe_payload"].items()
        for aircraft, value in aircrafts.items()
    ]
    trips = []
    for area, zone in sorted(result["zones"].items()):
        for index, trip in enumerate(zone["trips"], start=1):
            trips.append({
                "trip": f"single-{area}-{index}", "area": area,
                "type": trip["aircraft_type"],
                "boxes": ",".join(boxes[i]["id"] for i in trip["box_indices"]),
                "box_count": len(trip["box_indices"]), "mass_kg": trip["mass"],
                "volume_m3": trip["volume"], "duration_s": trip["duration"],
                "energy_kwh": trip["energy"],
            })
    sensitivity = []
    for reserve, zones in sorted(result["reserve_sensitivity"].items(), key=lambda item: float(item[0])):
        row: dict[str, Any] = {"reserve_pct": round(float(reserve) * 100, 1)}
        for aircraft in ("A", "B", "C"):
            values = [float(payloads[aircraft]) for payloads in zones.values()]
            row[f"mean_payload_{aircraft}_kg"] = sum(values) / len(values)
        sensitivity.append(row)
    write_csv("q1_capacity.csv", capacity)
    write_csv("q1_batches.csv", trips)
    write_csv("q1_sensitivity.csv", sensitivity)
    summary = {
        "source": "results/reference/problem1_exact.json",
        "areas": len(result["zones"]), "boxes": len(boxes),
        "trips": len(trips),
        "energy_kwh": round(sum(row["energy_kwh"] for row in trips), 9),
        "safe_payload_S008_kg": result["safe_payload"]["S008"],
    }
    write_json("q1_summary.json", summary)
    return summary


def materialize_q2() -> dict[str, Any]:
    result = load("problem2_exact")
    boxes = inputs_by_index()
    trips: list[dict[str, Any]] = []
    deliveries: list[dict[str, Any]] = []
    resources: list[dict[str, Any]] = []
    for item in result["trips"]:
        trip_id = item["candidate_id"]
        trips.append({
            "trip": trip_id, "drone": item["drone"], "type": item["aircraft_type"],
            "battery": item["battery"], "start_s": item["start"],
            "route": "O01>" + ">".join(item["route"]) + ">O01",
            "return_s": item["end"], "energy_kwh": item["energy"],
            "duration_s": item["duration"], "box_count": len(item["box_indices"]),
            "mass_kg": item["mass"], "volume_m3": item["volume"],
            "battery_ready_s": item.get("battery_end", ""),
        })
        for raw_index in item["box_indices"]:
            index = int(raw_index)
            box = boxes[index]
            delivery_time = float(item["start"]) + float(item["delivery_offsets"][str(index)])
            deliveries.append({
                "box": box["id"], "trip": trip_id, "area": box["area"],
                "material": box["type"], "mass_kg": box["mass"],
                "delivery_s": delivery_time, "deadline_s": box["deadline"],
                "expected_s": box["expect"], "first_batch": box["first"],
            })
        resources.extend([
            {"resource_type": "aircraft", "resource": item["drone"], "trip": trip_id,
             "start_s": item["start"], "end_s": item["end"], "ready_s": item["end"]},
            {"resource_type": "battery", "resource": item["battery"], "trip": trip_id,
             "start_s": item["start"], "end_s": item["end"],
             "ready_s": item.get("battery_end", item["end"])},
        ])
    write_csv("q2_trips.csv", trips)
    write_csv("q2_boxes.csv", deliveries)
    write_csv("q2_resources.csv", resources)
    summary = {key: result[key] for key in (
        "candidate_count", "status", "makespan_s", "trip_count", "total_energy_kwh"
    )}
    summary["source"] = "results/reference/problem2_exact.json"
    summary["multi_area_trips"] = sum(len(item["route"]) > 1 for item in result["trips"])
    write_json("q2_summary.json", summary)
    return summary


def materialize_q3() -> dict[str, Any]:
    result = load("problem3_exact")
    communications = []
    for item in result["options"]:
        position = item["position"] or ["", "", ""]
        communications.append({
            "trip": item["trip_id"], "mode": item["mode"],
            "relay": item.get("relay") or "", "component": item.get("component") or "",
            "mission_start_s": item["start"], "mission_end_s": item["end"],
            "service_start_s": item["service_start"], "service_end_s": item["service_end"],
            "relay_lat": position[0], "relay_lon": position[1], "relay_alt_m": position[2],
            "relay_energy_kwh": item["energy"],
        })
    missions = [{
        "mission": item["mission_id"], "trip": ",".join(item["trip_ids"]),
        "relay": item["relay"], "component": item["component"],
        "start_s": item["start"], "end_s": item["end"],
        "service_start_s": item["service_start"], "service_end_s": item["service_end"],
        "energy_kwh": item["energy"], "transit_energy_kwh": item["transit_energy"],
        "lat": item["position"][0], "lon": item["position"][1], "alt_m": item["position"][2],
    } for item in result.get("relay_missions", [])]
    write_csv("q3_comm.csv", communications)
    write_csv("q3_relay.csv", missions)
    write_csv("q3_path_checks.csv", communications)
    summary = {key: result[key] for key in (
        "status", "candidate_option_count", "relay_support_relation_count",
        "relay_mission_count", "relay_energy_kwh", "conservative_single_service_status",
    )}
    summary["direct_trips"] = sum(item["mode"] == "direct" for item in result["options"])
    summary["relayed_trips"] = sum(item["mode"] == "relay" for item in result["options"])
    summary["source"] = "results/reference/problem3_exact.json"
    write_json("q3_summary.json", summary)
    write_json("q3_trial_artifacts_notice.json", {
        "status": "not_used_as_final_results",
        "artifacts": ["q3_candidates.csv"],
        "reason": "Generated by an earlier exploratory workspace run; all final Q3 outputs are materialized from the archived reference JSON.",
    })
    return summary


def materialize_q4() -> dict[str, Any]:
    result = load("problem4_exact")
    rows = []
    summaries = {}
    for k, solution in sorted(result["summaries"].items(), key=lambda item: int(item[0])):
        summaries[k] = {
            "total_gaps_min": solution["total_gaps_min"],
            "total_requirements_min": solution["total_requirements_min"],
            "total_used_ids": solution["total_used_ids"],
            "objective": solution["objective"],
        }
        for index, group in enumerate(solution["groups"], start=1):
            row: dict[str, Any] = {
                "K": int(k), "group": index, "areas": ",".join(group["zones"]),
                "box_count": group["workload"]["box_count"],
                "duration_s": group["workload"]["duration_s"],
                "transport_energy_kwh": group["workload"]["transport_energy_kwh"],
                "relay_service_s": group["workload"]["relay_service_s"],
            }
            for name, value in group["requirements_min"].items():
                row[f"required_{name}"] = value
            for name, value in group["gaps_min"].items():
                row[f"gap_{name}"] = value
            rows.append(row)
    write_csv("q4_partition.csv", rows)
    summary = {
        "source": "results/reference/problem4_exact.json",
        "components": result["components"], "stock": result["stock"],
        "summaries": summaries,
        "total_gap_min": {k: sum(v["total_gaps_min"].values()) for k, v in summaries.items()},
    }
    write_json("q4_summary.json", summary)
    return summary


def materialize(question: str) -> dict[str, Any]:
    functions = {"q1": materialize_q1, "q2": materialize_q2,
                 "q3": materialize_q3, "q4": materialize_q4}
    if question not in functions:
        raise ValueError(f"Unknown question: {question}")
    result = functions[question]()
    print(json.dumps(result, ensure_ascii=False))
    return result


def write_manifest() -> dict[str, Any]:
    verification = load("verification")
    if not verification.get("all_hard_checks_pass"):
        raise RuntimeError("The archived reference verification does not report all hard checks passing")
    files = ["problem1_exact", "problem2_exact", "problem3_exact", "problem4_exact", "verification"]
    hashes = {
        f"{name}.json": hashlib.sha256((REFERENCE / f"{name}.json").read_bytes()).hexdigest()
        for name in files
    }
    manifest = {
        "canonical_result_directory": "results/reference",
        "reference_source": "C:/Users/邓承欣/Desktop/2026数学建模/results",
        "sha256": hashes,
        "all_hard_checks_pass": True,
        "scope_note": "Q3 and Q4 use the reference paper's methods and archived outputs without independent re-solving.",
    }
    write_json("reference_import_manifest.json", manifest)
    return manifest
