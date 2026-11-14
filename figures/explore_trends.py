"""Exploratory plots (not in the memo), saved to plots/explore/. The acceleration CDF that started here is now
Figure 7 (fig7_accel_cdf.py).

  explore_tau_vs_properties.png spin-down e-folding time tau against mass, mean altitude and bus height
  explore_rate_vs_size.png      latest-year rotation rate against mass and bus height

It also prints the numbers used in the memo: the rank correlations (Spearman's rho) of tau and rate against
size, the objects that went quiet (no period in their last 2+ years), and the brightness and size check for the
sampling bias.

    py explore_trends.py ..\\..\\HARMONIA_data_v2.xlsx ..\\mmt_rotation\\data\\pull_2026-10-24\\mmt_tracks.csv
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import left_out
from common import read_master, read_tracks
from fig3_spin_evolution import PANELS
from style import (FS, GRID_LW, save, apply_style, GROUP_COLOR, SCOPE_LABEL, SCOPE_ORDER, TYPE_SCALE, marker_for, INK, MUTED, GRID,
                   PLOTS, legend_top)

SHOW = ("In scope", "Near scope", "Orbit out", "Rocket body")
LO, HI = "r⊥ low (m)", "r⊥ high (m)"
RATE, LIM = "Rotation rate, latest year (deg/s)", "Detection limit, longest track (deg/s)"
OUT = PLOTS / "explore"
R_BAND, SLOW, FAST, A_MAX = (0.25, 3.5), (0, 6), (6, 31), 300


def bus_size(path):
    rp = openpyxl.load_workbook(path, data_only=True)["r_P"]
    H = {rp.cell(1, c).value: c for c in range(1, rp.max_column + 1)}
    return {rp.cell(r, 3).value: rp.cell(r, H["Bus height h (m)"]).value for r in range(2, 62) if rp.cell(r, 3).value}


def rank_corr(x, y):
    x, y = pd.Series(x, dtype=float).reset_index(drop=True), pd.Series(y, dtype=float).reset_index(drop=True)
    ok = x.notna() & y.notna()
    return x[ok].rank().corr(y[ok].rank()), int(ok.sum())


def max_track(path):
    lc = openpyxl.load_workbook(path, data_only=True)["Light curve"]
    H = {lc.cell(1, c).value: c for c in range(1, lc.max_column + 1)}
    return {lc.cell(r, 3).value: lc.cell(r, H["Max track length (s)"]).value for r in range(2, 62) if lc.cell(r, 3).value}


def scope_handles(groups):
    h, seen = [], []
    for g in SCOPE_ORDER + ["Rocket body"]:
        if (g in groups or (g == "Orbit out" and "Rocket body" in groups)) and SCOPE_LABEL[g] not in seen:
            seen.append(SCOPE_LABEL[g])
            h.append(Line2D([], [], color=GROUP_COLOR[g], lw=0, marker="o", ms=5, mew=0, label=SCOPE_LABEL[g]))
    return h


def fit_taus(M, t):
    out = []
    for nid, win in PANELS:
        if not win:
            continue
        p = t[(t.norad_id == nid) & t.has_period & ~t.left_out].copy()
        p["rate"] = 360 / p.period_s
        q = p.groupby("year").agg(dec=("dec", "median"), per=("period_s", "median"))
        q["rate"] = 360 / q.per
        w = q[(q.index >= win[0]) & (q.index <= win[1])]
        s, _ = np.polyfit(w.dec, np.log(w.rate), 1)
        if s < 0:
            o = M.set_index("NORAD ID").loc[nid]
            out.append(dict(nid=nid, name=o["name"], tau=-1 / s, n=len(w), group=o["Dataset group"],
                            family=o["Bus family"], mass=o["Dry mass (kg)"],
                            alt=(o["Perigee (km)"] + o["Apogee (km)"]) / 2, h=o["h"], type=o["Object type"]))
    return out


def plot_tau(M, t):
    F = fit_taus(M, t)
    props = [("mass", "Dry mass (kg)"), ("alt", "Mean altitude (km)"), ("h", "Bus height, h (m)")]
    apply_style()
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.6), sharey=True)
    for ax, (k, lab) in zip(axs, props):
        for f in F:
            col = GROUP_COLOR[f["group"]]
            hollow = f["n"] < 4
            ax.plot(f[k], f["tau"], marker="o", ms=5, lw=0, mfc="white" if hollow else col, mec=col, mew=1.0)
        ax.set_xlabel(lab)
        ax.grid(True, color=GRID, lw=GRID_LW)
        ax.set_axisbelow(True)
    axs[0].set_ylabel(r"Spin-down time, $\tau$ (years)")
    axs[0].set_ylim(0, 7.5)
    for f in F:  # name each point once, on the altitude panel, where they spread out most
        axs[1].annotate(f["name"].replace("DMSP 5D-2 ", "DMSP "), (f["alt"], f["tau"]), xytext=(4, 2),
                        textcoords="offset points", fontsize=FS["note"], color=INK)
    h = scope_handles({f["group"] for f in F})
    h.append(Line2D([], [], color=MUTED, lw=0, marker="o", ms=5, mfc="white", mew=1.0,
                    label="Fit on fewer than 4 yearly points"))
    fig.tight_layout(rect=(0, 0, 1, 0.85), w_pad=0.6)
    legend_top(fig, h, 3, y=0.86)
    save(fig, OUT / "explore_tau_vs_properties.png")
    plt.close(fig)

    print("\ntau vs size")
    for f in sorted(F, key=lambda f: f["tau"]):
        print(f"  {f['name']:<14} tau {f['tau']:4.1f} yr  n={f['n']:2d}  {f['family']:<30} mass {f['mass']:5.0f}  "
              f"alt {f['alt']:5.0f}  h {f['h']}")
    fams = {f["family"] for f in F}
    print(f"  {len(F)} fits from {len(fams)} bus families; "
          f"{sum(f['family'] == 'TIROS-N/ATN' for f in F)} are TIROS-N/ATN")
    for k in ("mass", "alt", "h"):
        rho, n = rank_corr([f[k] for f in F], [f["tau"] for f in F])
        print(f"  rank correlation tau vs {k}: {rho:+.2f} (n={n})")


def plot_rate(M):
    meas = M[(M["Rotation category"] == "Period measured") & M[RATE].notna()]
    lim = M[(M["Rotation category"] == "Below detection limit") & M[LIM].notna()]
    apply_style()
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.2), sharey=True)
    for ax, (k, lab, log) in zip(axs, [("Dry mass (kg)", "Dry mass (kg)", False), ("h", "Bus height, h (m)", False)]):
        ax.set_yscale("log")
        ax.axhspan(2, 5, color=GRID, alpha=0.55, lw=0, zorder=0)
        for _, o in meas.iterrows():
            col, mk = GROUP_COLOR[o["Dataset group"]], marker_for(o["Object type"])
            ax.plot(o[k], o[RATE], marker=mk, ms=5 * TYPE_SCALE[mk], mfc=col, mew=0, lw=0, zorder=3)
        for _, o in lim.iterrows():
            col, mk = GROUP_COLOR[o["Dataset group"]], marker_for(o["Object type"])
            ax.annotate("", (o[k], o[LIM] / 1.25), (o[k], o[LIM]), zorder=2,
                        arrowprops=dict(arrowstyle="-|>,head_width=0.12,head_length=0.22", color=col, lw=0.6,
                                        shrinkA=0, shrinkB=0, alpha=0.6))
            ax.plot(o[k], o[LIM], marker=mk, ms=4 * TYPE_SCALE[mk], mfc="white", mec=col, mew=0.8, lw=0,
                    alpha=0.8, zorder=2)
        ax.set_xlabel(lab)
        ax.set_yticks([1, 2, 5, 10, 20, 40])
        ax.set_yticklabels(["1", "2", "5", "10", "20", "40"])
        ax.minorticks_off()
        ax.set_ylim(1, 45)
        ax.grid(True, color=GRID, lw=GRID_LW)
        ax.set_axisbelow(True)
    axs[0].set_ylabel(r"Rotation rate, $\omega$ (°/s)")
    h = scope_handles(set(meas["Dataset group"]) | set(lim["Dataset group"]))
    h += [Line2D([], [], color=MUTED, lw=0, marker="o", ms=5, mew=0, label="Measured period (latest year)"),
          Line2D([], [], color=MUTED, lw=0, marker="o", ms=4, mfc="white", mew=0.8,
                 label="No period detected (upper limit)"),
          Patch(facecolor=GRID, alpha=0.9, label="Assumed rotation range, 2–5 °/s")]
    fig.tight_layout(rect=(0, 0, 1, 0.84), w_pad=0.8)
    legend_top(fig, h, 3, y=0.85)
    save(fig, OUT / "explore_rate_vs_size.png")
    plt.close(fig)

    print("\nrate vs size (measured objects)")
    for k in ("Dry mass (kg)", "h"):
        rho, n = rank_corr(meas[k], meas[RATE])
        print(f"  rank correlation rate vs {k}: {rho:+.2f} (n={n})")
    rho, _ = rank_corr(meas["Years since end of life"], meas[RATE])
    print(f"  for comparison, rate vs years since end of life: {rho:+.2f}")


def quiet(M, t):
    taus = {f["nid"]: f["tau"] for f in fit_taus(M, t)}
    meas = M[(M["Rotation category"] == "Period measured") & M[RATE].notna()]
    print("\nobjects with no period in their last 2+ years")
    groups = {}
    for _, o in meas.iterrows():
        x = t[t.norad_id == o["NORAD ID"]]
        last_p, last_t = x[x.has_period].year.max(), x.year.max()
        if last_t - last_p < 2:
            continue
        kept = x[x.has_period & ~x.left_out]
        yearly = 360 / kept.groupby("year").period_s.median()
        limit = 1.2 * 360 / x[x.year > last_p].track_length_s.max()
        tau = taus.get(o["NORAD ID"])
        extra = ""
        if len(yearly) == 1:
            trend = "one year of periods"
        elif tau:
            trend = "spinning down"
            now = yearly.iloc[-1] * np.exp(-(last_t - yearly.index[-1]) / tau)
            extra = f", fit extended to {last_t}: {now:.1f} deg/s"
        else:
            trend = "steady or speeding up"
        groups.setdefault(trend, []).append(o["name"])
        print(f"  {o['name']:<14} last period {last_p}, last track {last_t} ({last_t - last_p} yr), "
              f"last rate {yearly.iloc[-1]:4.1f} deg/s, limit of later tracks {limit:.1f} deg/s, {trend}{extra}")
    n = sum(len(v) for v in groups.values())
    print(f"  {n} of {len(meas)} measured objects")
    for k, v in groups.items():
        print(f"  {k}: {', '.join(v)}")


def recommend(M):
    meas = (M["Rotation category"] == "Period measured") & M[RATE].notna()
    lim = (M["Rotation category"] == "Below detection limit") & M[LIM].notna()
    ins = M["Dataset group"] == "In scope"
    r_ok = M[LO].between(*R_BAND) & M[HI].between(*R_BAND)
    w_ok = (meas & M[RATE].between(*FAST)) | (lim & M[LIM].between(*SLOW))
    a = np.radians(M[RATE].where(meas, M[LIM])) ** 2 * M[HI] * 1000
    a_ok = a.notna() & (a <= A_MAX)
    geo = lambda ok: f"{int(ok.groupby(M['Bus family']).all().sum())} of {M['Bus family'].nunique()} bus geometries"
    print(f"\nrecommended bands")
    print(f"  r_perp {R_BAND[0]} to {R_BAND[1]} m (whole low-to-high line): {int(r_ok[ins].sum())} of {int(ins.sum())} in scope, "
          f"{int(r_ok.sum())} of {len(M)} objects, {geo(r_ok)}; outside: {', '.join(M[~r_ok]['name'])}")
    print(f"  rate {SLOW[0]} to {SLOW[1]} deg/s (no period): {int((lim & w_ok).sum())} of {int(lim.sum())}; "
          f"{FAST[0]} to {FAST[1]} deg/s (measured): {int((meas & w_ok).sum())} of {int(meas.sum())} "
          f"({int((meas & w_ok & ins).sum())} of {int((meas & ins).sum())} in scope)")
    print(f"  rate, both cases: {int(w_ok[ins].sum())} of {int(ins.sum())} in scope, {int(w_ok.sum())} of {len(M)} objects, "
          f"{geo(w_ok)}; not covered: {', '.join(M[~w_ok]['name'])}")
    print(f"  a <= {A_MAX} mm/s^2 at r_perp high: {int((a_ok & meas & ins).sum())} of {int((meas & ins).sum())} in-scope measured, "
          f"{int((a_ok & meas).sum())} of {int(meas.sum())} measured, {int((a_ok & lim).sum())} of {int(lim.sum())} no period, "
          f"{geo(a_ok)}; above: {', '.join(M[meas & ~a_ok]['name'])}")


def selection(M, path):
    D = M[M["MMT tracks with a period / total"].notna()].copy()
    split = D["MMT tracks with a period / total"].str.split("/", expand=True).astype(int)
    D["tracks"], D["share"] = split[1], split[0] / split[1]
    D["Lmax"] = D["NORAD ID"].map(max_track(path)).astype(float)
    D["alt"] = (D["Perigee (km)"].astype(float) + D["Apogee (km)"].astype(float)) / 2
    print("\nbrightness and size (objects with MMT data)")
    for yk, yl in (("tracks", "tracks"), ("share", "share of tracks with a period"), ("Lmax", "longest track")):
        for xk, xl in (("alt", "mean altitude"), ("h", "bus height"), ("Dry mass (kg)", "dry mass")):
            rho, n = rank_corr(D[xk], D[yk])
            print(f"  rank correlation {yl} vs {xl}: {rho:+.2f} (n={n})")
    meas = D[D["Rotation category"] == "Period measured"]
    none = D[D["Rotation category"] == "Below detection limit"]
    print(f"  {len(none)} of {len(D)} objects have no period; median tracks {meas.tracks.median():.0f} (measured) and "
          f"{none.tracks.median():.0f} (no period); median longest track {meas.Lmax.median():.0f} s and {none.Lmax.median():.0f} s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("tracks")
    ap.add_argument("--left-out", help="list of left-out folds (default: mmt_rotation/left_out_folds.csv)")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    M = read_master(a.workbook)
    sizes = bus_size(a.workbook)
    M["h"] = M["NORAD ID"].map(sizes).astype(float)
    M = M[M["Dataset group"].isin(SHOW)].copy()
    t = left_out.mark(read_tracks(a.tracks), a.left_out)
    plot_tau(M, t)
    plot_rate(M)
    quiet(M, t)
    recommend(M)
    selection(M, a.workbook)
    print("\nSaved to", OUT)


if __name__ == "__main__":
    main()
