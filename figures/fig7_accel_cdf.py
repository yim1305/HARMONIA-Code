"""Fig 7: share of objects at or below each centripetal acceleration at the grab point, a = w^2 r_perp.

A servicer holding position beside the grab point needs a thrust of its mass times a, so this reads as the
share of objects a capture system rated for a given a could handle. Measured objects are drawn for both
r_perp cases (low and high); objects with no period are drawn at their upper limit with r_perp high.
Reference and not-intact objects are left out (same objects as Figure 4).

    py fig7_accel_cdf.py ..\\..\\HARMONIA_data_v2.xlsx
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from common import read_master
from style import FS, GRID_LW, save, apply_style, INK, MUTED, GRID, plot_path, legend_top

SHOW = ("In scope", "Near scope", "Orbit out", "Rocket body")
LO, HI = "r⊥ low (m)", "r⊥ high (m)"
RATE, LIM = "Rotation rate, latest year (deg/s)", "Detection limit, longest track (deg/s)"


def accel(w_deg, r):
    return np.radians(w_deg) ** 2 * r * 1000  # mm/s^2


def step_cdf(ax, values, **kw):
    v = np.sort(np.asarray(values, float))
    y = np.arange(1, len(v) + 1) / len(v) * 100
    ax.step(np.r_[v[0], v], np.r_[0, y], where="post", **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("--out", default=str(plot_path("fig7_accel_cdf.png")))
    a = ap.parse_args()
    M = read_master(a.workbook)
    M = M[M["Dataset group"].isin(SHOW)]
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
    ax.fill_between(grid, f_hi, f_lo, color=INK, alpha=0.07, lw=0, step="post")
    step_cdf(ax, a_lo, color=INK, lw=1.0, ls=(0, (3, 2)))
    step_cdf(ax, a_hi, color=INK, lw=1.3)
    step_cdf(ax, l_hi, color=MUTED, lw=1.2)
    ax.set_xlim(1, 1500)
    ax.set_ylim(0, 102)
    ax.set_xticks([1, 3, 10, 30, 100, 300, 1000])
    ax.set_xticklabels(["1", "3", "10", "30", "100", "300", "1000"])
    ax.minorticks_off()
    ax.set_xlabel(r"Centripetal acceleration at the grab point, $a=\omega^2 r_\perp$ (mm/s²)")
    ax.set_ylabel(r"Objects at or below $a$ (%)")
    ax.grid(True, color=GRID, lw=GRID_LW)
    ax.set_axisbelow(True)
    h = [Line2D([], [], color=INK, lw=1.3,
                label=rf"Measured period, $r_{{\perp,\mathrm{{high}}}}$ ({len(meas)} objects)"),
         Line2D([], [], color=INK, lw=1.0, ls=(0, (3, 2)),
                label=r"Measured period, $r_{\perp,\mathrm{low}}$"),
         Patch(facecolor=INK, alpha=0.07, label=r"Range between the two $r_\perp$ cases"),
         Line2D([], [], color=MUTED, lw=1.2,
                label=rf"No period detected, upper bound at $r_{{\perp,\mathrm{{high}}}}$ ({len(lim)} objects)")]
    legend_top(ax, h, 2)
    save(fig, a.out)
    plt.close(fig)

    print(f"Saved {a.out}")
    print(f"  measured ({len(meas)}): a from {a_lo.min():.0f} (r_perp low) to {a_hi.max():.0f} (r_perp high) mm/s^2")
    for q in (50, 80, 90, 100):
        print(f"    {q:3d}% of measured objects need at most {np.percentile(a_lo, q):4.0f} (r_perp low) "
              f"to {np.percentile(a_hi, q):4.0f} (r_perp high)")
    ins = (meas["Dataset group"] == "In scope").to_numpy()
    print(f"  in scope only ({ins.sum()}): r_perp high max {a_hi[ins].max():.0f}, median {np.median(a_hi[ins]):.0f}")
    print(f"  no period ({len(lim)}, upper bound, r_perp high): {l_hi.min():.0f} to {l_hi.max():.0f}, "
          f"median {np.median(l_hi):.0f}")


if __name__ == "__main__":
    main()
