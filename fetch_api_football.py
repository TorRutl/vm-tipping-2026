"""
Valfritt: automatisk henting av resultat frå API-Football.

Du treng ein API-nøkkel frå API-SPORTS/API-Football.
Set han som miljøvariabel:

Windows PowerShell:
    setx APIFOOTBALL_KEY "din_nokkel"

Mac/Linux:
    export APIFOOTBALL_KEY="din_nokkel"

Køyr:
    python fetch_api_football.py

Merk:
Dette skriptet hentar rå fixtures til data/api_football_fixtures.json.
Neste steg er å mappe fixture-vinnarar til actual.csv automatisk.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

OUT = Path(__file__).parent / "data" / "api_football_fixtures.json"

def main() -> None:
    key = os.environ.get("APIFOOTBALL_KEY")
    if not key:
        raise SystemExit("Manglar APIFOOTBALL_KEY. Sjå kommentar øvst i fila.")

    url = "https://v3.football.api-sports.io/fixtures?league=1&season=2026"
    req = Request(url, headers={"x-apisports-key": key})

    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Lagra {OUT}")

if __name__ == "__main__":
    main()
