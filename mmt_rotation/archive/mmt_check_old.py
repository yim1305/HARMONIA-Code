"""
mmt_check.py  -  count MMT tracks (with and without a period) for NORAD IDs,
and check whether the MMT snapshot has any field about factor-of-2 / alias / quality.

Install once (Windows):   py -m pip install pandas pyarrow fsspec aiohttp requests
Run:                      py mmt_check.py 47858 7924 4362
                          py mmt_check.py            (uses the IDS list below)

Writes (in the same folder):
  mmt_summary.csv   one row per object: total tracks, tracks with a period, tracks with no period, ...
  mmt_tracks.csv    one row per track: date, period (s), deg/s. Paste the rows with a period into the Tracks tab.

How it works: it asks Hugging Face for the dataset's parquet files and reads ONLY the few columns it
needs straight from the file (no per-object paging), so it is much faster than the old script and does
not depend on the flaky /filter index. If that fails it falls back to the /filter API with retries,
several objects at a time.
"""
import re
import sys
import time
import numpy as np
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor

DATASET = "kyselica/MMT_snapshot"
IDS = [47858]                      # used when you run the script with no arguments
API = "https://datasets-server.huggingface.co"
RSO_URL = f"https://huggingface.co/datasets/{DATASET}/resolve/main/rso.csv"
BASE_COLS = ["norad_id", "name", "period", "timestamp"]
# any extra column whose name looks like it could describe period quality or aliasing
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


def parquet_urls():
    data = get_json(f"{API}/parquet", {"dataset": DATASET})
    files = [f for f in data["parquet_files"] if f.get("split") == "train"]
    if not files:
        raise RuntimeError("no train parquet files listed")
    return [f["url"] for f in files]


def read_parquet_files(urls, ids):
    import fsspec
    import pyarrow as pa
    import pyarrow.parquet as pq
    parts, extra_seen = [], []
    for u in urls:
        print("  reading", u.split("/")[-1])
        with fsspec.open(u, "rb") as f:
            pf = pq.ParquetFile(f)
            schema = pf.schema_arrow
            names = schema.names
            if not parts:
                print("  columns in the snapshot:", ", ".join(names))
            missing = [c for c in BASE_COLS if c not in names]
            if missing:
                raise RuntimeError(f"expected columns missing: {missing}")
            extra = [n for n in names if n not in BASE_COLS and FLAG_RE.search(n)
                     and not pa.types.is_list(schema.field(n).type)
                     and not pa.types.is_large_list(schema.field(n).type)]
            extra_seen = extra
            f.seek(0)
            try:
                t = pq.read_table(f, columns=BASE_COLS + extra, filters=[("norad_id", "in", [int(i) for i in ids])])
            except Exception:           # norad_id stored as text in this file
                f.seek(0)
                t = pq.read_table(f, columns=BASE_COLS + extra, filters=[("norad_id", "in", [str(int(i)) for i in ids])])
            parts.append(t.to_pandas())
    return pd.concat(parts, ignore_index=True), extra_seen


def filter_api(ids):
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
    print("  columns in the snapshot:", ", ".join(df.columns))
    keep = [c for c in BASE_COLS + extra if c in df.columns]
    return df[keep], extra


def load_tracks(ids):
    try:
        print("Reading parquet files ...")
        return read_parquet_files(parquet_urls(), ids)
    except Exception as e:
        print("Parquet route failed:", e)
        print("Falling back to the /filter API ...")
        return filter_api(ids)


def to_time(s):
    if pd.api.types.is_numeric_dtype(s):
        # epoch seconds or milliseconds
        unit = "ms" if s.dropna().abs().median() > 1e11 else "s"
        return pd.to_datetime(s, unit=unit, errors="coerce")
    return pd.to_datetime(s, errors="coerce")


def summarize(df, ids):
    df = df.copy()
    df["norad_id"] = pd.to_numeric(df["norad_id"], errors="coerce").astype("Int64")
    df["period_s"] = pd.to_numeric(df["period"], errors="coerce")
    df["date"] = to_time(df["timestamp"])
    df["has_period"] = df["period_s"] > 0            # period 0 / empty = none measured
    df["deg_per_s"] = np.where(df["has_period"], 360.0 / df["period_s"], np.nan)
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
             "first_track": g["date"].min(), "last_track": g["date"].max()}
        if len(w):
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
    try:
        rso = pd.read_csv(RSO_URL)
    except Exception as e:
        print("(could not read rso.csv:", e, ")")
        return
    print("\nrso.csv columns:", ", ".join(rso.columns))
    flagged = [c for c in rso.columns if FLAG_RE.search(c)]
    sub = rso[pd.to_numeric(rso["norad_id"], errors="coerce").isin(ids)]
    print(sub[[c for c in ["norad_id", "name", "country", "variability"] + flagged if c in rso.columns]].to_string(index=False))


def main():
    ids = [int(a) for a in sys.argv[1:]] or IDS
    print("NORAD IDs:", ids)
    df, extra = load_tracks(ids)
    df, summ = summarize(df, ids)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print("\n" + summ.to_string(index=False))
    summ.to_csv("mmt_summary.csv", index=False)
    cols = ["norad_id", "name", "date", "period_s", "deg_per_s", "has_period"] + extra
    df[cols].to_csv("mmt_tracks.csv", index=False)
    print("\nsaved mmt_summary.csv and mmt_tracks.csv")
    print("\nFactor-of-2 / alias / quality check")
    if extra:
        print("Columns that might describe it:", ", ".join(extra))
        for c in extra:
            print(f"--- {c}")
            print(df[c].value_counts(dropna=False).head(10).to_string())
    else:
        print("No column in the track table mentions alias, factor of 2, quality or method.")
        print("So this snapshot does not publish a factor-of-2 flag. Judge it from the folded light curve.")
    check_rso(ids)


if __name__ == "__main__":
    main()
