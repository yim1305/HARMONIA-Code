import matplotlib as mpl

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
    "In scope": "In scope",
    "Near scope": "Near scope",
    "Orbit out": "Out of range (orbit or mass)",
    "Rocket body": "Out of range (orbit or mass)",
    "Reference (out of scope)": "Reference",
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
