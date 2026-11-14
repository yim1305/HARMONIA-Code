from pathlib import Path

import matplotlib as mpl

# every figure is saved here; last week's versions are in plots/archive
PLOTS = Path(__file__).resolve().parent / "plots"


def plot_path(name):
    PLOTS.mkdir(exist_ok=True)
    return PLOTS / name


INK = "#1f1f1d"
MUTED = "#6b6a66"
GRID = "#e4e3df"

GROUP_COLOR = {
    "In scope": "#2a78d6",
    "Near scope": "#eb6834",
    "Orbit out": "#1baf7a",
    "Rocket body": "#1baf7a",
    "Reference (out of scope)": "#a3a29d",
}
# Jason 1/2 fail on orbit and CZ-4C on mass, so they share one color
SCOPE_LABEL = {
    "In scope": "Within mass and orbit limits",
    "Near scope": "Wet mass just over 1,000 kg",
    "Orbit out": "Outside mass or orbit limits",
    "Rocket body": "Outside mass or orbit limits",
    "Reference (out of scope)": "Reference object",
}
SCOPE_ORDER = ["In scope", "Near scope", "Orbit out", "Reference (out of scope)"]

TYPE_MARKER = {"Satellite": "o", "Payload": "o", "Rocket body": "^"}
TYPE_LABEL = {"o": "Satellite", "^": "Rocket body"}
TYPE_SCALE = {"o": 1.0, "^": 1.15}  # triangles look smaller at the same size


def marker_for(obj_type):
    return TYPE_MARKER.get(obj_type, "o")


# One set of font sizes (pt) for every figure. Every PNG is saved exactly FIG_WIDTH wide (see save), so a
# size here prints the same in every figure when they are placed at the same width in the memo or paper.
FIG_WIDTH = 7.0
FS = {
    "axis": 9.0,    # axis labels
    "tick": 7.5,    # tick labels
    "legend": 7.0,  # legend text
    "panel": 8.0,   # panel titles: (a), (b), object names in fig 3
    "name": 7.0,    # object names and block labels down the side of figs 1 and 5
    "note": 6.5,    # labels and notes inside the plot area
    "cell": 5.6,    # numbers inside the fig 5 cells
}
GRID_LW = 0.4


def apply_style():
    mpl.rcParams.update({
        "font.family": "STIXGeneral",
        "mathtext.fontset": "stix",
        "font.size": FS["tick"],
        "axes.labelsize": FS["axis"],
        "axes.titlesize": FS["panel"],
        "xtick.labelsize": FS["tick"],
        "ytick.labelsize": FS["tick"],
        "axes.edgecolor": MUTED,
        "axes.linewidth": 0.6,
        "axes.labelcolor": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK,
        "ytick.labelcolor": INK,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.minor.visible": False,
        "ytick.minor.visible": False,
        "legend.labelcolor": INK,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
        "figure.dpi": 150,
    })


# One legend style for every figure: above the plot, no frame, same font and spacing.
LEGEND_FS = FS["legend"]


def legend_top(target, handles, ncol, labels=None, y=1.02, **kw):
    """Legend centered just above an axes (or a whole figure, for the panel figures)."""
    opts = dict(loc="lower center", bbox_to_anchor=(0.5, y), ncol=ncol, fontsize=LEGEND_FS, frameon=False,
                handlelength=1.8, handletextpad=0.6, columnspacing=1.5, borderaxespad=0.0)
    opts.update(kw)
    if labels is not None:
        return target.legend(handles=handles, labels=labels, **opts)
    return target.legend(handles=handles, **opts)



def save(fig, out, width=FIG_WIDTH, dpi=300):
    """Save with a tight crop that comes out exactly `width` inches wide.

    The figure is widened or narrowed until its tight bounding box (legend and labels included) is `width`
    wide, so every PNG has the same width and the same font scale.
    """
    pad = mpl.rcParams["savefig.pad_inches"]
    for _ in range(6):
        fig.canvas.draw()
        w = fig.get_tightbbox(fig.canvas.get_renderer()).width + 2 * pad
        if abs(w - width) < 0.002:
            break
        W, H = fig.get_size_inches()
        fig.set_size_inches(W + (width - w), H)
    fig.savefig(out, dpi=dpi, bbox_inches="tight", pad_inches=pad)
