import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from common import read_master

SHOW = ("In scope", "Near scope", "Orbit out", "Rocket body")
ORDER = ["Nimbus 2", "Nimbus 3 to 7", "Landsat 1", "Landsat 2 and 3", "TIROS-N/ATN", "DMSP Block 5D-2",
         "IRS-1", "PROTEUS", "FY-1", "Single designs"]
INPUTS = ["Spin axis", "CoM band", "Ring"]
OUT = Path(__file__).resolve().parent / "tables" / "table1_rp_width.csv"


def swings(r):
    # change in r_perp when one input goes over its full range and the others stay nominal
    d, dmin, dmax = r.d / 2, r.dmin / 2, r.dmax / 2
    spin = np.hypot(r.z, d) - d
    com = np.hypot(r.zmax, d) - np.hypot(r.zmin, d)
    ring = np.hypot(r.z, dmax) - np.hypot(r.z, dmin)
    return spin, com, ring


def row_name(r, singles):
    if r["Bus family"].startswith("Nimbus/Landsat"):
        if r["name"] in ("Nimbus 2", "Landsat 1"):
            return r["name"]
        return "Nimbus 3 to 7" if r["name"].startswith("Nimbus") else "Landsat 2 and 3"
    if r["Bus family"] in singles:
        return "Single designs"
    return r["Bus family"].replace(" bus", "")


def span(v, fmt="{:.2f}"):
    lo, hi = fmt.format(min(v) + 1e-9), fmt.format(max(v) + 1e-9)
    return lo if lo == hi else f"{lo}–{hi}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    rp = pd.read_excel(a.workbook, sheet_name="r_P")
    rp = rp[pd.to_numeric(rp["NORAD ID"], errors="coerce").notna()]
    rp = rp.rename(columns={"Bus height h (m)": "h", "Ring diameter (m)": "d", "Ring min (m), if assumed": "dmin",
                            "Ring max (m), if assumed": "dmax", "z min (m)": "zmin", "z max (m)": "zmax",
                            "z: CoM height above ring plane, nominal (m)": "z"})
    rp["NORAD ID"] = rp["NORAD ID"].astype(int)
    rp["assumed"] = rp.dmin.notna()
    rp["dmin"] = rp.dmin.fillna(rp.d)
    rp["dmax"] = rp.dmax.fillna(rp.d)

    M = read_master(a.workbook)
    T = M[M["Dataset group"].isin(SHOW)].merge(
        rp[["NORAD ID", "h", "d", "dmin", "dmax", "z", "zmin", "zmax", "assumed"]], on="NORAD ID")
    T[["spin", "com", "ring"]] = [swings(r) for r in T.itertuples()]
    T["main"] = [INPUTS[i] for i in T[["spin", "com", "ring"]].to_numpy().argmax(axis=1)]

    counts = T["Bus family"].value_counts()
    singles = set(counts[counts == 1].index)
    T["row"] = [row_name(r, singles) for _, r in T.iterrows()]

    rows = []
    for name in ORDER:
        g = T[T.row == name]
        n_a = int(g.assumed.sum())
        n_k = len(g) - n_a
        if n_a == 0:
            ring = "known"
        elif n_k == 0:
            ring = "assumed"
        else:
            ring = f"{n_k} known, {n_a} assumed" if n_k >= n_a else f"{n_a} assumed, {n_k} known"
        main = g.main.value_counts()
        main = main.index[0] if len(main) == 1 else ", ".join(f"{k} ({v})" for k, v in main.items())
        rows.append({"Bus family": name, "Objects": len(g), "Ring diameter": ring,
                     "r⊥ low (m)": span(g["r⊥ low (m)"]), "r⊥ high (m)": span(g["r⊥ high (m)"]),
                     "Spin axis case (m)": span(g.spin), "CoM height band (m)": span(g.com),
                     "Ring assumption (m)": span(g.ring), "Main input": main})
    out = pd.DataFrame(rows)
    a.out.parent.mkdir(exist_ok=True)
    out.to_csv(a.out, index=False, encoding="utf-8-sig")

    print(out.to_string(index=False))
    print("\nMain input over all", len(T), "objects:", T.main.value_counts().to_dict())
    print("Spin axis is the main input for:", ", ".join(T[T.main == "Spin axis"]["name"]))
    com_led = T[T.main == "CoM band"]
    print(f"Where the CoM band leads, it is {(com_led.com / com_led.spin).min():.2f} to {(com_led.com / com_led.spin).max():.2f} "
          f"times the spin axis case")

    print("\nCoM band with the default band instead (z min = 0.20h, z max = 0.65h):")
    for name in ("Nimbus 2", "Nimbus 3", "Landsat 1", "Landsat 2"):
        r = T[T.name == name].iloc[0]
        d = r.d / 2
        default = np.hypot(0.65 * r.h, d) - np.hypot(0.20 * r.h, d)
        print(f"  {name:10} now {r.com:.2f} m, default band {default:.2f} m")
    print(f"Saved {a.out}")


if __name__ == "__main__":
    main()
