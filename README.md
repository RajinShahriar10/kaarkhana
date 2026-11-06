# Kaarkhana

An on-device industrial engineer for garment lines. Film a line; Kaarkhana watches the **bundles** (not the workers),
measures how long each station stays busy and how much work queues in front of it, names the constraint,
reconciles it against the factory's own SMV sheet, and writes a costed rebalance report a plant manager can sign.

**Runs locally on any PC. Free. No account, no API key, no cloud.** Your video never leaves the computer.

## Use it
1. Open Kaarkhana (it opens in your browser, on your PC).
2. Drop in the **SMV sheet**, the **video**, and optionally the **layout** and other documents. Click **Try the demo** to see a full example first.
3. Check the station overlay, press **Analyse this line**.
4. Download the **signable PDF**, **Excel workbook** and a **ZIP package** of everything.

![Start](docs/screenshots/1-start.png)
![Calibrate](docs/screenshots/2-calibrate.png)
![Results](docs/screenshots/3-results.png)
![Documents](docs/screenshots/4-documents.png)

## Get it
- **Windows:** download `Kaarkhana-Setup.exe` from Releases (see [docs/RELEASING.md](docs/RELEASING.md) to produce it), double-click, then open **Kaarkhana** from the Start menu.
- **macOS / Linux / Windows portable:** download the zip for your OS from Releases and run `Kaarkhana`. Installers are unsigned, so Windows SmartScreen or macOS Gatekeeper may warn on first run (More info, Run anyway / right-click, Open).
- **Any OS with Python 3.10+:** `pip install .` then `kaarkhana` (or double-click `Kaarkhana.bat` / `Kaarkhana.command`).
- Details, troubleshooting, data locations: [docs/INSTALL.md](docs/INSTALL.md). How to film: [docs/CAMERA_GUIDE.md](docs/CAMERA_GUIDE.md).

```
kaarkhana              # open the app
kaarkhana selftest     # check the install on the bundled sample (about 20 s)
kaarkhana analyze VIDEO --line my_line.json --anchors x1,y1,x2,y2 --stopwatch ST5=86 --out report/
kaarkhana import-smv my_sheet.xlsx --out my_line.json
```
Free Colab notebook (no local install): `notebooks/kaarkhana_colab.ipynb`.

## How it works
| Stage | Module | What it does |
|---|---|---|
| Calibrate | `calibrate.py` | Auto-finds station plates, or you click the first and last work spot; geometry is in station-pitch units, so camera distance and resolution do not matter; shows an overlay so you can check it |
| See | `detect.py` | Bundle detector. Classical (CPU, default). Optional SAM 3 text-prompted zero-shot (`pip install .[sam]`, GPU) |
| Measure | `measure.py`, `events.py` | Per-station work-spot and queue signals become arrive/work/depart events; back-to-back bundles are separated by colour change |
| Decide | `analysis.py` | Constraint = longest cycle per operator, corroborated by downstream starvation and WIP queue; confidence is graded and capped when data is thin |
| Reconcile | `analysis.reconcile` | Observed vs your SMV sheet; flags stations deviating more than 25% from the line's own pace |
| Prescribe | `balance.py` | Same-headcount task shift, or +1/+2 operators (optimal min-max), with costing |
| Explain | `agent.py` | Deterministic, number-by-number justification; optional local LLM polish that is rejected if it contains any number not in the facts |
| Report | `report.py` | PDF with evidence, SMV table, options, assumptions, signature block |
| App | `server.py`, `web/` | Local web app: import SMV, upload, calibrate, analyse, history. Binds to 127.0.0.1 only |

## Honest status
- **Validated on a simulated line with known cycle times** ([docs/VALIDATION.md](docs/VALIDATION.md)): right constraint, correlation 0.94-0.97 with the true cycle times. **Not yet validated on a live factory floor.** Do a stopwatch time study on a real line before relying on it.
- Station-to-station ratios are reliable; uncalibrated absolute seconds read about 10-30% high. Enter one stopwatch reading to calibrate.
- The classical detector assumes a side-on camera and bundles on a table. The calibration overlay lets you verify the geometry fits your footage; unusual layouts (U-lines, overhead cameras) are not supported.
- Savings are estimates from your own inputs (wage, price, realisation factor). Defaults are placeholders.
- Reports are decision support: review with your industrial engineer before changing the line.
- Bangla UI and report text are not included yet.

## Develop
```
pip install -e ".[dev]"
pytest
python tests/make_icon.py && pyinstaller kaarkhana.spec --noconfirm   # build the app
```
`sim/` holds the 3D line simulator and SMV workbook used for benchmarking. MIT licence.
"# kaarkhana" 
