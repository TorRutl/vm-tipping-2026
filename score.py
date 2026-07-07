from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

DATA_DIR = Path(__file__).parent / "data"

STAGE_ORDER = [
    "16_delsfinale",
    "8_delsfinale",
    "kvartfinale",
    "semifinale",
    "finalist",
    "vm_vinnar",
    "solv",
    "bronse",
    "toppscorer",
]

STAGE_LABELS = {
    "16_delsfinale": "16-delsfinale",
    "8_delsfinale": "8-delsfinale",
    "kvartfinale": "Kvartfinale",
    "semifinale": "Semifinale",
    "finalist": "Finale/finalistar",
    "vm_vinnar": "VM-vinnar",
    "solv": "Sølv",
    "bronse": "Bronse",
    "toppscorer": "Toppscorar",
}

def read_csv_dict(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def load_points(data_dir: Path = DATA_DIR) -> dict[str, int]:
    rows = read_csv_dict(data_dir / "points.csv")
    return {r["stage"]: int(r["points_per_correct"]) for r in rows}

def load_team_codes(data_dir: Path = DATA_DIR) -> dict[str, str]:
    rows = read_csv_dict(data_dir / "team_codes.csv")
    return {r["code"]: r["team"] for r in rows}

def load_predictions(data_dir: Path = DATA_DIR) -> list[dict]:
    return read_csv_dict(data_dir / "predictions.csv")

def load_actual(data_dir: Path = DATA_DIR) -> list[dict]:
    return read_csv_dict(data_dir / "actual.csv")

def actual_sets(actual_rows: list[dict]) -> dict[str, set[str]]:
    sets: dict[str, set[str]] = defaultdict(set)
    for r in actual_rows:
        val = (r.get("actual") or "").strip()
        if val:
            sets[r["stage"]].add(val)
    return sets

def score_all(data_dir: Path = DATA_DIR) -> tuple[list[dict], list[dict]]:
    predictions = load_predictions(data_dir)
    actual = load_actual(data_dir)
    points = load_points(data_dir)
    team_names = load_team_codes(data_dir)
    actual_by_stage = actual_sets(actual)

    by_person: dict[str, list[dict]] = defaultdict(list)
    for row in predictions:
        by_person[row["name"]].append(row)

    leaderboard = []
    details = []

    for name, rows in sorted(by_person.items()):
        stage_points = {s: 0 for s in STAGE_ORDER}
        possible_remaining = {s: 0 for s in STAGE_ORDER}

        for r in rows:
            stage = r["stage"]
            pick = (r["pick"] or "").strip()
            if stage not in points or not pick:
                continue

            is_correct = pick in actual_by_stage.get(stage, set())
            earned = points[stage] if is_correct else 0
            stage_points[stage] += earned

            # A simple "still alive" marker: if the future actual stage is empty, we do not know yet.
            unresolved = len(actual_by_stage.get(stage, set())) == 0
            if unresolved:
                possible_remaining[stage] += points[stage]

            details.append({
                "name": name,
                "stage": stage,
                "stage_label": STAGE_LABELS.get(stage, stage),
                "slot": int(r["slot"]),
                "pick": pick,
                "pick_name": r.get("pick_name") or team_names.get(pick, pick),
                "correct": "Ja" if is_correct else "Nei",
                "points": earned,
            })

        total = sum(stage_points.values())
        max_remaining = sum(possible_remaining.values())
        out = {
            "name": name,
            "total": total,
            "max_remaining_simple": max_remaining,
            "max_total_simple": total + max_remaining,
        }
        for s in STAGE_ORDER:
            out[s] = stage_points[s]
        leaderboard.append(out)

    leaderboard.sort(key=lambda r: (-r["total"], r["name"]))
    for i, r in enumerate(leaderboard, start=1):
        r["rank"] = i

    return leaderboard, details

def write_outputs(data_dir: Path = DATA_DIR) -> None:
    leaderboard, details = score_all(data_dir)

    with (data_dir / "leaderboard.csv").open("w", encoding="utf-8", newline="") as f:
        fields = ["rank", "name", "total", "max_total_simple", "max_remaining_simple"] + STAGE_ORDER
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(leaderboard)

    with (data_dir / "details.csv").open("w", encoding="utf-8", newline="") as f:
        fields = ["name", "stage", "stage_label", "slot", "pick", "pick_name", "correct", "points"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(details)

if __name__ == "__main__":
    write_outputs()
    board, _ = score_all()
    print("VM-tipping - topp 10")
    for r in board[:10]:
        print(f"{r['rank']:>2}. {r['name']:<15} {r['total']:>3} p")
