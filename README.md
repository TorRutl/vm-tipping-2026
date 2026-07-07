# VM-tipping 2026

Dette er første komplette versjon av poengprogrammet.

## Kva er lagt inn?

- Alle tipsa frå kontrollfilene:
  - 16-delsfinale
  - 8-delsfinale
  - kvartfinale
  - semifinale
  - finalist
  - VM-vinnar
  - sølv
  - bronse
  - toppscorar
- Sissel og Eli er hoppa over.
- Poengreglane ligg i `data/points.csv`.
- Førebels fasit ligg i `data/actual.csv`.

## Slik køyrer du

### 1. Installer pakkar

```bash
python -m pip install -r requirements.txt
```

### 2. Start nettsida

```bash
streamlit run app.py
```

På Windows kan du også dobbeltklikke:

```text
run_windows.bat
```

## Slik oppdaterer du etter nye kampar

Opne `data/actual.csv` og legg til nye lag i riktig runde.

Døme:
- Når eit lag når kvartfinale, legg det inn med `stage = kvartfinale`.
- Når eit lag når semifinale, legg det inn med `stage = semifinale`.
- Når finalistane er klare, legg dei inn med `stage = finalist`.

## Automatisk henting av resultat

`fetch_api_football.py` er lagt inn som neste byggjekloss. Han kan hente rådata frå API-Football dersom du får ein API-nøkkel.

API-Football dokumenterer at VM 2026-kampane kan hentast med:

```text
fixtures?league=1&season=2026
```

Når vi har API-nøkkel og ser nøyaktig JSON-formatet, kan vi fullføre automatisk mapping frå kampar til `actual.csv`.


## Automatisk oppdatering med API-nøkkel

1. Legg API-nøkkelen i Windows-miljøvariabel:

```powershell
setx APIFOOTBALL_KEY "DIN_NOKKEL"
```

2. Lukk PowerShell og opne på nytt.

3. Køyr:

```powershell
python update_results.py
```

4. Start/oppdater nettsida:

```powershell
python -m streamlit run app.py
```

`update_results.py` hentar VM-kampane frå API-Football, finn ferdigspelte utslagskampar, oppdaterer `data/actual.csv`, og poengtavla les den nye fasiten.


## Gratis oppdatering frå FotMob

API-Football free fungerte ikkje for 2026-sesongen, så denne versjonen brukar FotMob i staden.

Køyr:

```powershell
python update_results_fotmob.py
```

Deretter startar/oppdaterer du poengtavla:

```powershell
python -m streamlit run app.py
```

Skriptet prøver å hente World Cup 2026 frå FotMob, finne utslagskampar som er ferdige, og oppdatere `data/actual.csv`.


## Nytt i v4

- Toppfelt som viser kven som leiar akkurat no.
- Delt leiing blir vist riktig.
- Eigen “Teten akkurat no”-tabell.
- Viser di plassering og kor mange poeng du er bak leiar.
- Auto-refresh i sidepanelet. Merk: Dette oppdaterer sida, men nye kampresultat må framleis hentast med:

```powershell
python update_results_fotmob.py
```

Deretter oppdaterer du sida, eller slår på auto-refresh.


## v5-fiks

Denne versjonen passar på at `8_delsfinale` ikkje blir sletta når FotMob-oppdateringa køyrer.

Etter `python update_results_fotmob.py` bør terminalen vise:
- `16_delsfinale` = 32
- `8_delsfinale` = 16
- `kvartfinale` = minst 4 no, og etter kvart 8


## v6 – poengreglar låst

Poengreglane er no eksplisitt sett slik:

- 16-delsfinale: 1 poeng per riktig lag
- 8-delsfinale: 2 poeng per riktig lag
- Kvartfinale: 3 poeng per riktig lag
- Semifinale: 4 poeng per riktig lag
- Finalist: 5 poeng per riktig finalist
- VM-vinnar: 3 poeng
- 2. plass/sølv: 2 poeng
- 3. plass/bronse: 1 poeng
- Toppscorar: 3 poeng

Desse ligg i `data/points.csv` og blir brukt av `score.py`.


## v7 – fiks for `actual is not defined`

I v6 kom kontrolltabellen for fasit før `actual.csv` vart lesen inn. Dette er fiksa i v7.


## v8 – sluttspelvisning per deltakar

Når du vel ein deltakar, får du no tipsa vist som eit sluttspel-kart:
- ✅ riktig
- ❌ feil
- ⏳ ikkje avgjort

Du kan også sjå kvar runde for seg eller alt i tabell.


## v9 – fiks for actual-feil

Fikser feilen `NameError: name 'actual' is not defined` i sluttspelvisninga.


## v10 – fungerande visuelt sluttspel

Bytta til `streamlit.components.v1.html`, slik at korta blir rendera og ikkje vist som rå HTML-kode.

Visninga har:
- grøn = riktig
- raud = feil
- gul = ikkje avgjort


## v11 – fiks for `leaders is not defined`

Denne versjonen definerer `leaders`, `leader_score` og delt plassering før Live status blir vist.


## v12-pro

Dette er ei ryddigare framside/appstruktur:

- Live status
- Teten akkurat no
- Poeng per runde
- Flest tips framleis i live/riktige
- Poeng i siste oppdaterte runde
- Deltakarvisning med visuelt sluttspel
- Fasit- og poengregel-faner

Køyr som før:

```powershell
python update_results_fotmob.py
python -m streamlit run app.py
```


## v13-cloud

Denne versjonen er laga for Streamlit Community Cloud.

Nytt:
- FotMob kan hentast automatisk når nettsida blir opna.
- Du kan opne appen frå mobil på ferie.
- Eigen deploy-guide: `DEPLOY_STREAMLIT_CLOUD.md`.
- Cache på 5 minutt for FotMob-henting.

Lokal køyring:
```powershell
python -m streamlit run app.py
```
