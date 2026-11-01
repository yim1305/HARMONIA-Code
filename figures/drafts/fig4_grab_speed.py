import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from common import read_master
from style import apply_style, GROUP_COLOR, SCOPE_LABEL, SCOPE_ORDER, TYPE_SCALE, marker_for, MUTED, GRID
import fig2_rate
fig2_rate.LABEL_FS = 6.0
from fig2_rate import place_line_labels

SHOW = ("In scope", "Near scope", "Orbit out", "Rocket body")
SPEEDS = [0.03, 0.1, 0.3, 1, 3]
BAND = (2.0, 5.0)
XL, YL = (0.55, 3.6), (0.9, 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("--out", default=str(Path(__file__).with_name("fig4_grab_speed.png")))
    a = ap.parse_args()
    M = read_master(a.workbook)
    M = M[M["Dataset group"].isin(SHOW) & M["r_P full (m)"].notna()].copy()
    meas = M["Rotation category"] == "Period measured"
    M["w"] = np.where(meas, M["Rotation rate, latest year (deg/s)"], M["Detection limit, longest track (deg/s)"])
    M["meas"] = meas
    skipped = M.loc[M["w"].isna(), "name"].tolist()
    M = M[M["w"].notna()]

    apply_style()
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(*XL)
    ax.set_ylim(*YL)
    ax.axhspan(*BAND, color=GRID, alpha=0.55, lw=0, zorder=0)
    rr = np.geomspace(*XL, 50)
    fig.canvas.draw()
    for v in SPEEDS:
        ax.plot(rr, np.degrees(v / rr), color=MUTED, lw=0.5, ls=(0, (1, 2)), zorder=1)
        # label where the line comes in at the top or left edge
        xe = max(XL[0], np.degrees(v) / YL[1]) * 1.12
        ye = np.degrees(v / xe)
        if ye < YL[0] * 1.3:
            continue
        p0, p1 = ax.transData.transform([(xe, ye), (xe * 1.2, np.degrees(v / (xe * 1.2)))])
        ang = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
        ax.text(xe, ye, f"  {v:g} m/s", rotation=ang, rotation_mode="anchor", fontsize=6.4, color=MUTED,
                ha="left", va="bottom", zorder=1)

    merged = {}
    for _, o in M.iterrows():
        col, mk = GROUP_COLOR[o["Dataset group"]], marker_for(o["Object type"])
        f, w = o["r_P full (m)"], o["w"]
        al = 1.0 if o["meas"] else 0.55
        ax.plot(f, w, marker=mk, ms=5.6 * TYPE_SCALE[mk], mfc=col, mew=0, alpha=al, zorder=4)
        if not o["meas"]:
            ax.annotate("", (f, w / 1.22), (f, w), arrowprops=dict(arrowstyle="-|>,head_width=0.13,head_length=0.25",
                        color=col, lw=0.7, shrinkA=2.5, shrinkB=0, alpha=al), zorder=3)
        merged.setdefault((round(f, 2), round(w)), []).append(o["name"])
    lab = [(x, y, ", ".join(ns)) for (x, y), ns in merged.items()]

    ax.set_xticks([0.6, 0.8, 1, 1.5, 2, 3])
    ax.set_xticklabels(["0.6", "0.8", "1", "1.5", "2", "3"])
    ax.set_yticks([1, 2, 5, 10, 20, 50])
    ax.set_yticklabels(["1", "2", "5", "10", "20", "50"])
    ax.minorticks_off()
    ax.set_xlabel(r"Distance from the spin axis to the grab point, $r$ (m)")
    ax.set_ylabel(r"Rotation rate, $\omega$ (°/s)")
    place_line_labels(fig, ax, lab, list(ax.texts))

    h = [Line2D([], [], marker="o", ms=5.2, mfc=MUTED, mew=0, lw=0, label=r"$r_P$ full at the latest-year rate"),
         Line2D([], [], marker="v", ms=4.5, color=MUTED, alpha=0.6, lw=0, label="No period: rate below this limit"),
         Line2D([], [], color=MUTED, lw=0.5, ls=(0, (1, 2)), label=r"Equal grab-point speed, $v=\omega r$"),
         Patch(facecolor=GRID, alpha=0.9, label="Task-sheet band, 2–5 °/s")]
    groups, seen = set(M["Dataset group"]), []
    for g in SCOPE_ORDER + ["Rocket body"]:
        if (g in groups or (g == "Orbit out" and "Rocket body" in groups)) and SCOPE_LABEL[g] not in seen:
            seen.append(SCOPE_LABEL[g])
            h.append(Line2D([], [], color=GROUP_COLOR[g], lw=1.6, label=SCOPE_LABEL[g]))
    h.append(Line2D([], [], marker="^", ms=5.2 * 1.15, mfc=MUTED, mew=0, lw=0, label="Rocket body (triangle)"))
    ax.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=3, fontsize=6.8, frameon=False,
              handlelength=1.8, columnspacing=1.2)
    ax.grid(True, color=GRID, lw=0.4)
    ax.set_axisbelow(True)
    fig.savefig(a.out, dpi=300)
    print("Saved", a.out)
    if skipped:
        print("No rate or limit yet (left out):", ", ".join(skipped))


if __name__ == "__main__":
    main()
