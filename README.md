# VM-tipping v2 live

Dette er ei ny og ryddigare utgåve.

## Viktig skilnad
Appen hentar FotMob-data i minnet og skriv ikkje over `actual.csv` i Streamlit Cloud.

`data/actual_baseline.csv` er trygg fasit fram til semifinalane. Nye resultat frå FotMob blir lagde oppå denne i minnet.

## Last opp til GitHub
Erstatt heile innhaldet i repoet med filene i denne mappa, eller minst:

- `app.py`
- `score.py`
- `live_data.py`
- `requirements.txt`
- `.streamlit/config.toml`
- `data/predictions.csv`
- `data/team_codes.csv`
- `data/points.csv`
- `data/actual_baseline.csv`

Du kan slette gamle:
- `update_results.py`
- `update_results_fotmob.py`
- `fetch_api_football.py`
- `data/actual.csv`
- `data/details.csv`
- `data/leaderboard.csv`

Streamlit skal framleis bruke `app.py`.
