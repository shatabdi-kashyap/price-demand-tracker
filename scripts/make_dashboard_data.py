"""Builds data/clean/dashboard_data.csv for the Tableau dashboard.

One row per staple per month (Oct 2023 - Oct 2026), with retail and wholesale
prices side by side and the measures the dashboard needs.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT / "data" / "clean" / "prices_long.csv", parse_dates=["date"])

NAMES = {"Rice": "Rice", "Tur/Arhar Dal": "Tur dal", "Sugar": "Sugar",
         "Milk": "Milk", "Onion": "Onion"}
df = df[df["commodity"].isin(NAMES) & (df["date"] >= "2023-10-01")].copy()
df["staple"] = df["commodity"].map(NAMES)

wide = (df.pivot_table(index=["date", "staple"], columns="price_type",
                       values="price_per_kg")
          .rename(columns={"retail": "retail_price", "wholesale": "wholesale_price"})
          .reset_index()
          .sort_values(["staple", "date"]))

g = wide.groupby("staple")
wide["retail_mom_pct"] = g["retail_price"].pct_change() * 100
wide["wholesale_mom_pct"] = g["wholesale_price"].pct_change() * 100
wide["gap_rs"] = wide["retail_price"] - wide["wholesale_price"]
wide["gap_pct_of_wholesale"] = wide["gap_rs"] / wide["wholesale_price"] * 100
median = g["retail_price"].transform("median")
wide["retail_median_3yr"] = median
wide["retail_vs_median_pct"] = (wide["retail_price"] / median - 1) * 100
wide["year"] = wide["date"].dt.year
wide["month_num"] = wide["date"].dt.month
wide["month_name"] = wide["date"].dt.strftime("%b")
wide["unit"] = wide["staple"].map(lambda s: "Rs per litre" if s == "Milk" else "Rs per kg")

wide = wide.round(2)
out = ROOT / "data" / "clean" / "dashboard_data.csv"
wide.to_csv(out, index=False)
print(f"Saved {len(wide)} rows to {out}")
print("Months per staple:", wide.groupby("staple").size().to_dict())
print("Missing values:", int(wide.isna().sum().sum()), "(expected 10: first month has no change)")
