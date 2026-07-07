# Legg VM-tippinga live på mobil

## 1. Lag GitHub-repo
Gå til GitHub og lag eit nytt repository, til dømes:

`vm-tipping-2026`

Last opp alle filene i denne mappa.

Viktig at desse ligg i rota av repoet:
- `app.py`
- `score.py`
- `update_results_fotmob.py`
- `requirements.txt`
- `data/`

## 2. Gå til Streamlit Community Cloud
Gå til Streamlit Community Cloud og vel **New app**.

Vel:
- Repository: `vm-tipping-2026`
- Branch: `main`
- Main file path: `app.py`

Trykk **Deploy**.

## 3. Bruk frå mobil
Når appen er deploya får du ei lenke som liknar:

`https://vm-tipping-2026.streamlit.app`

Opne lenka på mobil.

## 4. Oppdatering
I sidepanelet:
- slå på **Hent FotMob automatisk**
- eller trykk **Hent siste resultat frå FotMob no**

Appen brukar cache på 5 minutt, slik at han ikkje masar for mykje på FotMob.

## 5. Privat?
Streamlit Community Cloud-app kan vere synleg for dei som har lenka. Ikkje legg inn passord eller sensitiv informasjon i repoet.
