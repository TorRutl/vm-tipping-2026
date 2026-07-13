from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import pandas as pd

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

ROUND_TARGET = {
    "round32": "8_delsfinale",
    "round16": "kvartfinale",
    "quarter": "semifinale",
    "semi": "finalist",
    "final": "vm_vinnar",
    "bronze": "bronse",
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
    "Haiti":"HAI","Uzbekistan":"UZB",
}

@dataclass
class LiveResult:
    actual: pd.DataFrame
    source: str
    message: str
    labels_found: list[str]

def _baseline() -> pd.DataFrame:
    path = DATA_DIR / "actual_baseline.csv"
    df = pd.read_csv(path, dtype={"actual": str})
    required = {"stage", "slot", "actual", "actual_name"}
    if not required.issubset(df.columns):
        raise ValueError("actual_baseline.csv har feil kolonnar")
    return df

def _team_names() -> dict[str, str]:
    df = pd.read_csv(DATA_DIR / "team_codes.csv", dtype=str)
    return dict(zip(df["code"], df["team"]))

def _fetch_json() -> Any:
    req = Request(FOTMOB_URL, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.fotmob.com/",
    })
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def _code(obj: Any) -> str | None:
    if isinstance(obj, str):
        return TEAM_ALIASES.get(obj.strip())
    if not isinstance(obj, dict):
        return None

    for key in ("ccode", "code", "countryCode", "threeLetterCode"):
        value = obj.get(key)
        if isinstance(value, str) and 2 <= len(value) <= 4:
            code = value.upper()
            return {"DZA": "ALG", "IRN": "IRN"}.get(code, code)

    for key in ("name", "longName", "fullName"):
        value = obj.get(key)
        if isinstance(value, str) and value.strip() in TEAM_ALIASES:
            return TEAM_ALIASES[value.strip()]
    return None

def _pair(match: dict) -> tuple[str | None, str | None]:
    for home_key, away_key in (("home", "away"), ("homeTeam", "awayTeam")):
        if home_key in match and away_key in match:
            return _code(match[home_key]), _code(match[away_key])
    return None, None

def _is_match(obj: dict) -> bool:
    return (
        isinstance(obj, dict)
        and (("home" in obj and "away" in obj) or ("homeTeam" in obj and "awayTeam" in obj))
        and any(k in obj for k in ("status", "statusStr", "score", "homeScore", "awayScore"))
    )

def _round_label(node: dict, inherited: str = "") -> str:
    for key in ("round", "roundName", "stage", "stageName", "title"):
        value = node.get(key)
        if isinstance(value, dict):
            value = value.get("name")
        if isinstance(value, str):
            text = value.lower()
            if any(token in text for token in (
                "round of 32", "round of 16", "quarter", "semi", "final", "3rd", "third", "bronze"
            )):
                return value
    return inherited

def _iter_matches(node: Any, inherited: str = ""):
    if isinstance(node, dict):
        label = _round_label(node, inherited)
        if _is_match(node):
            yield node, label
        for value in node.values():
            yield from _iter_matches(value, label)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_matches(item, inherited)

def _normalise_round(label: str) -> str:
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

def _finished(match: dict) -> bool:
    status = match.get("status")
    if isinstance(status, dict):
        if status.get("finished") is True:
            return True
        status = status.get("short") or status.get("status") or status.get("reason")
    text = str(status or match.get("statusStr") or "").lower().strip()
    return text in {"finished", "ft", "aet", "pen"} or "finished" in text

def _number(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        for key in ("score", "current", "value"):
            if isinstance(value.get(key), int):
                return value[key]
    return None

def _winner_loser(match: dict) -> tuple[str | None, str | None]:
    home, away = _pair(match)
    home_obj = match.get("home") or match.get("homeTeam") or {}
    away_obj = match.get("away") or match.get("awayTeam") or {}

    if isinstance(home_obj, dict) and home_obj.get("winner") is True:
        return home, away
    if isinstance(away_obj, dict) and away_obj.get("winner") is True:
        return away, home

    penalty = match.get("penaltyScore") or match.get("penalties")
    if isinstance(penalty, dict):
        ph = _number(penalty.get("home"))
        pa = _number(penalty.get("away"))
        if ph is not None and pa is not None and ph != pa:
            return (home, away) if ph > pa else (away, home)

    score = match.get("score")
    if isinstance(score, dict):
        hs = _number(score.get("home"))
        aws = _number(score.get("away"))
    else:
        hs = _number(match.get("homeScore"))
        aws = _number(match.get("awayScore"))

    if hs is not None and aws is not None and hs != aws:
        return (home, away) if hs > aws else (away, home)
    return None, None

def _stage_sets(df: pd.DataFrame) -> dict[str, list[str]]:
    result = {stage: [] for stage in STAGES}
    for _, row in df.iterrows():
        stage = str(row["stage"])
        code = str(row["actual"])
        if stage in result and code and code != "nan" and code not in result[stage]:
            result[stage].append(code)
    return result

def _to_dataframe(stage_codes: dict[str, list[str]], note: str) -> pd.DataFrame:
    names = _team_names()
    rows = []
    for stage in STAGES:
        for slot, code in enumerate(stage_codes.get(stage, []), 1):
            rows.append({
                "stage": stage,
                "slot": slot,
                "actual": code,
                "actual_name": names.get(code, code),
                "source_note": note,
            })
    return pd.DataFrame(rows, columns=["stage","slot","actual","actual_name","source_note"])

def get_live_actual() -> LiveResult:
    baseline = _baseline()
    merged = _stage_sets(baseline)

    try:
        data = _fetch_json()
    except Exception as exc:
        return LiveResult(
            actual=baseline,
            source="baseline",
            message=f"FotMob kunne ikkje hentast: {exc}",
            labels_found=[],
        )

    found = {stage: [] for stage in STAGES}
    labels = []

    for match, label in _iter_matches(data):
        if label and label not in labels:
            labels.append(label)

        round_key = _normalise_round(label)
        home, away = _pair(match)

        if round_key == "round32":
            for code in (home, away):
                if code and code not in found["16_delsfinale"]:
                    found["16_delsfinale"].append(code)

        if not _finished(match):
            continue

        winner, loser = _winner_loser(match)
        if not winner:
            continue

        target = ROUND_TARGET.get(round_key)
        if target and winner not in found[target]:
            found[target].append(winner)

        if round_key == "final" and loser and loser not in found["solv"]:
            found["solv"].append(loser)

    # Merge only sensible data. Never delete good baseline data.
    changes = []
    for stage, codes in found.items():
        unique = list(dict.fromkeys(codes))
        maximum = EXPECTED_MAX.get(stage)

        if not unique:
            continue
        if maximum is not None and len(unique) > maximum:
            continue

        before = list(merged.get(stage, []))
        for code in unique:
            if code not in merged[stage]:
                merged[stage].append(code)

        if maximum is not None:
            merged[stage] = merged[stage][:maximum]

        if merged[stage] != before:
            changes.append(f"{stage}: {len(before)}→{len(merged[stage])}")

    note = "FotMob live + trygg baseline"
    actual = _to_dataframe(merged, note)

    message = "Oppdatert frå FotMob."
    if changes:
        message += " Endringar: " + ", ".join(changes)
    else:
        message += " Ingen nye lag sidan baseline."

    return LiveResult(actual=actual, source="fotmob", message=message, labels_found=labels)
