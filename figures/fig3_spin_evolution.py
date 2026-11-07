import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from common import read_master, read_tracks
import left_out
from style import apply_style, GROUP_COLOR, INK, MUTED, GRID, marker_for, plot_path, legend_top

# NORAD id, years to fit. Left-out folds come from mmt_rotation/left_out_folds.csv (left_out.py).
PANELS = [
    (21263, (2014, 2023)),  # NOAA 12
    (25758, (2014, 2019)),  # IRS-P4
    (19531, (2014, 2017)),  # NOAA 11
    (23455, (2014, 2020)),  # NOAA 14
    (11060, (2014, 2016)),  # TIROS-N
    (23233, (2018, 2025)),  # DMSP F12
    (4362, (2016, 2021)),   # Nimbus 4
    (22739, None),          # NOAA 13
    (16969, (2017, 2020)),  # NOAA 10
    (13923, None),          # NOAA 8
    (11080, None),          # Nimbus 7
    (22076, (2014, 2022)),  # TOPEX
]
MIN_FIT = 4  # fits with fewer yearly points than this are drawn lighter and marked "indicative"
NOTE = {16969: "spin-up from 2021", 22739: "accelerating spin-down", 13923: "slowed 2017–18, then spun up",
        11080: "spinning up", 22076: "spin-up, then flat"}
BAND = (2.0, 5.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("tracks")
    ap.add_argument("--out", default=str(plot_path("fig3_spin_evolution.png")))
    ap.add_argument("--left-out", help="list of left-out folds (default: mmt_rotation/left_out_folds.csv)")
    a = ap.parse_args()
    M = read_master(a.workbook).set_index("NORAD ID")
    t = left_out.mark(read_tracks(a.tracks), a.left_out)

    apply_style()
    fig, axs = plt.subplots(3, 4, figsize=(7.0, 5.9), sharex=True, sharey=True)
    for ax, (nid, win) in zip(axs.flat, PANELS):
        o = M.loc[nid]
        col, mk = GROUP_COLOR[o["Dataset group"]], marker_for(o["Object type"])
        x = t[t.norad_id == nid]
        p = x[x.has_period].copy()
        p["rate"] = 360 / p.period_s
        out = p.left_out.to_numpy()

        ax.axhspan(*BAND, color=GRID, alpha=0.55, lw=0, zorder=0)
        ax.scatter(p.dec[~out], p.rate[~out], s=4, color=col, alpha=0.25, lw=0, zorder=2)
        ax.scatter(p.dec[out], p.rate[out], s=9, facecolor="none", edgecolor=col, lw=0.6, alpha=0.7, zorder=2)
        q = p[~out].groupby("year").agg(dec=("dec", "median"), per=("period_s", "median"))
        q["rate"] = 360 / q.per
        ax.plot(q.dec, q.rate, color=col, lw=0.9, alpha=0.8, zorder=3)
        ax.plot(q.dec, q.rate, ls="none", marker=mk, ms=3.6, mfc=col, mew=0, zorder=4)

        txt = NOTE.get(nid, "")
        if win:
            w = q[(q.index >= win[0]) & (q.index <= win[1])]
            s, c = np.polyfit(w.dec, np.log(w.rate), 1)
            xx = np.linspace(w.dec.min(), w.dec.max(), 50)
            weak = len(w) < MIN_FIT
            ax.plot(xx, np.exp(c + s * xx), color=MUTED if weak else INK, lw=0.8, ls=(0, (1, 1.5)) if weak else (0, (3, 2)),
                    zorder=5)
            if s < 0:
                txt = rf"$\tau$ = {-1/s:.1f} yr" + (", then spin-up" if nid == 16969 else "")
            else:
                txt = f"+{100*(np.exp(s)-1):.0f} %/yr" + (", then flat" if nid == 22076 else "")
            if weak:
                txt += f"\nindicative ({len(w)} yearly points)"
            print(f"  {o['name']}: fit {win[0]}-{win[1]}, {len(w)} yearly points, {txt.splitlines()[0]}")
        for y in sorted(set(x.year) - set(p.year)):
            ax.plot([y + 0.5], [1.25], marker="|", ms=4, color=MUTED, mew=0.8)

        ax.set_title(o["name"], fontsize=8, color=INK, pad=2, loc="left")
        ax.text(0.97, 0.95, txt, transform=ax.transAxes, ha="right", va="top", fontsize=6.6, color=INK)
        ax.set_yscale("log")
        ax.set_ylim(1.0, 150)
        ax.set_xlim(2013.6, 2026.2)
        ax.set_yticks([2, 5, 10, 20, 50, 100])
        ax.set_yticklabels(["2", "5", "10", "20", "50", "100"])
        ax.set_xticks([2015, 2020, 2025])
        ax.grid(True, axis="y", color=GRID, lw=0.4)
        ax.set_axisbelow(True)
        ax.tick_params(labelsize=7)
        ax.minorticks_off()

    h = [Line2D([], [], marker="o", ms=3.6, color=MUTED, lw=0.9, label="Yearly median"),
         Line2D([], [], marker="o", ms=2.5, color=MUTED, alpha=0.4, lw=0, label="Single light curve"),
         Line2D([], [], marker="o", ms=3, mfc="none", mec=MUTED, lw=0, label="Excluded period (not in the median)"),
         Line2D([], [], color=INK, lw=0.8, ls=(0, (3, 2)), label=r"Exponential fit, $\omega \propto e^{-t/\tau}$"),
         Line2D([], [], color=MUTED, lw=0.8, ls=(0, (1, 1.5)), label=f"Fit on fewer than {MIN_FIT} yearly points (indicative)"),
         Line2D([], [], marker="|", ms=5, color=MUTED, lw=0, mew=0.8, label="Observed, no period found"),
         Patch(facecolor=GRID, alpha=0.9, label="Assumed rotation range, 2–5 °/s")]
    fig.tight_layout(rect=(0.03, 0.015, 1, 0.9), h_pad=0.6, w_pad=0.4)
    fig.supylabel(r"Rotation rate, $\omega$ (°/s)", fontsize=9, x=0.005)
    fig.supxlabel("Year of observation", fontsize=9, y=0.0)
    legend_top(fig, h, 3, y=0.905)
    fig.savefig(a.out, dpi=300)
    print("Saved", a.out)


if __name__ == "__main__":
    main()
