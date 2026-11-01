import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import numpy as np
import openpyxl
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.legend_handler import HandlerTuple
from matplotlib.patches import Patch

from style import apply_style, GROUP_COLOR, SCOPE_LABEL, SCOPE_ORDER, TYPE_LABEL, TYPE_SCALE, marker_for, INK, MUTED, GRID

TASK_BAND = (2.0, 5.0)  # deg/s from the task sheet
SHOW = ("In scope", "Near scope", "Orbit out", "Rocket body", "Reference (out of scope)")
BASELINE = 0.8
DROP = 1.32
LABEL_FS = 6.4


def headers(ws, row):
    return {ws.cell(row, c).value: c for c in range(1, ws.max_column + 1) if ws.cell(row, c).value}


def short(name):
    return (name.replace(" (UO-36)", "").replace(" (Arirang-1)", "").replace(" (Kirari)", "")
                .replace("DMSP 5D-2 ", "DMSP ").replace("TOPEX/Poseidon", "TOPEX").replace(" R/B", ""))


def read_workbook(path):
    wb = openpyxl.load_workbook(path)
    m, lc = wb["Master"], wb["Light curve"]
    M, LC = headers(m, 11), headers(lc, 1)
    objs = {}
    for r in range(12, 72):
        nid = m.cell(r, M["NORAD ID"]).value
        if not isinstance(nid, int):
            continue
        eol = m.cell(r, M["End-of-life year"]).value
        objs[nid] = dict(name=short(m.cell(r, M["Name"]).value), group=m.cell(r, M["Dataset group"]).value,
                         eol=eol if isinstance(eol, (int, float)) else None, type=m.cell(r, M["Object type"]).value)
    for r in range(2, 62):
        nid = lc.cell(r, LC["NORAD ID"]).value
        if nid not in objs:
            continue
        o = objs[nid]
        o["med_len"] = lc.cell(r, LC["Median track length (s)"]).value
        o["max_len"] = lc.cell(r, LC["Max track length (s)"]).value
        o["n_period"] = lc.cell(r, LC["Tracks with a period"]).value or 0
        o["by_hand"] = str(lc.cell(r, LC["Latest-year values set by hand"]).value or "").strip().lower() == "yes"
        o["hand_year"] = lc.cell(r, LC["Latest year with a period"]).value
    return objs


def spread(xs, gap):
    """Push sorted positions apart until neighbours are at least gap apart."""
    out = np.array(xs, float)
    for _ in range(300):
        moved = False
        for i in range(len(out) - 1):
            d = out[i + 1] - out[i]
            if d < gap:
                s = (gap - d) / 2
                out[i] -= s
                out[i + 1] += s
                moved = True
        if not moved:
            break
    return out


def data_points(fig, ax, step=1.5):
    """Points (in pixels) along every line, arrow and dot, so labels can avoid them."""
    fig.canvas.draw()
    pts = []
    for ln in ax.lines:
        xy = ax.transData.transform(np.column_stack([ln.get_xdata(), ln.get_ydata()]).astype(float))
        if len(xy) == 1 or ln.get_linewidth() == 0:
            r = ln.get_markersize() * fig.dpi / 72 / 2 + 1
            for x, y in xy:
                g = np.linspace(-r, r, 5)
                pts += [(x + u, y + v) for u in g for v in g]
            continue
        for (x0, y0), (x1, y1) in zip(xy[:-1], xy[1:]):
            n = max(2, int(np.hypot(x1 - x0, y1 - y0) / step))
            pts += list(zip(np.linspace(x0, x1, n), np.linspace(y0, y1, n)))
    for an in ax.texts:
        if getattr(an, "arrow_patch", None) is not None and an.get_text() == "":
            (x0, y0), (x1, y1) = ax.transData.transform([an.xyann, an.xy])
            n = max(2, int(np.hypot(x1 - x0, y1 - y0) / step))
            pts += list(zip(np.linspace(x0, x1, n), np.linspace(y0, y1, n)))
    return np.array(pts) if pts else np.zeros((0, 2))


def place_line_labels(fig, ax, labels, obstacles):
    """Put each label at the closest spot that doesn't cover text or data. Far ones get a leader line."""
    pts = data_points(fig, ax)
    r = fig.canvas.get_renderer()
    boxes = [o.get_window_extent(r).expanded(1.03, 1.1) for o in obstacles]
    ax_box = ax.get_window_extent(r)
    angles = [0, 25, -25, 50, -50, 180, 155, -155, 75, -75, 105, -105, 130, -130, 90, -90]
    cands = [(d * np.cos(np.radians(t)), d * np.sin(np.radians(t)))
             for d in (6, 10, 15, 21, 28, 36, 46) for t in angles]

    def clear(bb):
        if not (ax_box.contains(bb.x0, bb.y0) and ax_box.contains(bb.x1, bb.y1)):
            return False
        if any(bb.overlaps(b) for b in boxes):
            return False
        if len(pts):
            inside = (pts[:, 0] > bb.x0) & (pts[:, 0] < bb.x1) & (pts[:, 1] > bb.y0) & (pts[:, 1] < bb.y1)
            if inside.any():
                return False
        return True

    for x, y, txt in sorted(labels, key=lambda l: -l[1]):
        placed = False
        for dx, dy in cands:
            ha = "left" if dx > 0.5 else "right" if dx < -0.5 else "center"
            va = "center" if abs(dy) < abs(dx) else ("bottom" if dy > 0 else "top")
            an = ax.annotate(txt, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=LABEL_FS,
                             color=INK, ha=ha, va=va, zorder=6)
            bb = an.get_window_extent(r).expanded(1.06, 1.15)
            if clear(bb):
                if np.hypot(dx, dy) > 9:
                    an.remove()
                    an = ax.annotate(txt, (x, y), xytext=(dx, dy), textcoords="offset points",
                                     fontsize=LABEL_FS, color=INK, ha=ha, va=va, zorder=6,
                                     arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.4, shrinkA=0.5,
                                                     shrinkB=3))
                boxes.append(bb)
                placed = True
                break
            an.remove()
        if not placed:
            ax.annotate(txt, (x, y), xytext=(6, 0), textcoords="offset points", fontsize=LABEL_FS,
                        color=INK, ha="left", va="center", zorder=6)
            print("  no clear spot for label:", txt)


def draw(objs, t, out, part="all", xlim=(-1, 58), ylim=(0.26, 115), title=None):
    apply_style()
    fig, ax = plt.subplots(figsize=(7.0, 5.6))
    ax.set_yscale("log")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    if part != "periods":
        ax.axhspan(*TASK_BAND, color=GRID, alpha=0.55, lw=0, zorder=0)
    obstacles, line_lab, arrows = [], [], []
    drop = DROP if part == "all" else 1.2

    for nid, o in objs.items():
        if o["group"] not in SHOW or o["eol"] is None:
            continue
        col, mk = GROUP_COLOR[o["group"]], marker_for(o["type"])
        ms = 5.6 * TYPE_SCALE[mk]
        tr = t[t["norad_id"] == nid]
        per = tr[tr["has_period"]]
        if len(per) and part != "limits":
            used, harm = per, per.iloc[0:0]
            # TOMS-EP: years after the hand-set year are harmonics, show them hollow
            if o.get("by_hand") and o.get("hand_year"):
                used = per[per["year"] <= o["hand_year"]]
                harm = per[per["year"] > o["hand_year"]]
            ax.scatter(used["decyear"] - o["eol"], used["deg_per_s"], s=3.5, color=col, alpha=0.18,
                       lw=0, zorder=2)
            yr = used.groupby("year").agg(x=("decyear", "median"), p=("period_s", "median")).reset_index()
            yr["y"] = 360 / yr["p"]
            xs, ys, yrs = (yr["x"] - o["eol"]).to_numpy(), yr["y"].to_numpy(), yr["year"].to_numpy()
            for i in range(len(xs) - 1):
                gap = yrs[i + 1] - yrs[i] > 1
                ax.plot(xs[i:i + 2], ys[i:i + 2], color=col, lw=0.7 if gap else 1.1,
                        ls=(0, (2.5, 2)) if gap else "-", zorder=3, solid_joinstyle="round",
                        solid_capstyle="round")
            ax.plot(xs, ys, lw=0, marker=mk, ms=ms, mfc=col, mew=0, zorder=3)
            if len(harm):
                ax.scatter(harm["decyear"] - o["eol"], harm["deg_per_s"], s=11, facecolor="none",
                           edgecolor=col, lw=0.6, alpha=0.7, zorder=2)
                hx, hy = (harm["decyear"] - o["eol"]).max(), harm["deg_per_s"].max()
                if xlim[0] <= hx <= xlim[1] and ylim[0] <= hy <= ylim[1]:
                    right = hx > xlim[0] + 0.6 * (xlim[1] - xlim[0])
                    obstacles.append(ax.annotate(f"{o['name']} 2024–25: harmonics, not used", (hx, hy),
                                                 xytext=(-6 if right else 5, 4), textcoords="offset points",
                                                 fontsize=6.2, color=MUTED, va="bottom",
                                                 ha="right" if right else "left"))
            vis = np.where((xs >= xlim[0]) & (xs <= xlim[1]))[0]
            if len(vis):
                i = vis[-1]
                line_lab.append((xs[i], ys[i], o["name"]))
        elif not len(per) and part != "periods" and o.get("med_len") and o.get("max_len"):
            x = tr["decyear"].max() - o["eol"]
            if xlim[0] <= x <= xlim[1]:
                arrows.append(dict(x=x, hi=360 / o["med_len"], lo=360 / o["max_len"], name=o["name"], col=col,
                                   mk=mk, ms=ms))

    for a in arrows:
        if part == "limits":
            ax.plot([a["x"], a["x"]], [a["lo"], a["hi"]], color=a["col"], lw=0.6, alpha=0.5, zorder=3)
            ax.plot(a["x"], a["hi"], lw=0, marker=a["mk"], ms=a["ms"] * 0.82, mfc="none", mec=a["col"], mew=0.9,
                    zorder=4)
        ax.annotate("", xy=(a["x"], a["lo"] / drop), xytext=(a["x"], a["lo"]), zorder=4,
                    arrowprops=dict(arrowstyle="-|>", color=a["col"], lw=1.1, mutation_scale=6.5,
                                    shrinkA=0, shrinkB=0))
        ax.plot(a["x"], a["lo"], lw=0, marker=a["mk"], ms=a["ms"], mfc=a["col"], mew=0, zorder=5)

    if part == "all":
        # names of the upper limits hang off one baseline, objects at the same x share a label
        groups = []
        for a in sorted(arrows, key=lambda a: a["x"]):
            if groups and abs(a["x"] - groups[-1]["x"]) < 0.25:
                g = groups[-1]
                g["names"].append(a["name"])
                g["lo"] = min(g["lo"], a["lo"])
            else:
                groups.append(dict(x=a["x"], lo=a["lo"], names=[a["name"]]))
        units_per_pt = (xlim[1] - xlim[0]) / (7.0 * 0.86 * 72)
        xl = spread([g["x"] for g in groups], (LABEL_FS + 1.8) * units_per_pt)
        trans = mtransforms.offset_copy(ax.transData, fig=fig, y=-3, units="points")
        for g, x_lab in zip(groups, xl):
            ax.plot([g["x"], g["x"], x_lab], [g["lo"] / drop * 0.95, BASELINE * 1.05, BASELINE], color=MUTED,
                    lw=0.4, ls=(0, (1, 1.4)), zorder=1)
            obstacles.append(ax.text(x_lab, BASELINE, ", ".join(g["names"]), transform=trans, rotation=90,
                                     fontsize=LABEL_FS, color=INK, ha="center", va="top", zorder=5))
    else:
        line_lab += [(a["x"], a["lo"], a["name"]) for a in arrows]

    ticks = [v for v in (1, 2, 5, 10, 20, 50, 100) if ylim[0] <= v <= ylim[1]]
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{v:g}" for v in ticks])
    ax.set_xlabel("Years since end of life")
    ax.set_ylabel(r"Rotation rate $\omega$ (°/s)")
    ax.grid(True, which="major", axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, fontsize=8.5, color=INK, loc="left", pad=4)

    shown = [o for o in objs.values() if o["group"] in SHOW]
    if part == "periods":
        shown = [o for o in shown if o.get("n_period")]
    elif part == "limits":
        shown = [o for o in shown if not o.get("n_period") and o.get("max_len")]
    present = {o["group"] for o in shown}
    handles, seen = [], []
    for g in SCOPE_ORDER + ["Rocket body"]:
        if g in present and SCOPE_LABEL[g] not in seen:
            seen.append(SCOPE_LABEL[g])
            handles.append(Line2D([], [], color=GROUP_COLOR[g], lw=0 if part == "limits" else 1.1,
                                  marker="o" if part == "limits" else None, ms=5.6, mew=0, label=SCOPE_LABEL[g]))
    for mk in sorted({marker_for(o["type"]) for o in shown}, key=lambda m: m != "o"):
        handles.append(Line2D([], [], color=MUTED, lw=0, marker=mk, ms=5.6 * TYPE_SCALE[mk], mew=0,
                              label=TYPE_LABEL[mk]))
    if part != "limits":
        handles += [Line2D([], [], color=MUTED, lw=0, marker="o", ms=2.2, alpha=0.5, label="Single MMT track"),
                    Line2D([], [], color=MUTED, lw=0.7, ls=(0, (2.5, 2)), label="Years with no period")]
    if part != "periods":
        handles += [(Line2D([], [], color=MUTED, lw=0, marker="o", ms=5.6, mew=0),
                     Line2D([], [], color=MUTED, lw=0, marker=r"$\downarrow$", ms=7))]
        if part == "limits":
            handles += [Line2D([], [], color=MUTED, lw=0, marker="o", ms=4.6, mfc="none", mew=0.9,
                               label=r"Looser limit from the median track, $360/\tilde{L}$")]
        handles += [Patch(facecolor=GRID, alpha=0.9, edgecolor="none", label="Task-sheet band, 2–5 °/s")]
    labels = [h.get_label() if not isinstance(h, tuple) else r"No period: upper limit $360/L_{\max}$"
              for h in handles]
    ax.legend(handles=handles, labels=labels, loc="upper center", bbox_to_anchor=(0.5, -0.1), fontsize=7.0,
              frameon=False, ncol=4 if part == "all" else 3, handlelength=1.8, columnspacing=1.4,
              handler_map={tuple: HandlerTuple(ndivide=None, pad=0.1)})
    place_line_labels(fig, ax, line_lab, obstacles)
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print(f"Saved {out}")


def main():
    p = argparse.ArgumentParser(description="Fig 2: rotation rate vs years since end of life")
    p.add_argument("workbook", type=Path)
    p.add_argument("tracks", type=Path, help="mmt_tracks.csv from the data pull")
    p.add_argument("--part", choices=("all", "periods", "limits"), default="all")
    p.add_argument("--out", type=Path)
    a = p.parse_args()

    objs = read_workbook(a.workbook)
    t = pd.read_csv(a.tracks, parse_dates=["date"])
    t = t[t["norad_id"].isin(objs)]
    t["decyear"] = t["date"].dt.year + (t["date"].dt.dayofyear - 0.5) / 365.25
    here = Path(__file__)
    if a.part == "periods":
        draw(objs, t, a.out or here.with_name("fig2_periods.png"), "periods", xlim=(-1, 45), ylim=(4.5, 125),
             title="Objects with a measured period")
    elif a.part == "limits":
        draw(objs, t, a.out or here.with_name("fig2_limits.png"), "limits", xlim=(-1, 58), ylim=(0.8, 14),
             title="Objects with no period: detection limits")
    else:
        draw(objs, t, a.out or here.with_name("fig2_rate.png"), "all")


if __name__ == "__main__":
    main()
