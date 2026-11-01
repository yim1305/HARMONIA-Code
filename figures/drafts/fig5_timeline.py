import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from matplotlib.patches import Patch, Rectangle

from common import read_master, read_tracks
from style import apply_style, INK, GRID

SHOW = ("In scope", "Near scope", "Orbit out", "Rocket body", "Reference (out of scope)", "Not intact")
FAMILY_ORDER = ["Nimbus/Landsat (sensory ring)", "TIROS-N/ATN", "DMSP Block 5D-2", "IRS-1 bus", "PROTEUS", "FY-1"]
RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
EMPTY = "#ebeae6"
YEARS = list(range(2014, 2026))
# (NORAD id, year) where a fold was left out, marked with *
HARMONIC = {(23940, 2016), (23940, 2024), (23940, 2025), (23233, 2016), (23233, 2017), (11080, 2018)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("tracks")
    ap.add_argument("--out", default=str(Path(__file__).with_name("fig5_timeline.png")))
    a = ap.parse_args()
    M = read_master(a.workbook)
    t = read_tracks(a.tracks)
    M = M[M["Dataset group"].isin(SHOW) & M["NORAD ID"].isin(t.norad_id.unique())].copy()
    fam_n = M["Bus family"].value_counts()
    M["block"] = np.where(M["Bus family"].map(fam_n) > 1, M["Bus family"], "Single designs")
    blocks = [b for b in FAMILY_ORDER if b in set(M.block)] + ["Single designs"]
    cmap = mcolors.LinearSegmentedColormap.from_list("b", RAMP)
    norm = mcolors.LogNorm(5, 100)

    apply_style()
    fig, ax = plt.subplots(figsize=(7.0, 0.142 * (len(M) + len(blocks)) + 0.9))
    y, ticks, names = 0, [], []
    for b in blocks:
        ax.text(-0.02, y, b, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=6.8,
                style="italic", color=INK)
        y += 1
        for _, o in M[M.block == b].sort_values("Launch year").iterrows():
            x = t[t.norad_id == o["NORAD ID"]]
            for i, yr in enumerate(YEARS):
                xx = x[x.year == yr]
                if xx.empty:
                    continue
                pp = xx[xx.has_period]
                if pp.empty:
                    ax.add_patch(Rectangle((i - 0.46, y - 0.42), 0.92, 0.84, color=EMPTY, lw=0))
                    continue
                r = 360 / pp.period_s.median()
                c = cmap(norm(np.clip(r, 5, 100)))
                ax.add_patch(Rectangle((i - 0.46, y - 0.42), 0.92, 0.84, color=c, lw=0))
                lum = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
                star = "*" if (o["NORAD ID"], yr) in HARMONIC else ""
                ax.text(i, y, f"{r:.0f}{star}", ha="center", va="center", fontsize=5.6,
                        color="white" if lum < 0.5 else INK)
            ticks.append(y)
            names.append(f"{o['name']}  {100 * x.has_period.mean():.0f}%")
            y += 1

    ax.set_xlim(-0.6, len(YEARS) - 0.4)
    ax.set_ylim(y - 0.5, -0.6)
    ax.set_xticks(range(len(YEARS)))
    ax.set_xticklabels([str(v) for v in YEARS], fontsize=7)
    ax.xaxis.tick_top()
    ax.set_yticks(ticks)
    ax.set_yticklabels(names, fontsize=6.6)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    h = [Patch(facecolor=RAMP[1], label="Period: yearly median rate (°/s)"),
         Patch(facecolor=EMPTY, label="Tracks, but no period"),
         Patch(facecolor="white", edgecolor=GRID, label="No tracks"),
         Patch(facecolor="none", edgecolor="none", label="* includes a fold left out")]
    ax.legend(handles=h, loc="upper center", bbox_to_anchor=(0.45, -0.005), ncol=4, fontsize=6.6, frameon=False,
              handlelength=1.2, columnspacing=1.2)
    fig.savefig(a.out, dpi=300)
    print("Saved", a.out)


if __name__ == "__main__":
    main()
