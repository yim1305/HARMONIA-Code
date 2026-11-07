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
# Jason 1/2 fail on orbit and CZ-4C on mass, so they share one colour
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


def apply_style():
    mpl.rcParams.update({
        "font.family": "STIXGeneral",
        "mathtext.fontset": "stix",
        "font.size": 8.5,
        "axes.labelsize": 9,
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
LEGEND_FS = 7.0


def legend_top(target, handles, ncol, labels=None, y=1.02, **kw):
    """Legend centred just above an axes (or a whole figure, for the panel figures)."""
    opts = dict(loc="lower center", bbox_to_anchor=(0.5, y), ncol=ncol, fontsize=LEGEND_FS, frameon=False,
                handlelength=1.8, handletextpad=0.6, columnspacing=1.5, borderaxespad=0.0)
    opts.update(kw)
    if labels is not None:
        return target.legend(handles=handles, labels=labels, **opts)
    return target.legend(handles=handles, **opts)

