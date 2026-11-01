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
| `mmt_years.py` | Pulls and plots chosen NORAD IDs for a range of years into a separate pull folder |
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

To look at other years for any objects without touching the main pull, use `mmt_years.py`. It runs
`mmt_check.py` and then `mmt_plot.py --years` for every year in the range, and saves everything in a
new folder `data/pull_YYYY-MM-DD_<ids>_<from>-<to>/` (CSVs, pull info and `plots/`):

```powershell
py mmt_years.py 23940 --from 2023 --to 2024
py mmt_years.py 23940 11080 --from 2018 --to 2020 --max 5 --tag toms_nimbus7
```

`--max` is tracks per object per year (default 10), `--tag` names the folder instead of the IDs, and
`--dry-run` prints the commands without running them. `mmt_plot.py --years` can also be used on its
own; it overrides `--summary`.

## Method

- Rate (deg/s) = 360 / period (s). A track has a period if MMT gives one above 0.
- The rate for each object is the median period of all its tracks with a period in the latest
  year that has one. That year is the epoch. Some objects slow down over the years, so a median
  over all years would mix old and new rates. The all-years numbers are still in the summary.
- Exception: if the latest-year folds turn out to be harmonics, an earlier window is used instead and
  the row is marked "Yes" in the workbook's "Latest-year values set by hand" column (Light curve tab).
  `fill_lightcurve.py` then leaves that row's latest-year columns alone. TOMS-EP (23940) uses
  2018-2023 for this reason; see its notes and `data/pull_2026-10-30_23940_2023-2024`.
- The plots use the same year and show the latest 5 tracks from it. With `--summary` the year comes
  from the saved summary, and the script warns if the snapshot now has a different number of tracks.
- Factor-of-2 check: in the panel folded at P, two unequal peaks per cycle means P is the full
  rotation. One clean peak means the real period could be 2P (compare with the 2P panel).
- I also fold-checked every big jump between years with `mmt_years.py` (the `pull_2026-10-31_*`
  folders). Only two were fold errors: DMSP F12 Dec 2016 to Jan 2017 (too long) and TOMS-EP Aug 2016
  (half the real period). The rest are real spin-ups or slow-downs. What I decided for each one is in
  the Factor-of-2 comments column of the Light curve tab. Where I couldn't tell, I listed the
  candidate periods there instead of picking one.
- Track length = last sample time minus first, in seconds.
- Below detection limit: the object has tracks but none of them gives a period. That means it's
  either slower than the limit or not rotating periodically at all (attitude-stable, tumbling with no
  clean period, or too faint). A period can only be measured if at least one full rotation fits in a
  track, so the limit is 360 / track length. The workbook has two: one from the median track
  (about 4 to 12 deg/s) and one from the longest track (1.2 to 4.6 deg/s). The longest-track one is
  the real upper limit and is the one the figures use.

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
├── mmt_years.py
├── fill_lightcurve.py
├── requirements.txt
├── archive/                      old script versions
└── data/
    ├── pull_2026-10-24/          pull used for the dataset (CSVs, pull info, plots/)
    ├── pull_2026-10-30_23940_*   TOMS-EP 2023-2024 check
    ├── pull_2026-10-31_*         fold checks for the spin-ups and x2 jumps (one folder per object)
    └── archive/                  the three week 2 pulls
```
