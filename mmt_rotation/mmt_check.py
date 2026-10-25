"""Pull MMT light-curve tracks from the Hugging Face snapshot and summarize them per object.

    py mmt_check.py 47858 7924 --out data/pull_2026-10-24

Writes mmt_summary.csv (one row per object), mmt_tracks.csv (one row per track) and
mmt_pull_info.txt to the --out folder. See README.md for the columns.
"""
import argparse
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATASET = "kyselica/MMT_snapshot"
API = "https://datasets-server.huggingface.co"
RSO_URL = f"https://huggingface.co/datasets/{DATASET}/resolve/main/rso.csv"
BASE_COLS = ["norad_id", "name", "period", "timestamp"]
TIME_COL = "time"   # sample times of each track

# column names that might hold a period quality or alias flag
FLAG_RE = re.compile(r"(alias|half|doubl|factor|flag|quality|confid|reliab|method|note|err|harmon|ambig)", re.I)


def get_json(url, params=None, tries=8, wait=10):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=120)
            if r.status_code == 200:
                return r.json()
            last = f"{r.status_code} {r.text[:200]}"
        except requests.RequestException as e:
            last = str(e)
        print(f"  retry {i + 1}/{tries} ({last})")
        time.sleep(wait)
    raise RuntimeError(f"gave up on {url}: {last}")


def snapshot_info():
    # commit id and last-modified date of the snapshot
    try:
        d = get_json(f"https://huggingface.co/api/datasets/{DATASET}", tries=3, wait=5)
        return d.get("sha", "unknown"), d.get("lastModified", "unknown")
    except Exception as e:
        print("could not read snapshot version:", e)
        return "unknown", "unknown"


def parquet_urls():
    data = get_json(f"{API}/parquet", {"dataset": DATASET})
    files = [f for f in data["parquet_files"] if f.get("split") == "train"]
    if not files:
        raise RuntimeError("no train parquet files listed")
    return [f["url"] for f in files]


def read_parquet(urls, ids):
    import fsspec
    import pyarrow as pa
    import pyarrow.parquet as pq

    parts, extra = [], []
    for u in urls:
        print("  reading", u.split("/")[-1])
        with fsspec.open(u, "rb") as f:
            schema = pq.ParquetFile(f).schema_arrow
            names = schema.names
            if not parts:
                print("  columns:", ", ".join(names))
            missing = [c for c in BASE_COLS + [TIME_COL] if c not in names]
            if missing:
                raise RuntimeError(f"missing columns: {missing}")
            extra = [n for n in names if n not in BASE_COLS and FLAG_RE.search(n)
                     and not pa.types.is_list(schema.field(n).type)
                     and not pa.types.is_large_list(schema.field(n).type)]
            cols = BASE_COLS + [TIME_COL] + extra
            f.seek(0)
            try:
                t = pq.read_table(f, columns=cols, filters=[("norad_id", "in", [int(i) for i in ids])])
            except Exception:
                # some files store norad_id as text
                f.seek(0)
                t = pq.read_table(f, columns=cols, filters=[("norad_id", "in", [str(int(i)) for i in ids])])
            parts.append(t.to_pandas())
    return pd.concat(parts, ignore_index=True), extra


def read_filter_api(ids):
    # backup route: page through the /filter endpoint, 100 rows at a time
    def one(norad):
        rows, off, total = [], 0, None
        while total is None or off < total:
            d = get_json(f"{API}/filter", {"dataset": DATASET, "config": "default", "split": "train",
                                           "where": f'"norad_id"={norad}', "offset": off, "length": 100})
            total = d["num_rows_total"]
            rows += [x["row"] for x in d["rows"]]
            off += 100
        return rows

    with ThreadPoolExecutor(max_workers=4) as ex:
        out = list(ex.map(one, ids))
    df = pd.DataFrame([r for rows in out for r in rows])
    extra = [c for c in df.columns if c not in BASE_COLS and FLAG_RE.search(c)
             and not df[c].map(lambda v: isinstance(v, (list, dict))).any()]
    print("  columns:", ", ".join(df.columns))
    keep = [c for c in BASE_COLS + [TIME_COL] + extra if c in df.columns]
    return df[keep], extra


def load_tracks(ids):
    try:
        print("Reading parquet files...")
        return read_parquet(parquet_urls(), ids)
    except Exception as e:
        print("parquet read failed:", e)
        print("Trying the /filter API instead...")
        return read_filter_api(ids)


def to_time(s):
    if pd.api.types.is_numeric_dtype(s):
        unit = "ms" if s.dropna().abs().median() > 1e11 else "s"
        return pd.to_datetime(s, unit=unit, errors="coerce")
    try:
        return pd.to_datetime(s, errors="coerce", format="mixed")
    except (TypeError, ValueError):   # older pandas
        return pd.to_datetime(s, errors="coerce")


def track_span(t):
    # track length (s) = last sample - first sample, and number of points
    if t is None or (not isinstance(t, str) and not hasattr(t, "__len__")):
        return np.nan, 0
    x = pd.Series(list(t))
    if len(x) == 0:
        return np.nan, 0
    if pd.api.types.is_numeric_dtype(x):
        v = x.to_numpy(dtype=float)
    else:
        v = pd.to_datetime(x, errors="coerce").astype("int64").to_numpy(dtype=float) / 1e9
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return np.nan, 0
    return float(v.max() - v.min()), int(len(v))


def summarize(df, ids):
    df = df.copy()
    df["norad_id"] = pd.to_numeric(df["norad_id"], errors="coerce").astype("Int64")
    df["period_s"] = pd.to_numeric(df["period"], errors="coerce")
    df["date"] = to_time(df["timestamp"])
    df["has_period"] = df["period_s"] > 0   # 0 or empty = no period found
    df["deg_per_s"] = np.where(df["has_period"], 360.0 / df["period_s"], np.nan)
    if TIME_COL in df.columns:
        spans = df[TIME_COL].map(track_span)
    else:
        spans = pd.Series([(np.nan, 0)] * len(df), index=df.index)
    df["track_length_s"] = [round(a, 2) if np.isfinite(a) else np.nan for a, _ in spans]
    df["n_points"] = [b for _, b in spans]
    df["year"] = df["date"].dt.year.astype("Int64")
    df = df.sort_values(["norad_id", "date"])

    rows = []
    for i in ids:
        g = df[df["norad_id"] == i]
        if g.empty:
            rows.append({"norad_id": i, "name": "NOT IN SNAPSHOT", "total_tracks": 0,
                         "tracks_with_period": "", "tracks_no_period": ""})
            continue
        w = g[g["has_period"]]
        r = {"norad_id": i, "name": g["name"].iloc[0], "total_tracks": len(g),
             "tracks_with_period": len(w), "tracks_no_period": len(g) - len(w),
             "pct_with_period": round(100 * len(w) / len(g), 1),
             "first_track": g["date"].min(), "last_track": g["date"].max(),
             "last_track_year": g["year"].max(),
             "median_track_length_s": round(g["track_length_s"].median(), 1),
             "min_track_length_s": g["track_length_s"].min(),
             "max_track_length_s": g["track_length_s"].max()}
        if len(w):
            # rate = median of all tracks with a period in the latest year that has one
            ly = w["year"].max()
            wy = w[w["year"] == ly]
            r.update({"latest_year": ly, "latest_year_n_tracks": len(wy),
                      "latest_year_n_tracks_total": int((g["year"] == ly).sum()),
                      "latest_year_median_period_s": round(wy["period_s"].median(), 3),
                      "latest_year_median_deg_per_s": round(wy["deg_per_s"].median(), 3)})
            last = w.iloc[-1]
            r.update({"latest_period_s": last["period_s"], "latest_period_date": last["date"],
                      "median_period_s": round(w["period_s"].median(), 3),
                      "min_period_s": w["period_s"].min(), "max_period_s": w["period_s"].max(),
                      "median_deg_per_s": round(w["deg_per_s"].median(), 3),
                      "min_deg_per_s": round(w["deg_per_s"].min(), 3),
                      "max_deg_per_s": round(w["deg_per_s"].max(), 3)})
        rows.append(r)
    return df, pd.DataFrame(rows)


def check_rso(ids):
    # print the object table entries (rso.csv) for these IDs
    try:
        rso = pd.read_csv(RSO_URL)
    except Exception as e:
        print("could not read rso.csv:", e)
        return
    print("\nrso.csv columns:", ", ".join(rso.columns))
    flagged = [c for c in rso.columns if FLAG_RE.search(c)]
    sub = rso[pd.to_numeric(rso["norad_id"], errors="coerce").isin(ids)]
    cols = [c for c in ["norad_id", "name", "country", "variability"] + flagged if c in rso.columns]
    print(sub[cols].to_string(index=False))


def main():
    p = argparse.ArgumentParser(description="Pull and summarize MMT tracks.")
    p.add_argument("ids", nargs="*", type=int, default=[47858], help="NORAD IDs")
    p.add_argument("--out", default=".", help="output folder")
    a = p.parse_args()
    ids, out = a.ids, Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    print("NORAD IDs:", ids)
    pulled = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rev, modified = snapshot_info()
    print(f"Pulled {pulled}, snapshot {rev}, last modified {modified}")

    df, extra = load_tracks(ids)
    df, summ = summarize(df, ids)
    for d in (df, summ):
        d["pulled_utc"] = pulled
        d["snapshot_revision"] = rev
        d["snapshot_last_modified"] = modified

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print("\n" + summ.to_string(index=False))

    summ.to_csv(out / "mmt_summary.csv", index=False)
    cols = (["norad_id", "name", "date", "year", "period_s", "deg_per_s", "has_period",
             "track_length_s", "n_points"] + extra
            + ["pulled_utc", "snapshot_revision", "snapshot_last_modified"])
    df[cols].to_csv(out / "mmt_tracks.csv", index=False)
    (out / "mmt_pull_info.txt").write_text(
        f"Dataset: https://huggingface.co/datasets/{DATASET}\n"
        f"Pulled: {pulled}\n"
        f"Snapshot revision (commit): {rev}\n"
        f"Snapshot last modified: {modified}\n"
        f"NORAD IDs: {' '.join(str(i) for i in ids)}\n"
        f"Python {sys.version.split()[0]}, pandas {pd.__version__}, numpy {np.__version__}\n")
    print(f"\nSaved mmt_summary.csv, mmt_tracks.csv, mmt_pull_info.txt in {out.resolve()}")

    # does the snapshot have any factor-of-2 / quality column?
    print("\nQuality / alias columns:")
    if extra:
        for c in extra:
            print(f"--- {c}")
            print(df[c].value_counts(dropna=False).head(10).to_string())
    else:
        print("none found, so factor-of-2 has to be judged from the folded plots")
    check_rso(ids)


if __name__ == "__main__":
    main()
