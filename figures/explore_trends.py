"""Exploratory plots (not in the memo yet), saved to plots/explore/:

  explore_accel_cdf.png         share of objects a servicer could handle, against the centripetal acceleration
                                a = omega^2 r_perp it can match (thrust per kg of servicer)
  explore_tau_vs_properties.png spin-down e-folding time tau against mass, mean altitude and bus height
  explore_rate_vs_size.png      latest-year rotation rate against mass and bus height

    py explore_trends.py ..\\..\\HARMONIA_data_v2.xlsx ..\\mmt_rotation\\data\\pull_2026-10-24\\mmt_tracks.csv
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import left_out
from common import read_master, read_tracks
from fig3_spin_evolution import PANELS
from style import (apply_style, GROUP_COLOR, SCOPE_LABEL, SCOPE_ORDER, TYPE_SCALE, marker_for, INK, MUTED, GRID,
                   PLOTS, legend_top)

SHOW = ("In scope", "Near scope", "Orbit out", "Rocket body")
LO, HI = "r⊥ low (m)", "r⊥ high (m)"
RATE, LIM = "Rotation rate, latest year (deg/s)", "Detection limit, longest track (deg/s)"
OUT = PLOTS / "explore"


def accel(w_deg, r):
    return np.radians(w_deg) ** 2 * r * 1000  # mm/s^2


def bus_size(path):
    rp = openpyxl.load_workbook(path, data_only=True)["r_P"]
    H = {rp.cell(1, c).value: c for c in range(1, rp.max_column + 1)}
    return {rp.cell(r, 3).value: rp.cell(r, H["Bus height h (m)"]).value for r in range(2, 62) if rp.cell(r, 3).value}


def scope_handles(groups):
    h, seen = [], []
    for g in SCOPE_ORDER + ["Rocket body"]:
        if (g in groups or (g == "Orbit out" and "Rocket body" in groups)) and SCOPE_LABEL[g] not in seen:
            seen.append(SCOPE_LABEL[g])
            h.append(Line2D([], [], color=GROUP_COLOR[g], lw=0, marker="o", ms=5, mew=0, label=SCOPE_LABEL[g]))
    return h


def step_cdf(ax, values, **kw):
    v = np.sort(np.asarray(values, float))
    y = np.arange(1, len(v) + 1) / len(v) * 100
    ax.step(np.r_[v[0], v], np.r_[0, y], where="post", **kw)


def plot_cdf(M):
    meas = M[(M["Rotation category"] == "Period measured") & M[RATE].notna()]
    lim = M[(M["Rotation category"] == "Below detection limit") & M[LIM].notna()]
    a_lo, a_hi = accel(meas[RATE], meas[LO]), accel(meas[RATE], meas[HI])
    l_hi = accel(lim[LIM], lim[HI])

    apply_style()
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    ax.set_xscale("log")
    # shade between the two r_perp cases
    grid = np.geomspace(1, 1500, 400)
    f_lo = [(a_lo <= g).mean() * 100 for g in grid]
    f_hi = [(a_hi <= g).mean() * 100 for g in grid]
    ax.fill_between(grid, f_hi, f_lo, color=GROUP_COLOR["In scope"], alpha=0.12, lw=0, step="post")
    step_cdf(ax, a_lo, color=GROUP_COLOR["In scope"], lw=1.2, ls=(0, (3, 2)))
    step_cdf(ax, a_hi, color=GROUP_COLOR["In scope"], lw=1.4)
    step_cdf(ax, l_hi, color=MUTED, lw=1.2)
    ax.set_xlim(1, 1500)
    ax.set_ylim(0, 102)
    ax.set_xticks([1, 3, 10, 30, 100, 300, 1000])
    ax.set_xticklabels(["1", "3", "10", "30", "100", "300", "1000"])
    ax.minorticks_off()
    ax.set_xlabel(r"Centripetal acceleration at the grab point, $a=\omega^2 r_\perp$ (mm/s²)")
    ax.set_ylabel("Objects at or below a (%)")
    ax.grid(True, color=GRID, lw=0.4)
    ax.set_axisbelow(True)
    h = [Line2D([], [], color=GROUP_COLOR["In scope"], lw=1.4,
                label=rf"Measured period, $r_{{\perp,\mathrm{{high}}}}$ ({len(meas)} objects)"),
         Line2D([], [], color=GROUP_COLOR["In scope"], lw=1.2, ls=(0, (3, 2)),
                label=r"Measured period, $r_{\perp,\mathrm{low}}$"),
         Patch(facecolor=GROUP_COLOR["In scope"], alpha=0.12, label=r"Range between the two $r_\perp$ cases"),
         Line2D([], [], color=MUTED, lw=1.2,
                label=rf"No period detected, upper bound at $r_{{\perp,\mathrm{{high}}}}$ ({len(lim)} objects)")]
    legend_top(ax, h, 2)
    fig.savefig(OUT / "explore_accel_cdf.png", dpi=300)
    plt.close(fig)

    print("\n[1] a = w^2 r_perp (mm/s^2)")
    for q in (50, 80, 90, 100):
        print(f"  measured: {q:3d}% of objects need at most {np.percentile(a_lo, q):6.0f} (r_perp low) "
              f"to {np.percentile(a_hi, q):6.0f} (r_perp high)")
    print(f"  no period (upper bound, r_perp high): {l_hi.min():.0f} to {l_hi.max():.0f}, median {np.median(l_hi):.0f}")
    ins = meas["Dataset group"] == "In scope"
    print(f"  in scope only ({ins.sum()}): r_perp high max {a_hi[ins].max():.0f}, median {np.median(a_hi[ins]):.0f}")


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
        ax.grid(True, color=GRID, lw=0.4)
        ax.set_axisbelow(True)
    axs[0].set_ylabel(r"Spin-down time, $\tau$ (years)")
    axs[0].set_ylim(0, 7.5)
    for f in F:  # name each point once, on the altitude panel, where they spread out most
        axs[1].annotate(f["name"].replace("DMSP 5D-2 ", "DMSP "), (f["alt"], f["tau"]), xytext=(4, 2),
                        textcoords="offset points", fontsize=6.2, color=INK)
    h = scope_handles({f["group"] for f in F})
    h.append(Line2D([], [], color=MUTED, lw=0, marker="o", ms=5, mfc="white", mew=1.0,
                    label="Fit on fewer than 4 yearly points"))
    fig.tight_layout(rect=(0, 0, 1, 0.85), w_pad=0.6)
    legend_top(fig, h, 3, y=0.86)
    fig.savefig(OUT / "explore_tau_vs_properties.png", dpi=300)
    plt.close(fig)

    print("\n[5] tau fits")
    for f in sorted(F, key=lambda f: f["tau"]):
        print(f"  {f['name']:<14} tau {f['tau']:4.1f} yr  n={f['n']:2d}  {f['family']:<30} mass {f['mass']:5.0f}  "
              f"alt {f['alt']:5.0f}  h {f['h']}")
    fams = {f["family"] for f in F}
    print(f"  {len(F)} fits from {len(fams)} bus families; "
          f"{sum(f['family'] == 'TIROS-N/ATN' for f in F)} are TIROS-N/ATN")
    for k in ("mass", "alt", "h"):
        x = np.array([f[k] for f in F], float); y = np.array([f["tau"] for f in F])
        print(f"  Spearman-style rank correlation tau vs {k}: {np.corrcoef(np.argsort(np.argsort(x)), np.argsort(np.argsort(y)))[0, 1]:+.2f}")


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
        ax.grid(True, color=GRID, lw=0.4)
        ax.set_axisbelow(True)
    axs[0].set_ylabel(r"Rotation rate, $\omega$ (°/s)")
    h = scope_handles(set(meas["Dataset group"]) | set(lim["Dataset group"]))
    h += [Line2D([], [], color=MUTED, lw=0, marker="o", ms=5, mew=0, label="Measured period (latest year)"),
          Line2D([], [], color=MUTED, lw=0, marker="o", ms=4, mfc="white", mew=0.8,
                 label="No period detected (upper limit)"),
          Patch(facecolor=GRID, alpha=0.9, label="Assumed rotation range, 2–5 °/s")]
    fig.tight_layout(rect=(0, 0, 1, 0.84), w_pad=0.8)
    legend_top(fig, h, 3, y=0.85)
    fig.savefig(OUT / "explore_rate_vs_size.png", dpi=300)
    plt.close(fig)

    print("\n[6] rate vs size (measured objects)")
    for k in ("Dry mass (kg)", "h"):
        x, y = meas[k].astype(float).to_numpy(), meas[RATE].astype(float).to_numpy()
        ok = ~np.isnan(x)
        rx, ry = np.argsort(np.argsort(x[ok])), np.argsort(np.argsort(y[ok]))
        print(f"  rank correlation rate vs {k}: {np.corrcoef(rx, ry)[0, 1]:+.2f} (n={ok.sum()})")
    ys = meas["Years since end of life"].astype(float).to_numpy()
    rx, ry = np.argsort(np.argsort(ys)), np.argsort(np.argsort(meas[RATE].astype(float).to_numpy()))
    print(f"  for comparison, rate vs years since end of life: {np.corrcoef(rx, ry)[0, 1]:+.2f}")


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
    plot_cdf(M)
    plot_tau(M, t)
    plot_rate(M)
    print("\nSaved to", OUT)


if __name__ == "__main__":
    main()
