from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).parent / "data"
API_BASE = "https://v3.football.api-sports.io"

# API-Football usually uses these round names for World Cup knockout.
# If the API returns a slightly different spelling, run this once and inspect
# data/api_football_fixtures.json or data/update_log.json.
ROUND_TO_STAGE = {
    "Round of 32": "8_delsfinale",      # winner reaches 8-delsfinale / round of 16
    "Round of 16": "kvartfinale",       # winner reaches quarterfinal
    "Quarter-finals": "semifinale",     # winner reaches semifinal
    "Quarter Finals": "semifinale",
    "Semi-finals": "finalist",          # winner reaches final
    "Semi Finals": "finalist",
    "Final": "vm_vinnar",
}

THIRD_PLACE_ROUNDS = {
    "3rd Place Final",
    "3rd Place Play-Off",
    "Third Place Play-Off",
    "Third-place play-off",
}

def api_get(path: str, params: dict) -> dict:
    key = os.environ.get("APIFOOTBALL_KEY")
    if not key:
        raise SystemExit(
            "Manglar APIFOOTBALL_KEY.\n\n"
            "Legg inn nøkkelen slik i PowerShell:\n"
            '  setx APIFOOTBALL_KEY "DIN_NOKKEL"\n\n'
            "Lukk PowerShell og opne på nytt etterpå."
        )

    url = f"{API_BASE}{path}?{urlencode(params)}"
    req = Request(url, headers={"x-apisports-key": key})

    with urlopen(req, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))

def load_team_codes() -> dict[str, str]:
    with (DATA_DIR / "team_codes.csv").open("r", encoding="utf-8", newline="") as f:
        return {r["code"]: r["team"] for r in csv.DictReader(f)}

def save_actual(rows: list[dict]) -> None:
    fields = ["stage", "slot", "actual", "actual_name", "source_note"]
    with (DATA_DIR / "actual.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def normalise_round(round_name: str | None) -> str:
    if not round_name:
        return ""
    # API can return e.g. "Round of 16" or "World Cup - Round of 16"
    name = str(round_name).strip()
    name = re.sub(r"^World Cup\s*-\s*", "", name, flags=re.I)
    return name

def is_finished(fixture: dict) -> bool:
    status = fixture.get("fixture", {}).get("status", {})
    short = status.get("short")
    # FT = full time, AET = after extra time, PEN = penalties
    return short in {"FT", "AET", "PEN"}

def winner_code(fixture: dict) -> str | None:
    teams = fixture.get("teams", {})
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}

    if home.get("winner") is True:
        return home.get("code")
    if away.get("winner") is True:
        return away.get("code")

    # Fallback: compare goals, then penalty score.
    goals = fixture.get("goals", {}) or {}
    h, a = goals.get("home"), goals.get("away")
    if isinstance(h, int) and isinstance(a, int) and h != a:
        return home.get("code") if h > a else away.get("code")

    score = fixture.get("score", {}) or {}
    penalty = score.get("penalty", {}) or {}
    ph, pa = penalty.get("home"), penalty.get("away")
    if isinstance(ph, int) and isinstance(pa, int) and ph != pa:
        return home.get("code") if ph > pa else away.get("code")

    return None

def loser_code(fixture: dict) -> str | None:
    teams = fixture.get("teams", {})
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}
    win = winner_code(fixture)
    if not win:
        return None
    if home.get("code") == win:
        return away.get("code")
    if away.get("code") == win:
        return home.get("code")
    return None

def build_actual_from_api() -> tuple[list[dict], list[dict]]:
    team_names = load_team_codes()
    data = api_get("/fixtures", {"league": 1, "season": 2026})
    (DATA_DIR / "api_football_fixtures.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if data.get("errors"):
        raise SystemExit(f"API-feil: {data['errors']}")

    stage_codes: dict[str, list[str]] = {
        "16_delsfinale": [],
        "8_delsfinale": [],
        "kvartfinale": [],
        "semifinale": [],
        "finalist": [],
        "vm_vinnar": [],
        "solv": [],
        "bronse": [],
        "toppscorer": [],  # handled later manually/API top scorers
    }
    log_rows = []

    # First: determine all teams that reached Round of 32.
    # We can infer this from the Round of 32 fixtures: both teams in those matches reached 16-delsfinale in your scoring.
    for fx in data.get("response", []):
        league = fx.get("league", {}) or {}
        round_name = normalise_round(league.get("round"))
        teams = fx.get("teams", {}) or {}
        home = (teams.get("home") or {}).get("code")
        away = (teams.get("away") or {}).get("code")

        if round_name == "Round of 32":
            for code in [home, away]:
                if code and code not in stage_codes["16_delsfinale"]:
                    stage_codes["16_delsfinale"].append(code)

        if not is_finished(fx):
            continue

        win = winner_code(fx)
        lose = loser_code(fx)
        if not win:
            continue

        if round_name in ROUND_TO_STAGE:
            stage = ROUND_TO_STAGE[round_name]
            if win not in stage_codes[stage]:
                stage_codes[stage].append(win)
            log_rows.append({
                "fixture_id": fx.get("fixture", {}).get("id"),
                "round": round_name,
                "stage_added": stage,
                "winner": win,
                "loser": lose or "",
            })

            if round_name == "Final" and lose:
                if lose not in stage_codes["solv"]:
                    stage_codes["solv"].append(lose)

        if round_name in THIRD_PLACE_ROUNDS:
            if win not in stage_codes["bronse"]:
                stage_codes["bronse"].append(win)

    rows = []
    for stage, codes in stage_codes.items():
        for i, code in enumerate(codes, start=1):
            rows.append({
                "stage": stage,
                "slot": i,
                "actual": code,
                "actual_name": team_names.get(code, code),
                "source_note": "Henta automatisk frå API-Football",
            })

    return rows, log_rows

def main() -> None:
    rows, log_rows = build_actual_from_api()
    save_actual(rows)

    (DATA_DIR / "update_log.json").write_text(
        json.dumps(log_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Oppdaterte data/actual.csv med {len(rows)} fasitlinjer.")
    print("No kan du køyre: python -m streamlit run app.py")

if __name__ == "__main__":
    main()
