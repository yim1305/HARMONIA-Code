"""Copy an MMT pull (mmt_summary.csv) into the Light curve tab of the HARMONIA workbook.

    py fill_lightcurve.py ..\\..\\HARMONIA_data_vN.xlsx data\\pull_2026-10-24\\mmt_summary.csv

Close the workbook in Excel first. Rows are matched by NORAD ID. Only the MMT columns listed in
FIELDS are written; periods, factor-of-2 calls, confidence and notes are left alone. An object that
is on the Master tab but not on the Light curve tab gets a new row with its formulas. A backup copy
of the workbook is saved before writing.

Rows marked "Yes" in the "Latest-year values set by hand" column keep their latest-year columns
(latest year, tracks in that year, median period in that year): the script still updates their
track counts, track lengths and pull dates, but never overwrites those three. Use it when the
latest-year value was replaced by hand (for example TOMS-EP, where the 2024-2025 periods are
harmonics). Clear the mark to let the pull overwrite them again.

Columns are found by their header text in row 1 (Light curve) and row 11 (Master), not by letter,
so adding or moving columns in the workbook does not break this script. If a header is renamed,
the script stops and names the missing header.
"""
import argparse
import shutil
from copy import copy
from datetime import datetime
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.formula.translate import Translator
from openpyxl.utils import get_column_letter

SHEET = "Light curve"
FIRST, LAST = 2, 61            # rows covered by the Master lookups
MASTER_FIRST, MASTER_LAST = 12, 71
LC_HEADER_ROW, MASTER_HEADER_ROW = 1, 11

# Light curve header -> mmt_summary.csv column
FIELDS = {
    "Tracks with a period": "tracks_with_period",
    "Tracks with no period": "tracks_no_period",
    "Latest year with a period": "latest_year",
    "Tracks with a period in that year": "latest_year_n_tracks",
    "Median period in that year (s)": "latest_year_median_period_s",
    "Latest year with any track": "last_track_year",
    "Median track length (s)": "median_track_length_s",
    "Max track length (s)": "max_track_length_s",
    "Pulled (UTC)": "pulled_utc",
    "Snapshot last modified": "snapshot_last_modified",
}

# rows marked "Yes" here keep the HAND_FIELDS values
HAND_HEADER = "Latest-year values set by hand"
HAND_FIELDS = (
    "Latest year with a period",
    "Tracks with a period in that year",
    "Median period in that year (s)",
)

# Light curve columns whose formulas are copied into a new row
FORMULA_HEADERS = (
    "Name (from Master)",
    "Rotation rate, all years (deg/s)",
    "Measurement epoch (latest year with a period)",
    "Rotation category",
    "Rotation rate in that year (deg/s)",
    "Detection limit, median track (deg/s)",
    "Detection limit, longest track (deg/s)",
)


def header_columns(ws, row):
    # header text -> column number
    cols = {}
    for c in range(1, ws.max_column + 1):
        v = ws.cell(row, c).value
        if isinstance(v, str) and v.strip():
            cols[v.strip()] = c
    return cols


def need(cols, names, where):
    missing = [n for n in names if n not in cols]
    if missing:
        raise SystemExit(f"{where}: header not found: {'; '.join(missing)}. "
                         f"Rename it back or update fill_lightcurve.py.")


def clean(v):
    if pd.isna(v) or v == "":
        return None
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def add_row(lc, nid, cols):
    # put a new object in the first empty row, copying style and formulas from the row above
    id_col = cols["NORAD ID"]
    free = [r for r in range(FIRST, LAST + 1) if lc.cell(r, id_col).value in (None, "")]
    if not free:
        return None
    r = free[0]
    tmpl = r - 1 if r > FIRST else FIRST
    for c in range(1, lc.max_column + 1):
        lc.cell(r, c)._style = copy(lc.cell(tmpl, c)._style)
    lc.cell(r, cols["#"]).value = r - 1
    lc.cell(r, id_col).value = nid
    lc.cell(r, cols["Unit as published"]).value = "s (period)"
    lc.cell(r, cols["Measured by"]).value = "Light curve"
    for h in FORMULA_HEADERS:
        col = get_column_letter(cols[h])
        f = lc[f"{col}{tmpl}"].value
        if isinstance(f, str) and f.startswith("="):
            lc[f"{col}{r}"].value = Translator(f, f"{col}{tmpl}").translate_formula(f"{col}{r}")
    return r


def main():
    p = argparse.ArgumentParser(description="Copy an MMT summary into the Light curve tab.")
    p.add_argument("workbook", type=Path)
    p.add_argument("summary", type=Path)
    a = p.parse_args()

    sm = pd.read_csv(a.summary)
    wb = openpyxl.load_workbook(a.workbook)
    lc, master = wb[SHEET], wb["Master"]

    cols = header_columns(lc, LC_HEADER_ROW)
    need(cols, ["#", "NORAD ID", "Unit as published", "Measured by", HAND_HEADER, *FIELDS,
                *FORMULA_HEADERS],
         f"{SHEET} tab, row {LC_HEADER_ROW}")
    mcols = header_columns(master, MASTER_HEADER_ROW)
    need(mcols, ["NORAD ID"], f"Master tab, row {MASTER_HEADER_ROW}")
    id_col, m_id_col = cols["NORAD ID"], mcols["NORAD ID"]

    rows = {int(lc.cell(r, id_col).value): r for r in range(FIRST, LAST + 1)
            if lc.cell(r, id_col).value not in (None, "")}
    on_master = {int(master.cell(r, m_id_col).value) for r in range(MASTER_FIRST, MASTER_LAST + 1)
                 if isinstance(master.cell(r, m_id_col).value, (int, float))}

    updated, added, skipped, kept = [], [], [], []
    for _, s in sm.iterrows():
        nid = int(s["norad_id"])
        if s.get("name") == "NOT IN SNAPSHOT":
            skipped.append(f"{nid} (not in snapshot)")
            continue
        if nid not in rows:
            if nid not in on_master:
                skipped.append(f"{nid} (not on Master)")
                continue
            r = add_row(lc, nid, cols)
            if r is None:
                skipped.append(f"{nid} (no free row)")
                continue
            rows[nid] = r
            added.append(nid)
        r = rows[nid]
        by_hand = str(lc.cell(r, cols[HAND_HEADER]).value or "").strip().lower() == "yes"
        for header, key in FIELDS.items():
            if by_hand and header in HAND_FIELDS:
                continue
            if key in sm.columns:
                lc.cell(r, cols[header]).value = clean(s[key])
        if by_hand:
            kept.append(str(nid))
        updated.append(nid)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    backup = a.workbook.with_name(f"{a.workbook.stem}_before_fill_{stamp}{a.workbook.suffix}")
    shutil.copy2(a.workbook, backup)
    try:
        wb.save(a.workbook)
    except PermissionError:
        print(f"Could not save {a.workbook}, it is open in Excel. Close it and run again.")
        backup.unlink(missing_ok=True)
        return
    print(f"Backup: {backup.name}")
    print(f"Updated {len(updated)} objects")
    if added:
        print("New rows:", ", ".join(map(str, added)))
    if kept:
        print("Latest-year columns kept (set by hand):", ", ".join(kept))
    if skipped:
        print("Skipped:", "; ".join(skipped))


if __name__ == "__main__":
    main()
