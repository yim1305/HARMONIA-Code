import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from common import read_master, read_tracks
from style import apply_style, GROUP_COLOR, MUTED, GRID
import fig2_rate
fig2_rate.LABEL_FS = 6.4
from fig2_rate import place_line_labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("tracks")
    ap.add_argument("--out", default=str(Path(__file__).with_name("fig6_detection.png")))
    a = ap.parse_args()
    M = read_master(a.workbook).set_index("NORAD ID")
    t = read_tracks(a.tracks)
    t = t[t.norad_id.isin(M.index)]
    p = t[t.has_period]

    apply_style()
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(8, 330)
    ax.set_ylim(2.5, 120)
    L = np.geomspace(8, 330, 50)
    ax.fill_between(L, L / 1.2, 200, color=GRID, alpha=0.55, lw=0, zorder=0)
    for k, ls in ((1.2, "-"), (1.9, (0, (3, 2)))):
        ax.plot(L, L / k, color=MUTED, lw=0.7, ls=ls, zorder=1)
    ax.text(11, 80, "Not measurable:\nfewer than 1.2 cycles\nfit in the track", fontsize=6.8, color=MUTED,
            ha="left", va="top")
    for nid, g in p.groupby("norad_id"):
        col = GROUP_COLOR.get(M.loc[nid, "Dataset group"], MUTED)
        ax.scatter(g.track_length_s, g.period_s, s=5, color=col, alpha=0.35, lw=0, zorder=2)

    quiet = []
    for nid, x in t.groupby("norad_id"):
        pp = x[x.has_period]
        if pp.empty or x.year.max() - pp.year.max() < 3:
            continue
        last = pp.sort_values("dec").iloc[-1]
        col = GROUP_COLOR.get(M.loc[nid, "Dataset group"], MUTED)
        ax.plot(last.track_length_s, last.period_s, marker="o", ms=5.5, mfc=col, mec="white", mew=0.6, zorder=4,
                lw=0)
        quiet.append((last.track_length_s, last.period_s, M.loc[nid, "name"]))

    ax.set_xticks([10, 20, 50, 100, 200])
    ax.set_xticklabels(["10", "20", "50", "100", "200"])
    ax.set_yticks([3, 5, 10, 20, 50, 100])
    ax.set_yticklabels(["3", "5", "10", "20", "50", "100"])
    ax.minorticks_off()
    ax.set_xlabel("Track length, $L$ (s)")
    ax.set_ylabel("Period found, $P$ (s)")
    ax.grid(True, color=GRID, lw=0.4)
    ax.set_axisbelow(True)
    place_line_labels(fig, ax, quiet, list(ax.texts))
    h = [Line2D([], [], marker="o", ms=3, color=MUTED, alpha=0.5, lw=0, label="One track with a period"),
         Line2D([], [], marker="o", ms=5.5, mfc=MUTED, mec="white", lw=0, label="Last period before the object went quiet"),
         Line2D([], [], color=MUTED, lw=0.7, label="$P = L/1.2$ (shortest fold found)"),
         Line2D([], [], color=MUTED, lw=0.7, ls=(0, (3, 2)), label="$P = L/1.9$ (95% of folds are below)")]
    ax.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2, fontsize=6.8, frameon=False)
    fig.savefig(a.out, dpi=300)
    print("Saved", a.out)
    c = p.track_length_s / p.period_s
    print("cycles per track: 1%", round(c.quantile(0.01), 2), "5%", round(c.quantile(0.05), 2),
          "min", round(c.min(), 2))


if __name__ == "__main__":
    main()
