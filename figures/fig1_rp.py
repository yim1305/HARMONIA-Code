import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import openpyxl
from matplotlib.lines import Line2D

from style import apply_style, GROUP_COLOR, SCOPE_LABEL, SCOPE_ORDER, TYPE_LABEL, TYPE_SCALE, marker_for, INK, MUTED, GRID, plot_path, legend_top

SHOW = ("In scope", "Near scope", "Orbit out", "Rocket body")
SINGLE = "Single designs"
FAMILY_ORDER = ["Nimbus/Landsat (sensory ring)", "TIROS-N/ATN", "DMSP Block 5D-2", "IRS-1 bus", "PROTEUS", "FY-1",
                SINGLE]
BAND = "#f3f2ef"


def headers(ws, row):
    return {ws.cell(row, c).value: c for c in range(1, ws.max_column + 1) if ws.cell(row, c).value}


def short(name):
    return name.replace(" (UO-36)", "").replace(" (Arirang-1)", "").replace(" (Kirari)", "")


def read(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    m, rp = wb["Master"], wb["r_P"]
    M, RP = headers(m, 11), headers(rp, 1)
    master = {}
    for r in range(12, 72):
        nid = m.cell(r, M["NORAD ID"]).value
        if isinstance(nid, int):
            master[nid] = dict(name=short(m.cell(r, M["Name"]).value), group=m.cell(r, M["Dataset group"]).value,
                               family=m.cell(r, M["Bus family"]).value, type=m.cell(r, M["Object type"]).value)
    rows, missing, uncalculated = [], [], 0
    for r in range(2, 62):
        nid = rp.cell(r, RP["NORAD ID"]).value
        if nid not in master or master[nid]["group"] not in SHOW:
            continue
        full, lo, hi = (rp.cell(r, RP[h]).value for h in ("r_P full (m)", "r⊥ low (m)", "r⊥ high (m)"))
        if rp.cell(r, RP["Bus height h (m)"]).value not in (None, "") and full is None:
            uncalculated += 1
        if not all(isinstance(v, (int, float)) for v in (full, lo, hi)):
            missing.append(master[nid]["name"])
            continue
        o = dict(master[nid], full=full, lo=lo, hi=hi,
                 spin=rp.cell(r, RP["Likely spin state (from moments of inertia)"]).value)
        same_family = sum(1 for v in master.values() if v["family"] == o["family"])
        o["block"] = o["family"] if same_family > 1 else SINGLE
        rows.append(o)
    if uncalculated and not rows:
        raise SystemExit("No calculated r_P values found. Open the workbook in Excel, save it, and run again.")
    return rows, missing


def main():
    p = argparse.ArgumentParser(description="Fig 1: r_P per object, grouped by bus family")
    p.add_argument("workbook", type=Path)
    p.add_argument("--out", type=Path, default=plot_path("fig1_rp.png"))
    a = p.parse_args()
    rows, missing = read(a.workbook)

    blocks = [b for b in FAMILY_ORDER if any(o["block"] == b for o in rows)]
    blocks += sorted({o["block"] for o in rows} - set(blocks))
    order = []
    for b in blocks:
        order += sorted([o for o in rows if o["block"] == b], key=lambda o: (o["full"], o["name"]))

    apply_style()
    n = len(order) + len(blocks)
    fig, ax = plt.subplots(figsize=(7.0, 0.165 * n + 1.35))
    y, ticks, names, spans = 0, [], [], []
    for b in blocks:
        head = y
        y += 1
        for o in [o for o in order if o["block"] == b]:
            col, mk = GROUP_COLOR[o["group"]], marker_for(o["type"])
            sc = TYPE_SCALE[mk]
            ax.plot([o["lo"], o["hi"]], [y, y], color=col, lw=1.4, solid_capstyle="round", zorder=2)
            for xv in (o["lo"], o["hi"]):
                ax.plot(xv, y, marker=mk, ms=4.6 * sc, mfc="white", mec=col, mew=1.1, zorder=3)
            ax.plot(o["full"], y, marker=mk, ms=5.6 * sc, mfc=col, mew=0, zorder=4)
            # ring = likely spin state from the moments of inertia
            if o["spin"] and "high" in str(o["spin"]):
                ax.plot(o["hi"], y, marker="o", ms=9.5, mfc="none", mec=col, mew=0.8, zorder=3)
            ticks.append(y)
            names.append(o["name"])
            y += 1
        spans.append((b, head, y - 1))
    for i, (b, h, e) in enumerate(spans):
        if i % 2 == 0:
            ax.axhspan(h - 0.5, e + 0.5, color=BAND, lw=0, zorder=0)
        count = f"{e - h} designs" if b == SINGLE else f"{e - h} objects"
        ax.text(0.006, h, f"{b}  ·  {count}", transform=ax.get_yaxis_transform(), ha="left", va="center",
                fontsize=7.4, color=INK, style="italic", zorder=5)

    ax.set_yticks(ticks)
    ax.set_yticklabels(names, fontsize=7.2)
    ax.tick_params(axis="y", length=0, pad=4)
    ax.set_ylim(y - 0.5, -0.6)
    ax.set_xlim(0, max(o["hi"] for o in order) * 1.06)
    ax.set_xlabel(r"Grab-point distance, $r_\perp$ and $r_P$ (m)")
    ax.grid(True, axis="x", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)

    k = dict(lw=0, mew=1.1)
    handles = [
        Line2D([], [], marker="o", ms=4.6, mfc="white", mec=MUTED, label=r"Left end: $r_{\perp,\mathrm{low}}$ from the spin axis (spin about the long axis)", **k),
        Line2D([], [], marker="o", ms=5.6, mfc=MUTED, mew=0, lw=0, label=r"Filled: $r_{P}$ from the center of mass (nominal $z$)"),
        Line2D([], [], marker="o", ms=4.6, mfc="white", mec=MUTED, label=r"Right end: $r_{\perp,\mathrm{high}}$ from the spin axis (highest $z$, largest ring)", **k),
        Line2D([], [], marker="o", ms=9.5, mfc="none", mec=MUTED, mew=0.8, lw=0, label="Circle: likely spin state from moments of inertia"),
    ]
    blank = Line2D([], [], lw=0, alpha=0, label=" ")
    present = {o["group"] for o in order}
    seen = []
    for g in SCOPE_ORDER + ["Rocket body"]:
        if (g in present or (g == "Orbit out" and "Rocket body" in present)) and SCOPE_LABEL[g] not in seen:
            seen.append(SCOPE_LABEL[g])
            handles.append(Line2D([], [], color=GROUP_COLOR[g], lw=1.6, label=SCOPE_LABEL[g]))
    # pad so each legend column holds one kind of thing
    handles += [blank] * (8 - len(handles))
    for mk in sorted({marker_for(o["type"]) for o in order}, key=lambda m: m != "o"):
        handles.append(Line2D([], [], marker=mk, ms=5.6 * TYPE_SCALE[mk], mfc=MUTED, mew=0, lw=0, label=TYPE_LABEL[mk]))
    handles += [blank] * (12 - len(handles))
    legend_top(ax, handles, 3, y=1.01)
    fig.savefig(a.out, dpi=300)
    print(f"Saved {a.out}: {len(order)} objects in {len(blocks)} blocks")
    if missing:
        print("No r_P yet (left out):", ", ".join(missing))


if __name__ == "__main__":
    main()
