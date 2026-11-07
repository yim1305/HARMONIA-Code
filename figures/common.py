import openpyxl
import pandas as pd

NUMERIC = ["r_P full (m)", "r⊥ low (m)", "r⊥ high (m)", "Rotation rate, latest year (deg/s)",
           "Detection limit, longest track (deg/s)", "End-of-life year", "Dry mass (kg)"]


def headers(ws, row):
    return {ws.cell(row, c).value: c for c in range(1, ws.max_column + 1) if ws.cell(row, c).value}


def short(n):
    for a in (" (UO-36)", " (Arirang-1)", " (Kirari)"):
        n = n.replace(a, "")
    return n


def read_master(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    m = wb["Master"]
    H = headers(m, 11)
    rows = []
    for r in range(12, 72):
        if isinstance(m.cell(r, H["NORAD ID"]).value, int):
            rows.append({h: m.cell(r, c).value for h, c in H.items()})
    M = pd.DataFrame(rows)
    M["name"] = M["Name"].map(short)

    rp = wb["r_P"]
    RH = headers(rp, 1)
    rr = []
    for r in range(2, 62):
        if isinstance(rp.cell(r, RH["NORAD ID"]).value, int):
            rr.append({h: rp.cell(r, c).value for h, c in RH.items()})
    keep = ["NORAD ID", "r_P full (m)", "r⊥ low (m)", "r⊥ high (m)"]
    if "Likely spin state (from moments of inertia)" in RH:
        keep.append("Likely spin state (from moments of inertia)")
    R = pd.DataFrame(rr)[keep]
    M = M.merge(R, on="NORAD ID", how="left", suffixes=("_m", ""))
    for c in NUMERIC:
        M[c] = pd.to_numeric(M[c], errors="coerce")
    return M


def read_tracks(path):
    t = pd.read_csv(path, parse_dates=["date"])
    t["dec"] = t.date.dt.year + (t.date.dt.dayofyear - 0.5) / 365.25
    return t
