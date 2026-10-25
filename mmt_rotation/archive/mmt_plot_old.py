"""
mmt_plot.py  -  draw the MMT light curves for a NORAD ID so you can count peaks per cycle.

Install once (Windows):   py -m pip install pandas pyarrow fsspec requests matplotlib
Run:                      py mmt_plot.py 47858            (latest 5 tracks that have a period)
                          py mmt_plot.py 47858 --max 20   (latest 20)
                          py mmt_plot.py 47858 7924       (several objects)

For each track it saves one PNG in the folder mmt_plots/ with four panels:
  1. the raw light curve (magnitude vs time)
  2. folded at half the published period (P/2)
  3. folded at the published period (P)
  4. folded at twice the published period (2P)
Dots are the measurements, the line is the median in 20 phase bins.
Magnitude axes are flipped (brighter is up).

How to read it (factor-of-2 check): look at the middle panel (folded at P).
  two unequal peaks per cycle -> the published period already covers the full rotation
  one clean peak per cycle    -> the true rotation could be twice as long; compare with the 2P panel
  a mess                      -> unclear

This is NOT MMT's own period plot. The snapshot only stores the measurements and the period number,
so the plot is redrawn here from those points.
"""
import re
import sys
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
    """Read only the rows for these NORAD IDs (with the time and mag lists) from the parquet files."""
    import fsspec
    import pyarrow.parquet as pq
    parts = []
    for u in urls:
        print("  reading", str(u).split("/")[-1])
        with fsspec.open(u, "rb") as f:
            pf = pq.ParquetFile(f)
            names = pf.schema_arrow.names
            if not parts:
                print("  columns in the snapshot:", ", ".join(names))
            missing = [c for c in COLS if c not in names]
            if missing:
                raise RuntimeError(f"expected columns missing: {missing}")
            f.seek(0)
            try:
                t = pq.read_table(f, columns=COLS, filters=[("norad_id", "in", [int(i) for i in ids])])
            except Exception:           # norad_id stored as text in this file
                f.seek(0)
                t = pq.read_table(f, columns=COLS, filters=[("norad_id", "in", [str(int(i)) for i in ids])])
            parts.append(t.to_pandas())
    return pd.concat(parts, ignore_index=True)


def to_seconds(t):
    """Turn the stored time list into seconds from the first point."""
    t = pd.Series(t)
    if pd.api.types.is_numeric_dtype(t):
        x = t.to_numpy(dtype=float)
    else:
        x = pd.to_datetime(t, errors="coerce").astype("int64").to_numpy(dtype=float) / 1e9
    return x - np.nanmin(x)


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
    note = ""
    if cycles < 1 or cycles > 1e5:
        note = "  (WARNING: time may not be in seconds)"
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
        a.invert_yaxis()
        a.grid(alpha=0.3)
    fig.suptitle(f"{row['name']} (NORAD {row['norad_id']})   track {row['timestamp']}   "
                 f"published period {period:.3f} s   {len(t)} points, {cycles:.1f} cycles{note}")
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return cycles, note


def main():
    args = sys.argv[1:]
    maxn = 5
    if "--max" in args:
        i = args.index("--max")
        maxn = int(args[i + 1])
        del args[i:i + 2]
    ids = [int(a) for a in args]
    if not ids:
        print("Give at least one NORAD ID, e.g.  py mmt_plot.py 47858")
        return
    df = read_tracks(parquet_urls(), ids)
    df["norad_id"] = pd.to_numeric(df["norad_id"], errors="coerce").astype("Int64")
    df["period"] = pd.to_numeric(df["period"], errors="coerce")
    df["_date"] = pd.to_datetime(df["timestamp"], errors="coerce")
    out = Path("mmt_plots")
    out.mkdir(exist_ok=True)
    for i in ids:
        g = df[(df["norad_id"] == i) & (df["period"] > 0)].sort_values("_date")
        total = int((df["norad_id"] == i).sum())
        print(f"\nNORAD {i}: {total} tracks, {len(g)} with a period; plotting the latest {min(maxn, len(g))}")
        for _, row in g.tail(maxn).iterrows():
            safe = re.sub(r"[^A-Za-z0-9]+", "_", str(row["name"])).strip("_")
            stamp = re.sub(r"[^0-9]", "", str(row["timestamp"]))[:14]
            path = out / f"{i}_{safe}_{stamp}.png"
            cycles, note = plot_track(row, path)
            print(f"  saved {path}  ({cycles:.1f} cycles){note}")


if __name__ == "__main__":
    main()
