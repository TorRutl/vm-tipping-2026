from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import pandas as pd

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
    "finalist": "Finalistar",
    "vm_vinnar": "VM-vinnar",
    "solv": "2. plass",
    "bronse": "3. plass",
    "toppscorer": "Toppscorar",
}

def load_points(data_dir: Path = DATA_DIR) -> dict[str, int]:
    df = pd.read_csv(data_dir / "points.csv")
    return dict(zip(df["stage"], df["points_per_correct"].astype(int)))

def load_predictions(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    return pd.read_csv(data_dir / "predictions.csv", dtype={"pick": str})

def score_all(actual: pd.DataFrame, data_dir: Path = DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    predictions = load_predictions(data_dir)
    points = load_points(data_dir)

    actual_sets = {
        stage: set(group["actual"].dropna().astype(str))
        for stage, group in actual.groupby("stage")
    }

    leaderboard_rows = []
    detail_rows = []

    for name, person in predictions.groupby("name", sort=True):
        stage_scores = {stage: 0 for stage in STAGE_ORDER}

        for _, row in person.iterrows():
            stage = str(row["stage"])
            pick = str(row["pick"]).strip()
            if stage not in points or not pick or pick == "nan":
                continue

            known = actual_sets.get(stage, set())
            correct = pick in known
            earned = points[stage] if correct else 0
            stage_scores[stage] += earned

            detail_rows.append({
                "name": name,
                "stage": stage,
                "stage_label": STAGE_LABELS.get(stage, stage),
                "slot": int(row["slot"]),
                "pick": pick,
                "pick_name": row.get("pick_name", pick),
                "status": "riktig" if correct else ("uavklart" if not known else "feil"),
                "points": earned,
            })

        total = sum(stage_scores.values())
        leaderboard_rows.append({"name": name, "total": total, **stage_scores})

    board = pd.DataFrame(leaderboard_rows).sort_values(
        ["total", "name"], ascending=[False, True]
    ).reset_index(drop=True)

    board["plass"] = board["total"].rank(method="min", ascending=False).astype(int)
    if len(board):
        board["bak_leiar"] = int(board.iloc[0]["total"]) - board["total"]
    else:
        board["bak_leiar"] = 0

    details = pd.DataFrame(detail_rows)
    return board, details
