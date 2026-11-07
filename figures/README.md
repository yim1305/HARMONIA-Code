# HARMONIA figures

The scripts that make figures 1 to 6 for the dataset. They read straight from the workbook and the MMT pull, so if the data changes I just rerun them and the figures update. Each one saves a 300 dpi PNG that fits a full page width (7 in) into `plots/`.

## What's in this folder

```
figures/
├── fig1_rp.py               Fig 1: grab-point distance per object
├── fig2_rate.py             Fig 2: rotation rate vs years since end of life (+ 2 supporting plots)
├── fig3_spin_evolution.py   Fig 3: spin rate over time, one panel per object
├── fig4_grab_accel.py       Fig 4: rotation rate vs r⊥, with lines of equal centripetal acceleration
├── fig5_timeline.py         Fig 5: which years each object gave a period
├── fig6_detection.py        Fig 6: period found vs track length (what MMT can measure)
├── style.py                 fonts, colors, markers, legend style, and where plots are saved
├── common.py                reads the workbook and the tracks CSV (figs 3 to 6)
├── left_out.py              reads the list of left-out folds (figs 2, 3, 5, 6)
└── plots/                   the current PNGs
    └── archive/             last week's PNGs, as committed on 1 Nov 2026
```

## Style

All six figures follow the same rules so they look like one set in the paper:

- 7 in wide (full page width), 300 dpi, STIX serif font to match the paper text.
- Legend above the plot, centered, no frame (`legend_top` in `style.py`). No titles inside the figures; that goes in the caption. Panel figures name each panel above it.
- Same colors for scope everywhere (blue in scope, orange near scope, green out of range, gray reference), circles for satellites and triangles for rocket bodies.
- Axis labels are "Quantity, symbol (unit)", e.g. "Rotation rate, ω (°/s)". Log axes show plain numbers and no minor ticks.
- The gray band is always the 2 to 5 °/s range from the task sheet, and left-out folds are always hollow.
- Figure text only describes what's shown, for a reader with no project context: no internal terms like "task sheet", "fold", "track" or "in scope". The legend says "Assumed rotation range", "Excluded period", "Light curve" and "Within mass and orbit limits" instead; the caption explains the rest.

## Setup

Same packages as `mmt_rotation`, so if that already runs you're set. Otherwise:

```
py -m pip install -r ..\mmt_rotation\requirements.txt
```

## Running

1. **Open the workbook in Excel and save it.** The r_P, r⊥ and detection limit columns are formulas, and Python can only read the values Excel last calculated. If a script has edited the workbook since then, those values are empty: fig1 stops and tells you, and fig4 leaves objects out.
2. From this folder in PowerShell (the paths are in variables so there's only one place to change if the workbook gets renamed):

```powershell
$wb = "..\..\HARMONIA_data_v2.xlsx"
$tr = "..\mmt_rotation\data\pull_2026-10-24\mmt_tracks.csv"

py fig1_rp.py $wb
py fig2_rate.py $wb $tr
py fig2_rate.py $wb $tr --part periods
py fig2_rate.py $wb $tr --part limits
py fig3_spin_evolution.py $wb $tr
py fig4_grab_accel.py $wb
py fig5_timeline.py $wb $tr
py fig6_detection.py $wb $tr
```

The PNGs always go to `plots/`, wherever you run the scripts from. Add `--out path.png` to save one somewhere else.

3. Check the printed lines. If everything ran right:
   - fig1 prints `40 objects in 7 blocks`.
   - fig3 prints `TIROS-N: fit 2014-2016, 3 yearly points`.
   - fig4 prints `Measured objects: a from 8 to 708 mm/s^2` and that Cosmos 2334 was left out (it has r_P but no MMT rate yet).
   - fig6 prints a minimum of 1.21 cycles per track, 5% at 1.89.

## The figures

### Fig 1: grab-point distance (`fig1_rp.py` → `fig1_rp.png`)

Each row is one object. The line runs from r⊥ low (left end, spin about the long axis) to r⊥ high (right end, highest z and largest ring). Both ends are measured **from the spin axis**. The filled dot is r_P full, measured **from the center of mass**. A ring marks the likely spin state, which I only have for the objects with published moments of inertia (Nimbus and Landsat 1).

Rows are grouped by bus family from the Master tab; a design with only one object goes under "Single designs". Color is scope (In scope, Near scope, Out of range) and shape is object type (circle = satellite, triangle = rocket body). Reference and Not intact objects aren't shown, and anything without r_P yet is left out with its name printed.

![fig1_rp.png](plots/fig1_rp.png)

### Fig 2: rotation rate vs years since end of life (`fig2_rate.py` → `fig2_rate.png`)

Faint points are single MMT tracks with a period. Each object's line goes through its yearly medians, dashed across a gap of a year or more with no period. Hollow points are left-out folds (see *Left-out folds*); they aren't in the medians.

Objects that never gave a period are upper limits: a dot at 1.2 × 360 / (longest track) with an arrow down, since the real rate must be slower (see *Detection limit*). Their names hang off one line at the bottom, and objects at the same x share a label. The gray band is the 2 to 5 °/s range from the task sheet.

![fig2_rate.png](plots/fig2_rate.png)

Two supporting plots split Fig 2 so it's easier to read:
- `--part periods` → `fig2_periods.png`: only the objects with a measured period.
- `--part limits` → `fig2_limits.png`: only the objects with no period. Filled dot = the stated limit (1.2 cycles), hollow dot = the typical case (1.9 cycles).

### Fig 3: spin evolution (`fig3_spin_evolution.py` → `fig3_spin_evolution.png`)

Spin rate over time for the 12 objects with several years of periods, one panel each on the same log axis. The dashed line is an exponential fit over the spin-down years, labeled with its e-folding time τ (or % per year for a spin-up). Fits on fewer than 4 yearly points are dotted gray and labeled "indicative" (only TIROS-N, 3 points). Ticks along the bottom are years with tracks but no period. The fit years for each object are in `PANELS` at the top of the script.

### Fig 4: grab-point acceleration (`fig4_grab_accel.py` → `fig4_grab_accel.png`)

Rotation rate against r⊥, in two panels with the same x-axis: (a) objects with a measured period, at their latest-year rate, and (b) objects with no period, at their detection limit with an arrow down. Each object is a line from r⊥ low to r⊥ high, and the ring marks the likely spin state, as in Fig 1. Names sit in a column on the right, joined to the end of each line by a faint leader, so no label covers the data.

The dotted lines are equal centripetal acceleration, a = ω²r⊥, at 1, 3, 10, 30, 100, 300 and 1000 mm/s². A servicer holding station beside the grab point needs a thrust of (its mass) × ω²r⊥, so each line is a thrust per kg of servicer. The script prints a for every measured object (8 to 708 mm/s²).

### Fig 5: timeline (`fig5_timeline.py` → `fig5_timeline.png`)

Which years each object gave a period in MMT, 2014 to 2025. Blue cells show that year's median rate in °/s, using only the kept folds. Gray = tracks but no period, blank = no tracks. `*` = some folds that year were left out; an outlined cell with a dash = all of them were. The % after each name is the share of tracks with a period.

### Fig 6: what MMT can measure (`fig6_detection.py` → `fig6_detection.png`)

Period found against track length for every track with a period. A period only shows if at least about 1.2 cycles fit in the track, so all points sit below P = L/1.2, and 95% sit below P = L/1.9. Large dots are the last period seen before an object went quiet for 3+ years. Hollow points are left-out folds; they still count in the cycles-per-track numbers, because the question here is what MMT can detect, not whether the period is the real rotation.

## Detection limit

A period only shows when at least 1.2 cycles fit in a track: the fewest behind any period in the pull is 1.21, and 95% of periods have at least 1.9. So for an object with no period:

- **Stated limit:** 1.2 × 360 / (longest track). This is what figs 2 and 4 plot.
- **Typical case:** 1.9 × 360 / (longest track), shown hollow in `fig2_limits.png`.

The factors are `CYCLES` and `CYCLES_TYPICAL` at the top of `fig2_rate.py`. The same 1.2 is in the two detection limit columns of the Light curve tab, so change both if it ever changes.

## Left-out folds

The folds I leave out are listed once, in `../mmt_rotation/left_out_folds.csv` (NORAD ID, date range, reason). Figs 2, 3, 5 and 6 all read it through `left_out.py`, so they always drop the same tracks:

| Object | Left out | Why |
|---|---|---|
| DMSP F12 | Dec 2016 to Jan 2017 | Period is a whole multiple of the real cycle |
| Nimbus 7 | Jul 2018 | Doesn't fold cleanly at P/2, P or 2P |
| TOMS-EP | Aug 2016 | Half the real period |
| TOMS-EP | 2024 to 2025 | Harmonics; the workbook uses 2018 to 2023 |

The full reasons are in the Factor-of-2 comments on the Light curve tab. To leave out another fold, add a row to the CSV (dates are inclusive) and rerun the figures. Every script also takes `--left-out other.csv` to try a different list without changing the real one.
