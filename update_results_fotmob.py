from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).parent / "data"

FOTMOB_URLS = [
    "https://www.fotmob.com/api/leagues?id=77&season=2026",
    "https://www.fotmob.com/api/leagues?id=77&tab=fixtures&season=2026",
    "https://www.fotmob.com/leagues/77/overview/world-cup",
]

STAGES = ["16_delsfinale","8_delsfinale","kvartfinale","semifinale","finalist","vm_vinnar","solv","bronse","toppscorer"]

# Fallback basert på ferdige 32-delsfinalar vi allereie har brukt i prosjektet.
# Scriptet vil berre bruke desse dersom FotMob ikkje klarer å fylle runda.
FALLBACK = {
    "16_delsfinale": ["RSA","CAN","BRA","JAP","GER","PAR","NED","MAR","CIV","NOR","FRA","SWE","MEX","ECU","ENG","COD",
                      "BEL","SEN","USA","BIH","ESP","AUT","POR","CRO","SUI","ALG","AUS","EGY","ARG","CPV","COL","GHA"],
    "8_delsfinale": ["CAN","MAR","PAR","FRA","BRA","NOR","MEX","ENG","POR","ESP","USA","BEL","ARG","EGY","SUI","COL"],
    "kvartfinale": ["MAR","FRA","NOR","ENG"],
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

def load_team_codes() -> dict[str, str]:
    return {r["code"]: r["team"] for r in read_csv(DATA_DIR / "team_codes.csv")}

def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent":"Mozilla/5.0","Accept":"application/json,text/html;q=0.9,*/*;q=0.8"})
    with urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")

def extract_json(html: str) -> Any:
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("Fann ikkje __NEXT_DATA__.")
    return json.loads(m.group(1))

def fetch_fotmob_data() -> Any | None:
    errors = []
    for url in FOTMOB_URLS:
        try:
            txt = fetch(url)
            data = json.loads(txt) if txt.lstrip().startswith(("{","[")) else extract_json(txt)
            (DATA_DIR / "fotmob_raw.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return data
        except Exception as e:
            errors.append(f"{url}: {e}")
    (DATA_DIR / "fotmob_errors.txt").write_text("\n".join(errors), encoding="utf-8")
    return None

def iter_matches(obj: Any):
    if isinstance(obj, dict):
        keys = set(obj)
        if any(k in keys for k in ["home","away","homeTeam","awayTeam","teams"]) and any(k in keys for k in ["status","statusStr","score","scores","homeScore","awayScore"]):
            yield obj
        for v in obj.values():
            yield from iter_matches(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from iter_matches(x)

def code_from_team(x: Any) -> str | None:
    if isinstance(x, str):
        return TEAM_ALIASES.get(x.strip())
    if not isinstance(x, dict):
        return None
    for k in ["code","ccode","countryCode","shortName","threeLetterCode"]:
        v = x.get(k)
        if isinstance(v, str) and 2 <= len(v) <= 4:
            return v.upper()
    for k in ["name","longName","fullName","teamName"]:
        v = x.get(k)
        if isinstance(v, str) and v.strip() in TEAM_ALIASES:
            return TEAM_ALIASES[v.strip()]
    return None

def pair(m: dict) -> tuple[str|None, str|None]:
    for h,a in [("home","away"),("homeTeam","awayTeam"),("team1","team2")]:
        if h in m and a in m:
            return code_from_team(m.get(h)), code_from_team(m.get(a))
    teams = m.get("teams")
    if isinstance(teams, list) and len(teams) >= 2:
        return code_from_team(teams[0]), code_from_team(teams[1])
    return None, None

def all_text(obj: Any) -> str:
    out = []
    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
        elif isinstance(x, (str,int)):
            out.append(str(x))
    walk(obj)
    return " ".join(out).lower()

def round_key(m: dict) -> str:
    t = all_text(m)
    if re.search(r"round\s*of\s*32|1/16|last\s*32|32", t): return "round32"
    if re.search(r"round\s*of\s*16|1/8|last\s*16", t): return "round16"
    if "quarter" in t: return "quarter"
    if "semi" in t: return "semi"
    if "third" in t or "3rd" in t or "bronze" in t: return "bronze"
    if re.search(r"\bfinal\b", t): return "final"
    return ""

def finished(m: dict) -> bool:
    t = all_text(m)
    return any(x in t for x in ["finished","full-time","full time","after penalties","penalties","ft","aet"])

def score(m: dict) -> tuple[int|None,int|None]:
    s = m.get("score") or m.get("scores")
    if isinstance(s, dict):
        h = s.get("home"); a = s.get("away")
        if isinstance(h, dict): h = h.get("score") or h.get("current")
        if isinstance(a, dict): a = a.get("score") or a.get("current")
        if isinstance(h, int) and isinstance(a, int): return h,a
    h = m.get("homeScore"); a = m.get("awayScore")
    if isinstance(h, dict): h = h.get("score") or h.get("current")
    if isinstance(a, dict): a = a.get("score") or a.get("current")
    return (h if isinstance(h,int) else None, a if isinstance(a,int) else None)

def pen_score(m: dict) -> tuple[int|None,int|None]:
    p = m.get("penaltyScore") or m.get("penalties") or m.get("shootout")
    if isinstance(p, dict):
        h = p.get("home") or p.get("homeScore"); a = p.get("away") or p.get("awayScore")
        return (h if isinstance(h,int) else None, a if isinstance(a,int) else None)
    return None,None

def winner(m: dict) -> tuple[str|None,str|None]:
    h,a = pair(m)
    ph,pa = pen_score(m)
    if ph is not None and pa is not None and ph != pa: return (h,a) if ph>pa else (a,h)
    sh,sa = score(m)
    if sh is not None and sa is not None and sh != sa: return (h,a) if sh>sa else (a,h)
    return None,None

def save_actual(stage_codes: dict[str,list[str]]):
    names = load_team_codes()
    rows = []
    for st in STAGES:
        for i,c in enumerate(stage_codes.get(st, []), 1):
            rows.append({"stage":st,"slot":i,"actual":c,"actual_name":names.get(c,c),"source_note":"FotMob/fallback"})
    with (DATA_DIR/"actual.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["stage","slot","actual","actual_name","source_note"])
        w.writeheader(); w.writerows(rows)

def main():
    # Start with existing fasit, so we never wipe 8-dels points.
    stage_codes = {s: [] for s in STAGES}
    for r in read_csv(DATA_DIR/"actual.csv"):
        st, c = r.get("stage",""), r.get("actual","")
        if st in stage_codes and c and c not in stage_codes[st]:
            stage_codes[st].append(c)

    data = fetch_fotmob_data()
    log = []
    if data is not None:
        found = {s: [] for s in STAGES}
        for m in iter_matches(data):
            rk = round_key(m)
            h,a = pair(m)
            if rk == "round32":
                for c in [h,a]:
                    if c and c not in found["16_delsfinale"]:
                        found["16_delsfinale"].append(c)
            if not finished(m): 
                continue
            win, lose = winner(m)
            if not win: 
                continue
            mapping = {"round32":"8_delsfinale","round16":"kvartfinale","quarter":"semifinale","semi":"finalist","final":"vm_vinnar","bronze":"bronse"}
            if rk in mapping:
                st = mapping[rk]
                if win not in found[st]:
                    found[st].append(win)
                if rk == "final" and lose and lose not in found["solv"]:
                    found["solv"].append(lose)
                log.append({"round":rk,"home":h,"away":a,"winner":win,"stage":st})
        # Only replace a stage if FotMob found something for that stage
        for st, codes in found.items():
            if codes:
                stage_codes[st] = codes

    # Hard fallback for early knockout if stage is missing
    for st, codes in FALLBACK.items():
        if len(stage_codes.get(st, [])) == 0:
            stage_codes[st] = codes

    save_actual(stage_codes)
    (DATA_DIR/"fotmob_update_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Oppdatert fasit:")
    for st in STAGES:
        print(f"  {st:<15} {len(stage_codes.get(st, []))}")
    print("\nSjekk særleg at 8_delsfinale = 16. Då får 8-dels-tipsa poeng.")

if __name__ == "__main__":
    main()
