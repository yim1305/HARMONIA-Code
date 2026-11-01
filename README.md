# HARMONIA code

Code for the HARMONIA target dataset (UF Space Systems Group): defunct satellites in LEO with their
rotation rates, dry masses and grab-point geometry (r_P). The dataset itself is the
`HARMONIA_data_vN.xlsx` workbook in the folder above this one.

| Folder | What's in it | Language |
|---|---|---|
| [`week1_orbit_transfers`](week1_orbit_transfers/README.md) | Week 1: Hohmann transfer ΔV and HCW relative motion plots | MATLAB R2020a+ |
| [`mmt_rotation`](mmt_rotation/README.md) | Rotation rates from MMT light curves, the factor-of-2 plots, and the import into the workbook | Python 3 |
| [`figures`](figures/README.md) | The dataset figures (r_P by bus family, rotation rate vs years since end of life) plus some drafts | Python 3 |

```
HARMONIA Code/
├── week1_orbit_transfers/
│   ├── hohmann.m
│   ├── hcw.m
│   ├── figures/
│   └── archive/
├── mmt_rotation/
│   ├── mmt_check.py
│   ├── mmt_plot.py
│   ├── mmt_years.py
│   ├── fill_lightcurve.py
│   ├── requirements.txt
│   ├── archive/
│   └── data/
└── figures/
    ├── style.py
    ├── fig1_rp.py
    ├── fig2_rate.py
    └── drafts/         figures 3 to 6
```

## Quick start

Week 1: open `hohmann.m` or `hcw.m` in MATLAB and press Run. Figures go to
`week1_orbit_transfers/figures/`.

Rotation data:

```
cd mmt_rotation
py -m pip install -r requirements.txt
py mmt_check.py 47858 7924 --out data/pull_YYYY-MM-DD
```

The full steps are in [`mmt_rotation/README.md`](mmt_rotation/README.md).

Figures (save the workbook in Excel once first, fig1 needs the calculated r_P values):

```
cd figures
py fig1_rp.py ..\..\HARMONIA_data_v1.2.xlsx
py fig2_rate.py ..\..\HARMONIA_data_v1.2.xlsx ..\mmt_rotation\data\pull_2026-10-24\mmt_tracks.csv
```

More in [`figures/README.md`](figures/README.md).
