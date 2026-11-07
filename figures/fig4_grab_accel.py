"""Fig 4: rotation rate against the grab-point distance from the spin axis, with lines of equal centripetal
acceleration a = omega^2 r_perp.

A servicer holding station beside the grab point needs a thrust of (its mass) x omega^2 r_perp, so each
acceleration line is a thrust per kg of servicer. Each object is drawn as a range from r_perp low (spin
about the long axis) to r_perp high (highest z, largest ring), at its latest-year rate, or at its detection
limit with an arrow down if it has no period. Needs the Excel save like fig1 (r_perp values are formulas).
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from common import read_master
from style import apply_style, GROUP_COLOR, SCOPE_LABEL, SCOPE_ORDER, TYPE_SCALE, marker_for, MUTED, GRID, INK, plot_path, legend_top
from fig2_rate import CYCLES, spread

SHOW = ("In scope", "Near scope", "Orbit out", "Rocket body")
ACCELS = [1, 3, 10, 30, 100, 300, 1000]  # mm/s^2
BAND = (2.0, 5.0)
XL = (0.25, 4.5)
LABEL_FS = 6.4  # same as the object labels in figs 2 and 6
LO, HI = "r⊥ low (m)", "r⊥ high (m)"
SPIN = "Likely spin state (from moments of inertia)"


def omega_deg(a_mm, r):
    return np.degrees(np.sqrt(a_mm / 1000 / r))


LEADER = "#cfcec9"


def side_labels(fig, ax, labels):
    """Names in a column to the right of the panel. A faint leader runs from the right end of each line, at
    the object's own rate, to its name, so no label sits on the data."""
    fig.canvas.draw()
    to_ax = ax.transAxes.inverted()
    pts = sorted(((*to_ax.transform(ax.transData.transform((x, y))), txt) for x, y, txt in labels),
                 key=lambda p: p[1])
    gap = (LABEL_FS + 1.4) / (ax.get_window_extent().height * 72 / fig.dpi)
    ys = spread([p[1] for p in pts], gap)
    ys += max(0, -ys.min()) - max(0, ys.max() - 1)  # keep the column inside the panel height
    for (xa, ya, txt), yl in zip(pts, ys):
        ax.plot([xa + 0.012, 1.0, 1.03], [ya, ya, yl], transform=ax.transAxes, clip_on=False, color=LEADER,
                lw=0.5, zorder=1)
        ax.text(1.038, yl, txt, transform=ax.transAxes, fontsize=LABEL_FS, color=INK, ha="left", va="center")


def accel_lines(ax, ylim):
    rr = np.geomspace(*XL, 60)
    for acc in ACCELS:
        ax.plot(rr, omega_deg(acc, rr), color=MUTED, lw=0.5, ls=(0, (1, 2)), zorder=1)
        # label just inside where the line comes in at the top or left edge
        r_top = acc / 1000 / np.radians(ylim[1]) ** 2
        xe = max(XL[0], r_top) * 1.08
        ye = omega_deg(acc, xe)
        if ye < ylim[0] * 1.15 or xe > XL[1] / 1.6:
            continue
        p0, p1 = ax.transData.transform([(xe, ye), (xe * 1.2, omega_deg(acc, xe * 1.2))])
        ang = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
        ax.text(xe, ye, f" {acc:g} mm/s²", rotation=ang, rotation_mode="anchor", fontsize=LABEL_FS, color=MUTED,
                ha="left", va="bottom", zorder=1)


def draw_panel(fig, ax, M, ylim, yticks, tag):
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(*XL)
    ax.set_ylim(*ylim)
    ax.axhspan(*BAND, color=GRID, alpha=0.55, lw=0, zorder=0)
    fig.canvas.draw()
    accel_lines(ax, ylim)
    merged = {}
    for _, o in M.iterrows():
        col, mk = GROUP_COLOR[o["Dataset group"]], marker_for(o["Object type"])
        sc = TYPE_SCALE[mk]
        lo, hi, w = o[LO], o[HI], o["w"]
        ax.plot([lo, hi], [w, w], color=col, lw=1.2, solid_capstyle="round", zorder=3)
        for xv in (lo, hi):
            ax.plot(xv, w, marker=mk, ms=3.8 * sc, mfc="white", mec=col, mew=0.9, zorder=4)
        if "high" in str(o.get(SPIN) or ""):
            ax.plot(hi, w, marker="o", ms=8, mfc="none", mec=col, mew=0.7, zorder=4)
        if not o["meas"]:
            xm = np.sqrt(lo * hi)
            ax.annotate("", (xm, w / 1.12), (xm, w), zorder=3,
                        arrowprops=dict(arrowstyle="-|>,head_width=0.12,head_length=0.22", color=col, lw=0.6,
                                        shrinkA=0, shrinkB=0))
        # same r range and a rate within about 5%: one label
        merged.setdefault((round(lo, 3), round(hi, 3), round(np.log10(w) * 50)), []).append((hi, w, o["name"]))
    side_labels(fig, ax, [(g[0][0], g[0][1], ", ".join(n for _, _, n in g)) for g in merged.values()])
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"{v:g}" for v in yticks])
    ax.minorticks_off()
    ax.grid(True, color=GRID, lw=0.4)
    ax.set_axisbelow(True)
    ax.set_title(tag, loc="left", fontsize=8, color=INK, pad=3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("--out", default=str(plot_path("fig4_grab_accel.png")))
    a = ap.parse_args()
    M = read_master(a.workbook)
    M = M[M["Dataset group"].isin(SHOW) & M[LO].notna() & M[HI].notna()].copy()
    meas = M["Rotation category"] == "Period measured"
    M["w"] = np.where(meas, M["Rotation rate, latest year (deg/s)"], M["Detection limit, longest track (deg/s)"])
    M["meas"] = meas
    skipped = M.loc[M["w"].isna(), "name"].tolist()
    M = M[M["w"].notna()]

    apply_style()
    fig, (top, bot) = plt.subplots(2, 1, figsize=(7.0, 7.0), sharex=True, gridspec_kw=dict(height_ratios=[1, 1]))
    fig.subplots_adjust(right=0.82, hspace=0.16)
    draw_panel(fig, top, M[M["meas"]], (5.0, 45), [5, 10, 20, 40], "(a) Measured rotation rate (most recent year)")
    draw_panel(fig, bot, M[~M["meas"]], (1.2, 7.0), [1.5, 2, 3, 5],
               rf"(b) No period detected: upper limit ${CYCLES:g} \times 360/L_{{\max}}$")
    bot.set_xticks([0.3, 0.5, 1, 2, 3, 4])
    bot.set_xticklabels(["0.3", "0.5", "1", "2", "3", "4"])
    bot.set_xlabel(r"Distance from the spin axis to the grab point, $r_\perp$ (m)")
    fig.supylabel(r"Rotation rate, $\omega$ (°/s)", fontsize=9, x=0.035)

    k = dict(lw=0, mew=0.9)
    h = [Line2D([], [], color=MUTED, lw=1.2, marker="o", ms=3.8, mfc="white", mec=MUTED, mew=0.9,
                label=r"Range of $r_\perp$, from $r_{\perp,\mathrm{low}}$ to $r_{\perp,\mathrm{high}}$"),
         Line2D([], [], marker="o", ms=8, mfc="none", mec=MUTED, mew=0.7, lw=0,
                label="Circle: likely spin state from moments of inertia"),
         Line2D([], [], color=MUTED, lw=0.5, ls=(0, (1, 2)),
                label=r"Constant centripetal acceleration, $a=\omega^2 r_\perp$"),
         Patch(facecolor=GRID, alpha=0.9, label="Assumed rotation range, 2–5 °/s")]
    groups, seen = set(M["Dataset group"]), []
    for g in SCOPE_ORDER + ["Rocket body"]:
        if (g in groups or (g == "Orbit out" and "Rocket body" in groups)) and SCOPE_LABEL[g] not in seen:
            seen.append(SCOPE_LABEL[g])
            h.append(Line2D([], [], color=GROUP_COLOR[g], lw=1.6, label=SCOPE_LABEL[g]))
    h.append(Line2D([], [], marker="^", ms=3.8 * 1.15, mfc="white", mec=MUTED, label="Rocket body", **k))
    legend_top(top, h, 2, y=1.08)
    fig.savefig(a.out, dpi=300)
    print("Saved", a.out)

    # a = omega^2 r_perp for the memo (mm/s^2), measured objects only
    m = M[M["meas"]]
    wr = np.radians(m["w"])
    acc_lo, acc_hi = (wr ** 2 * m[LO] * 1000), (wr ** 2 * m[HI] * 1000)
    print(f"Measured objects: a from {acc_lo.min():.0f} to {acc_hi.max():.0f} mm/s^2")
    for (_, o), al_, ah_ in sorted(zip(m.iterrows(), acc_lo, acc_hi), key=lambda z: z[2]):
        print(f"  {o['name']:<16} {o['Dataset group']:<11} w={o['w']:5.1f} deg/s  a={al_:6.0f} to {ah_:6.0f} mm/s^2")
    if skipped:
        print("No rate or limit yet (left out):", ", ".join(skipped))


if __name__ == "__main__":
    main()
