import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from common import read_master, read_tracks
import left_out
from style import apply_style, GROUP_COLOR, MUTED, GRID, plot_path, legend_top
import fig2_rate
fig2_rate.LABEL_FS = 6.4
from fig2_rate import place_line_labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("tracks")
    ap.add_argument("--out", default=str(plot_path("fig6_detection.png")))
    ap.add_argument("--left-out", help="list of left-out folds (default: mmt_rotation/left_out_folds.csv)")
    a = ap.parse_args()
    M = read_master(a.workbook).set_index("NORAD ID")
    t = left_out.mark(read_tracks(a.tracks), a.left_out)
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
    ax.text(11, 80, "Not measurable:\nfewer than 1.2 cycles\nfit in the light curve", fontsize=6.8, color=MUTED,
            ha="left", va="top")
    for nid, g in p.groupby("norad_id"):
        col = GROUP_COLOR.get(M.loc[nid, "Dataset group"], MUTED)
        k = g[~g.left_out]
        ax.scatter(k.track_length_s, k.period_s, s=5, color=col, alpha=0.35, lw=0, zorder=2)
        d = g[g.left_out]
        ax.scatter(d.track_length_s, d.period_s, s=9, facecolor="none", edgecolor=col, lw=0.6, alpha=0.7, zorder=2)

    quiet = []
    for nid, x in t.groupby("norad_id"):
        pp = x[x.has_period & ~x.left_out]
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
    ax.set_xlabel("Light-curve length, $L$ (s)")
    ax.set_ylabel("Measured period, $P$ (s)")
    ax.grid(True, color=GRID, lw=0.4)
    ax.set_axisbelow(True)
    place_line_labels(fig, ax, quiet, list(ax.texts))
    h = [Line2D([], [], marker="o", ms=3, color=MUTED, alpha=0.5, lw=0, label="Light curve with a period"),
         Line2D([], [], marker="o", ms=3, mfc="none", mec=MUTED, lw=0, label="Excluded period"),
         Line2D([], [], marker="o", ms=5.5, mfc=MUTED, mec="white", lw=0, label="Last period before 3+ years with none"),
         Line2D([], [], color=MUTED, lw=0.7, label="$P = L/1.2$ (fewest cycles found)"),
         Line2D([], [], color=MUTED, lw=0.7, ls=(0, (3, 2)), label="$P = L/1.9$ (95% of periods lie below)")]
    legend_top(ax, h, 2)
    fig.savefig(a.out, dpi=300)
    print("Saved", a.out)
    # all folds count here: the question is what MMT can detect, not whether the period is the real rotation
    c = p.track_length_s / p.period_s
    print("cycles per track (all", len(p), "periods): 1%", round(c.quantile(0.01), 2), "5%",
          round(c.quantile(0.05), 2), "min", round(c.min(), 2), "| share with >= 1.9:", round((c >= 1.9).mean(), 3))


if __name__ == "__main__":
    main()
