import argparse
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATASET = "kyselica/MMT_snapshot"
API = "https://datasets-server.huggingface.co"
COLS = ["norad_id", "name", "period", "timestamp", "time", "mag"]


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


def read_tracks(urls, ids):
    # only the rows for these IDs, with the time and mag lists
    import fsspec
    import pyarrow.parquet as pq

    parts = []
    for u in urls:
        print("  reading", str(u).split("/")[-1])
        with fsspec.open(u, "rb") as f:
            names = pq.ParquetFile(f).schema_arrow.names
            missing = [c for c in COLS if c not in names]
            if missing:
                raise RuntimeError(f"missing columns: {missing}")
            f.seek(0)
            try:
                t = pq.read_table(f, columns=COLS, filters=[("norad_id", "in", [int(i) for i in ids])])
            except Exception:
                # some files store norad_id as text
                f.seek(0)
                t = pq.read_table(f, columns=COLS, filters=[("norad_id", "in", [str(int(i)) for i in ids])])
            parts.append(t.to_pandas())
    return pd.concat(parts, ignore_index=True)


def to_seconds(t):
    # sample times -> seconds from the first point
    t = pd.Series(t)
    if pd.api.types.is_numeric_dtype(t):
        x = t.to_numpy(dtype=float)
    else:
        x = pd.to_datetime(t, errors="coerce").astype("int64").to_numpy(dtype=float) / 1e9
    return x - np.nanmin(x)


def to_date(s):
    try:
        return pd.to_datetime(s, errors="coerce", format="mixed")
    except (TypeError, ValueError):   # older pandas
        return pd.to_datetime(s, errors="coerce")


def binned_median(phase, mag, nbins=20):
    edges = np.linspace(0, 1, nbins + 1)
    idx = np.clip(np.digitize(phase, edges) - 1, 0, nbins - 1)
    xs, ys = [], []
    for b in range(nbins):
        m = mag[idx == b]
        if len(m) >= 2:
            xs.append((edges[b] + edges[b + 1]) / 2)
            ys.append(np.median(m))
    return np.array(xs), np.array(ys)


def plot_track(row, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    period = float(row["period"])
    t = to_seconds(row["time"])
    mag = np.asarray(row["mag"], dtype=float)
    ok = np.isfinite(t) & np.isfinite(mag)
    t, mag = t[ok], mag[ok]
    span = t.max() - t.min() if len(t) else 0
    cycles = span / period if period > 0 else 0
    note = "  (WARNING: time may not be in seconds)" if (cycles < 1 or cycles > 1e5) else ""

    fig, ax = plt.subplots(1, 4, figsize=(18, 4), constrained_layout=True)
    ax[0].plot(t, mag, ".", ms=3, color="#444444")
    ax[0].set_title("raw light curve")
    ax[0].set_xlabel("time (s)")
    ax[0].set_ylabel("magnitude (1000 km)")
    for a, (label, p) in zip(ax[1:], [("P/2", period / 2), ("P", period), ("2P", 2 * period)]):
        ph = (t % p) / p
        a.plot(ph, mag, ".", ms=3, color="#9aa5b1")
        bx, by = binned_median(ph, mag)
        if len(bx):
            a.plot(bx, by, "-", lw=2, color="#d55e00")
        a.set_title(f"folded at {label} = {p:.3f} s")
        a.set_xlabel("phase")
    for a in ax:
        a.invert_yaxis()   # brighter is up
        a.grid(alpha=0.3)
    fig.suptitle(f"{row['name']} (NORAD {row['norad_id']})   track {row['timestamp']}   "
                 f"published period {period:.3f} s   {len(t)} points, {cycles:.1f} cycles{note}")
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return cycles, note


def main():
    p = argparse.ArgumentParser(description="Plot MMT light curves folded at P/2, P and 2P.")
    p.add_argument("ids", nargs="+", type=int, help="NORAD IDs")
    p.add_argument("--summary", help="mmt_summary.csv to take the year from")
    p.add_argument("--out", default="mmt_plots", help="folder for the PNGs")
    p.add_argument("--max", type=int, default=5, help="tracks to plot per object (per year with --years)")
    p.add_argument("--years", nargs="+", type=int,
                   help="plot these years instead of the latest year (overrides --summary)")
    a = p.parse_args()
    out = Path(a.out)

    recorded = {}
    if a.summary:
        sm = pd.read_csv(a.summary)
        for _, r in sm.iterrows():
            if pd.notna(r.get("latest_year")):
                recorded[int(r["norad_id"])] = (int(r["latest_year"]), int(r["latest_year_n_tracks"]))

    df = read_tracks(parquet_urls(), a.ids)
    df["norad_id"] = pd.to_numeric(df["norad_id"], errors="coerce").astype("Int64")
    df["period"] = pd.to_numeric(df["period"], errors="coerce")
    df["_date"] = to_date(df["timestamp"])
    df["_year"] = df["_date"].dt.year
    out.mkdir(parents=True, exist_ok=True)

    for i in a.ids:
        g = df[(df["norad_id"] == i) & (df["period"] > 0)].sort_values("_date")
        total = int((df["norad_id"] == i).sum())
        if g.empty:
            print(f"\nNORAD {i}: {total} tracks, none with a period, nothing to plot")
            continue
        if a.years:
            plan = [(y, None) for y in a.years]
        elif a.summary:
            if i not in recorded:
                print(f"\nNORAD {i}: no latest_year in {a.summary}, skipped")
                continue
            plan = [recorded[i]]
        else:
            plan = [(int(g["_year"].max()), None)]
        for year, n_rec in plan:
            gy = g[g["_year"] == year]
            if n_rec is not None and len(gy) != n_rec:
                print(f"  WARNING: {len(gy)} tracks with a period in {year}, summary has {n_rec} "
                      f"(snapshot may have changed)")
            sel = gy.tail(a.max)
            print(f"\nNORAD {i}: {total} tracks, {len(gy)} with a period in {year}, plotting {len(sel)}")
            for _, row in sel.iterrows():
                safe = re.sub(r"[^A-Za-z0-9]+", "_", str(row["name"])).strip("_")
                stamp = re.sub(r"[^0-9]", "", str(row["timestamp"]))[:14]
                path = out / f"{i}_{safe}_{year}_{stamp}.png"
                cycles, note = plot_track(row, path)
                print(f"  saved {path} ({cycles:.1f} cycles){note}")

if __name__ == "__main__":
    main()
