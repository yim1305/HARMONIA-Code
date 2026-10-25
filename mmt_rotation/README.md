# MMT rotation data

Scripts that get rotation rates for the HARMONIA objects from Mini-MegaTORTORA (MMT) light curves,
plot the curves for the factor-of-2 check, and copy the results into the workbook.

## Data

- MMT snapshot on Hugging Face: https://huggingface.co/datasets/kyselica/MMT_snapshot (MIT license)
- MMT: Karpov et al. (2016). Snapshot: Kyselica, Hrobár, Šilha, Ďurikovič and Šuppa (2025),
  "LCDC: Bridging Science and Machine Learning for Light Curve Analysis", arXiv:2504.10550
- The snapshot gets updated and MMT keeps adding tracks, so every pull saves the pull date and the
  snapshot version (`mmt_pull_info.txt`, and on every CSV row).

The pull used for the dataset is `data/pull_2026-10-24` (pulled 24 Oct 2026, snapshot last modified
2 Sep 2025).

## Setup

Python 3, then:

```
py -m pip install -r requirements.txt
```

## Scripts

| Script | What it does |
|---|---|
| `mmt_check.py` | Pulls every track for the given NORAD IDs and writes `mmt_summary.csv`, `mmt_tracks.csv` and `mmt_pull_info.txt` |
| `mmt_plot.py` | Plots the latest-year light curves: raw, and folded at P/2, P and 2P |
| `fill_lightcurve.py` | Copies `mmt_summary.csv` into the Light curve tab of the workbook (makes a backup first) |
| `archive/` | The older versions used for the week 2 pulls |

## Running a pull

From the `mmt_rotation` folder in PowerShell:

```powershell
$ids = "47858 7924 ...".Split(" ")   # NORAD IDs from the Master tab (full list in data/pull_2026-10-24/mmt_pull_info.txt)
py mmt_check.py @ids --out data/pull_YYYY-MM-DD
py mmt_plot.py @ids --summary data/pull_YYYY-MM-DD/mmt_summary.csv --out data/pull_YYYY-MM-DD/plots
py fill_lightcurve.py ..\..\HARMONIA_data_vN.xlsx data\pull_YYYY-MM-DD\mmt_summary.csv
```

Close the workbook in Excel before the last step. Use a new `data/pull_YYYY-MM-DD` folder for each
pull so older ones aren't overwritten. `mmt_plot.py --max N` changes how many tracks are plotted
per object (default 5).

## Method

- Rate (deg/s) = 360 / period (s). A track has a period if MMT gives one above 0.
- The rate for each object is the median period of all its tracks with a period in the latest
  year that has one. That year is the epoch. Some objects slow down over the years, so a median
  over all years would mix old and new rates. The all-years numbers are still in the summary.
- The plots use the same year and show the latest 5 tracks from it. With `--summary` the year comes
  from the saved summary, and the script warns if the snapshot now has a different number of tracks.
- Factor-of-2 check: in the panel folded at P, two unequal peaks per cycle means P is the full
  rotation. One clean peak means the real period could be 2P (compare with the 2P panel).
- Track length = last sample time minus first, in seconds.
- Below detection limit: the object has tracks but none of them gives a period. A period can only
  be measured if at least one full rotation fits in a track. In the 24 Oct 2026 pull tracks are
  6.5 to 310 s long, and the below-detection objects have median track lengths of 30 to 84 s
  (about 55 s typically). So they probably rotate slower than about 360 / (median track length),
  roughly 4 to 12 deg/s depending on the object. This is a limit of the data, not missing data.

## Output files

`mmt_tracks.csv` (one row per track): `norad_id`, `name`, `date`, `year`, `period_s`, `deg_per_s`,
`has_period`, `track_length_s`, `n_points`, `pulled_utc`, `snapshot_revision`, `snapshot_last_modified`.

`mmt_summary.csv` (one row per object): track counts (total, with and without a period), first and
last track date, `last_track_year`, track length median/min/max, `latest_year`,
`latest_year_n_tracks`, `latest_year_n_tracks_total`, `latest_year_median_period_s`,
`latest_year_median_deg_per_s`, the all-years period and rate stats, and the pull and snapshot fields.

## Folders

```
mmt_rotation/
├── mmt_check.py
├── mmt_plot.py
├── fill_lightcurve.py
├── requirements.txt
├── archive/              old script versions
└── data/
    ├── pull_2026-10-24/  pull used for the dataset (CSVs, pull info, plots/)
    └── archive/          the three week 2 pulls
```
