"""Copy an MMT pull (mmt_summary.csv) into the Light curve tab of the HARMONIA workbook.

    py fill_lightcurve.py ..\\..\\HARMONIA_data_vN.xlsx data\\pull_2026-10-24\\mmt_summary.csv

Close the workbook in Excel first. Rows are matched by NORAD ID. Only the MMT columns listed in
FIELDS are written; periods, factor-of-2 calls, confidence and notes are left alone. An object that
is on the Master tab but not on the Light curve tab gets a new row with its formulas. A backup copy
of the workbook is saved before writing.
"""
import argparse
import shutil
from copy import copy
from datetime import datetime
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.formula.translate import Translator

SHEET = "Light curve"
FIRST, LAST = 2, 61            # rows covered by the Master lookups
MASTER_FIRST, MASTER_LAST = 12, 71
FORMULA_COLS = ("B", "H", "N", "P", "T")

# Light curve column -> mmt_summary.csv column
FIELDS = {
    "K": "tracks_with_period",
    "L": "tracks_no_period",
    "Q": "latest_year",
    "R": "latest_year_n_tracks",
    "S": "latest_year_median_period_s",
    "U": "last_track_year",
    "V": "median_track_length_s",
    "W": "max_track_length_s",
    "X": "pulled_utc",
    "Y": "snapshot_last_modified",
}


def clean(v):
    if pd.isna(v) or v == "":
        return None
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def add_row(lc, nid):
    # put a new object in the first empty row, copying style and formulas from the row above
    free = [r for r in range(FIRST, LAST + 1) if lc.cell(r, 3).value in (None, "")]
    if not free:
        return None
    r = free[0]
    tmpl = r - 1 if r > FIRST else FIRST
    for c in range(1, lc.max_column + 1):
        lc.cell(r, c)._style = copy(lc.cell(tmpl, c)._style)
    lc.cell(r, 1).value = r - 1
    lc.cell(r, 3).value = nid
    lc.cell(r, 7).value = "s (period)"
    lc.cell(r, 13).value = "Light curve"
    for col in FORMULA_COLS:
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

    rows = {int(lc.cell(r, 3).value): r for r in range(FIRST, LAST + 1)
            if lc.cell(r, 3).value not in (None, "")}
    on_master = {int(master.cell(r, 3).value) for r in range(MASTER_FIRST, MASTER_LAST + 1)
                 if isinstance(master.cell(r, 3).value, (int, float))}

    updated, added, skipped = [], [], []
    for _, s in sm.iterrows():
        nid = int(s["norad_id"])
        if s.get("name") == "NOT IN SNAPSHOT":
            skipped.append(f"{nid} (not in snapshot)")
            continue
        if nid not in rows:
            if nid not in on_master:
                skipped.append(f"{nid} (not on Master)")
                continue
            r = add_row(lc, nid)
            if r is None:
                skipped.append(f"{nid} (no free row)")
                continue
            rows[nid] = r
            added.append(nid)
        r = rows[nid]
        for col, key in FIELDS.items():
            if key in sm.columns:
                lc[f"{col}{r}"].value = clean(s[key])
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
    if skipped:
        print("Skipped:", "; ".join(skipped))


if __name__ == "__main__":
    main()
