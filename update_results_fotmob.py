from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).parent / "data"

FOTMOB_URL = "https://www.fotmob.com/api/leagues?id=77&season=2026"

STAGES = [
    "16_delsfinale", "8_delsfinale", "kvartfinale", "semifinale",
    "finalist", "vm_vinnar", "solv", "bronse", "toppscorer"
]

EXPECTED_MAX = {
    "16_delsfinale": 32,
    "8_delsfinale": 16,
    "kvartfinale": 8,
    "semifinale": 4,
    "finalist": 2,
    "vm_vinnar": 1,
    "solv": 1,
    "bronse": 1,
}

TEAM_ALIASES = {
    "United States":"USA","USA":"USA","Bosnia and Herzegovina":"BIH","Bosnia-Herzegovina":"BIH",
    "Ivory Coast":"CIV","Côte d’Ivoire":"CIV","Cote d'Ivoire":"CIV","DR Congo":"COD","Congo DR":"COD",
    "Cape Verde":"CPV","Czechia":"CZE","Czech Republic":"CZE","Türkiye":"TUR","Turkey":"TUR",
    "Saudi Arabia":"KSA","South Korea":"KOR","Korea Republic":"KOR","New Zealand":"NZL","South Africa":"RSA",
    "Netherlands":"NED","Switzerland":"SUI","Germany":"GER","France":"FRA","Spain":"ESP","England":"ENG",
    "Portugal":"POR","Argentina":"ARG","Brazil":"BRA","Mexico":"MEX","Canada":"CAN","Norway":"NOR",
    "Morocco":"MAR","Paraguay":"PAR","Belgium":"BEL","Colombia":"COL","Egypt":"EGY","Algeria":"ALG",
    "Australia":"AUS","Croatia":"CRO","Ghana":"GHA","Japan":"JAP","Sweden":"SWE","Ecuador":"ECU",
    "Austria":"AUT","Senegal":"SEN","Uruguay":"URU","Scotland":"SCO","Tunisia":"TUN","Iran":"IRN",
    "Iraq":"IRQ","Jordan":"JOR","Qatar":"QAT","Panama":"PAN","Curacao":"CUR","Curaçao":"CUR",
    "Haiti":"HAI","Uzbekistan":"UZB"
}

def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def team_names() -> dict[str, str]:
    return {r["code"]: r["team"] for r in read_csv(DATA_DIR / "team_codes.csv")}

def fetch_json() -> Any:
    req = Request(FOTMOB_URL, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.fotmob.com/",
    })
    with urlopen(req, timeout=40) as response:
        data = json.loads(response.read().decode("utf-8"))
    (DATA_DIR / "fotmob_raw.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data

def code_from_team(obj: Any) -> str | None:
    if not isinstance(obj, dict):
        return TEAM_ALIASES.get(str(obj).strip()) if obj else None
    for key in ("ccode", "code", "countryCode", "threeLetterCode"):
        value = obj.get(key)
        if isinstance(value, str) and 2 <= len(value) <= 4:
            code = value.upper()
            return "ALG" if code == "DZA" else code
    for key in ("name", "longName", "fullName"):
        value = obj.get(key)
        if isinstance(value, str) and value.strip() in TEAM_ALIASES:
            return TEAM_ALIASES[value.strip()]
    return None

def team_pair(match: dict) -> tuple[str | None, str | None]:
    for home_key, away_key in (("home", "away"), ("homeTeam", "awayTeam")):
        if home_key in match and away_key in match:
            return code_from_team(match[home_key]), code_from_team(match[away_key])
    return None, None

def is_match(obj: dict) -> bool:
    return (
        isinstance(obj, dict)
        and (("home" in obj and "away" in obj) or ("homeTeam" in obj and "awayTeam" in obj))
        and any(k in obj for k in ("status", "statusStr", "score", "homeScore", "awayScore"))
    )

def label_from_node(node: dict, inherited: str = "") -> str:
    for key in ("round", "roundName", "stage", "stageName", "name", "title"):
        value = node.get(key)
        if isinstance(value, str):
            text = value.lower()
            if any(word in text for word in ("round of 32", "round of 16", "quarter", "semi", "final", "3rd", "third")):
                return value
    return inherited

def iter_matches(node: Any, inherited_label: str = ""):
    if isinstance(node, dict):
        current_label = label_from_node(node, inherited_label)
        if is_match(node):
            yield node, current_label
        for value in node.values():
            yield from iter_matches(value, current_label)
    elif isinstance(node, list):
        for item in node:
            yield from iter_matches(item, inherited_label)

def normalise_round(label: str) -> str:
    text = (label or "").lower().strip()
    if re.search(r"round\s*of\s*32|last\s*32|1/16", text):
        return "round32"
    if re.search(r"round\s*of\s*16|last\s*16|1/8", text):
        return "round16"
    if "quarter" in text:
        return "quarter"
    if "semi" in text:
        return "semi"
    if "3rd" in text or "third" in text or "bronze" in text:
        return "bronze"
    if re.search(r"\bfinal\b", text):
        return "final"
    return ""

def finished(match: dict) -> bool:
    status = match.get("status")
    if isinstance(status, dict):
        if status.get("finished") is True:
            return True
        status = status.get("short") or status.get("status") or status.get("reason")
    text = str(status or match.get("statusStr") or "").lower()
    return text in {"finished", "ft", "aet", "pen"} or "finished" in text

def numeric_score(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        for key in ("score", "current", "value"):
            if isinstance(value.get(key), int):
                return value[key]
    return None

def winner_loser(match: dict) -> tuple[str | None, str | None]:
    home, away = team_pair(match)
    home_obj = match.get("home") or match.get("homeTeam") or {}
    away_obj = match.get("away") or match.get("awayTeam") or {}

    if isinstance(home_obj, dict) and home_obj.get("winner") is True:
        return home, away
    if isinstance(away_obj, dict) and away_obj.get("winner") is True:
        return away, home

    penalty = match.get("penaltyScore") or match.get("penalties")
    if isinstance(penalty, dict):
        ph = numeric_score(penalty.get("home"))
        pa = numeric_score(penalty.get("away"))
        if ph is not None and pa is not None and ph != pa:
            return (home, away) if ph > pa else (away, home)

    score = match.get("score")
    if isinstance(score, dict):
        hs = numeric_score(score.get("home"))
        aws = numeric_score(score.get("away"))
    else:
        hs = numeric_score(match.get("homeScore"))
        aws = numeric_score(match.get("awayScore"))

    if hs is not None and aws is not None and hs != aws:
        return (home, away) if hs > aws else (away, home)
    return None, None

def existing_stages() -> dict[str, list[str]]:
    result = {stage: [] for stage in STAGES}
    for row in read_csv(DATA_DIR / "actual.csv"):
        stage = row.get("stage", "")
        code = row.get("actual", "")
        if stage in result and code and code not in result[stage]:
            result[stage].append(code)
    return result

def save(stage_codes: dict[str, list[str]]) -> None:
    names = team_names()
    rows = []
    for stage in STAGES:
        for slot, code in enumerate(stage_codes[stage], 1):
            rows.append({
                "stage": stage,
                "slot": slot,
                "actual": code,
                "actual_name": names.get(code, code),
                "source_note": "FotMob, validert før lagring",
            })
    with (DATA_DIR / "actual.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["stage","slot","actual","actual_name","source_note"]
        )
        writer.writeheader()
        writer.writerows(rows)

def main() -> None:
    current = existing_stages()
    found = {stage: [] for stage in STAGES}
    data = fetch_json()

    for match, inherited_label in iter_matches(data):
        round_key = normalise_round(inherited_label)
        home, away = team_pair(match)

        if round_key == "round32":
            for code in (home, away):
                if code and code not in found["16_delsfinale"]:
                    found["16_delsfinale"].append(code)

        if not finished(match):
            continue

        winner, loser = winner_loser(match)
        if not winner:
            continue

        target = {
            "round32": "8_delsfinale",
            "round16": "kvartfinale",
            "quarter": "semifinale",
            "semi": "finalist",
            "final": "vm_vinnar",
            "bronze": "bronse",
        }.get(round_key)

        if target and winner not in found[target]:
            found[target].append(winner)
        if round_key == "final" and loser and loser not in found["solv"]:
            found["solv"].append(loser)

    # Never replace a correct stage with an incomplete or oversized scrape.
    merged = current
    for stage, codes in found.items():
        maximum = EXPECTED_MAX.get(stage)
        unique_codes = list(dict.fromkeys(codes))
        if not unique_codes:
            continue
        if maximum is not None and len(unique_codes) > maximum:
            continue
        if len(unique_codes) >= len(current.get(stage, [])):
            merged[stage] = unique_codes

    save(merged)

    print("Fasit etter oppdatering:")
    for stage in STAGES:
        print(f"{stage:16} {len(merged[stage])}")

if __name__ == "__main__":
    main()
