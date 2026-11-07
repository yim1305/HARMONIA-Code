"""The one list of folds left out of the figures (mmt_rotation/left_out_folds.csv).

Every figure that uses MMT periods reads the list through here, so they all drop the same tracks. To leave
out another fold, add a row to the CSV (dates are inclusive) and rerun the figures. The reasons come from
the Factor-of-2 comments column on the Light curve tab.
"""
from pathlib import Path

import pandas as pd

DEFAULT = Path(__file__).resolve().parent.parent / "mmt_rotation" / "left_out_folds.csv"


def load(path=None):
    lo = pd.read_csv(path or DEFAULT, parse_dates=["from_date", "to_date"])
    lo["figure_note"] = lo["figure_note"].fillna("")
    # to_date covers the whole day
    lo["to_date"] = lo["to_date"] + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    return lo


def mark(tracks, path=None):
    """Add a 'left_out' column: True for tracks with a period that fall in a window on the list."""
    lo = load(path)
    out = pd.Series(False, index=tracks.index)
    for _, w in lo.iterrows():
        out |= (tracks["norad_id"] == w.norad_id) & tracks["date"].between(w.from_date, w.to_date)
    tracks = tracks.copy()
    tracks["left_out"] = out & tracks["has_period"].astype(bool)
    return tracks


def notes(path=None):
    """(norad_id, from_date, to_date, note) for windows that get a label on the figure."""
    lo = load(path)
    return [(r.norad_id, r.from_date, r.to_date, r.figure_note) for r in lo.itertuples() if r.figure_note]
