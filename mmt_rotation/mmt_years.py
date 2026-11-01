import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description="Pull and plot MMT tracks for a range of years.")
    p.add_argument("ids", nargs="+", type=int, help="NORAD IDs")
    p.add_argument("--from", dest="y0", type=int, required=True, help="first year")
    p.add_argument("--to", dest="y1", type=int, required=True, help="last year (included)")
    p.add_argument("--max", type=int, default=10, help="tracks to plot per object per year")
    p.add_argument("--tag", help="name for the folder instead of the IDs")
    p.add_argument("--dry-run", action="store_true", help="print the commands only")
    a = p.parse_args()
    if a.y1 < a.y0:
        p.error("--to must be the same as or later than --from")

    years = [str(y) for y in range(a.y0, a.y1 + 1)]
    ids = [str(i) for i in a.ids]
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    tag = a.tag or "_".join(ids)
    out = HERE / "data" / f"pull_{today}_{tag}_{a.y0}-{a.y1}"

    steps = [
        [sys.executable, str(HERE / "mmt_check.py"), *ids, "--out", str(out)],
        [sys.executable, str(HERE / "mmt_plot.py"), *ids, "--years", *years,
         "--max", str(a.max), "--out", str(out / "plots")],
    ]
    for cmd in steps:
        print(">", " ".join(cmd))
        if not a.dry_run:
            subprocess.run(cmd, check=True)
    if a.dry_run:
        return

    with open(out / "mmt_pull_info.txt", "a", encoding="utf-8") as f:
        f.write(f"Plots: years {a.y0} to {a.y1}, up to {a.max} tracks per object per year "
                f"(mmt_years.py, separate from the main dataset pull)\n")
    print(f"\nDone. Everything is in {out}")


if __name__ == "__main__":
    main()
