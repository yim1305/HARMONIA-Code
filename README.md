# HARMONIA code

Code for the HARMONIA target dataset (UF Space Systems Group): defunct satellites in LEO with their rotation rates, dry masses and grab-point geometry (r_P). The dataset itself is the `HARMONIA_data_v2.xlsx` workbook in the folder above this one.

| Folder | What's in it | Language |
|---|---|---|
| [`week1_orbit_transfers`](week1_orbit_transfers/README.md) | Week 1: Hohmann transfer ΔV and HCW relative motion plots | MATLAB R2020a+ |
| [`mmt_rotation`](mmt_rotation/README.md) | Gets rotation rates from MMT light curves, plots the folds for the factor-of-2 check, and copies the results into the workbook | Python 3 |
| [`figures`](figures/README.md) | Makes the dataset figures 1 to 7 | Python 3 |

```
HARMONIA Code/
├── week1_orbit_transfers/
│   ├── hohmann.m, hcw.m
│   ├── figures/
│   └── archive/
├── mmt_rotation/
│   ├── mmt_check.py           pull tracks for NORAD IDs
│   ├── mmt_plot.py            plot and fold light curves
│   ├── mmt_years.py           pull and plot a range of years
│   ├── fill_lightcurve.py     copy a pull into the workbook
│   ├── left_out_folds.csv     folds every figure leaves out
│   ├── requirements.txt
│   ├── archive/               old script versions
│   └── data/                  one folder per pull
└── figures/
    ├── fig1_rp.py ... fig7_accel_cdf.py
    ├── table1_rp_width.py     Table 1 (saved to tables/)
    ├── explore_trends.py      exploratory plots, not in the memo
    ├── style.py, common.py, left_out.py
    └── plots/                 the PNGs
        └── archive/           last week's PNGs
```

## Quick start

Install the Python packages once (both Python folders use the same list):

```
py -m pip install -r mmt_rotation\requirements.txt
```

**Week 1:** open `hohmann.m` or `hcw.m` in MATLAB and press Run. Figures go to `week1_orbit_transfers/figures/`.

**Rotation data:** a new pull goes in its own `data/pull_YYYY-MM-DD` folder.

```
cd mmt_rotation
py mmt_check.py 47858 7924 --out data/pull_YYYY-MM-DD
```

The full steps (plots, years, copying into the workbook) are in [`mmt_rotation/README.md`](mmt_rotation/README.md).

**Figures:** open the workbook in Excel and save it first, because fig1 and fig4 need the calculated r_P values. Then:

```
cd figures
py fig1_rp.py ..\..\HARMONIA_data_v2.xlsx
py fig2_rate.py ..\..\HARMONIA_data_v2.xlsx ..\mmt_rotation\data\pull_2026-10-24\mmt_tracks.csv
```

PNGs go to `figures/plots/`. The commands for all seven figures are in [`figures/README.md`](figures/README.md).
