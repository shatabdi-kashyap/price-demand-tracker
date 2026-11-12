"""Combine DoCA 'Daily All India Average (R & W)' snapshot files into one tidy table.

Each raw .xls is really an HTML page with several dates (the chosen date and one or more
spans earlier), for both Retail and Wholesale prices. Run from the project folder:
    python scripts/build_dataset.py
Output: data/clean/prices_long.csv  (one row per date x commodity x price type)
"""
from io import StringIO
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw/snapshots")
OUT_FILE = Path("data/clean/prices_long.csv")

# Wholesale prices are reported in Rs/quintal (100 kg); retail in Rs/kg (milk: Rs/litre).
QUINTAL_TO_KG = 100


def parse_snapshot(path: Path) -> pd.DataFrame:
    html = path.read_text(encoding="utf-8", errors="ignore")
    tables = pd.read_html(StringIO(html))
    # the data table is the one whose first cell is 'Commodities'
    table = next(t for t in tables if str(t.iloc[0, 0]).strip() == "Commodities")

    group = table.iloc[0]   # 'Daily Average Retail Price' / '... Wholesale Price'
    label = table.iloc[1]   # 'Price As On', '1 Month Ago', ... or '% Variation over'
    dates = table.iloc[2]   # the date for each price column
    body = table.iloc[3:].reset_index(drop=True)

    parts = []
    for col in range(1, table.shape[1]):
        lab = str(label[col]).strip()
        # price columns only: 'Price As On' or 'N Month(s)/Year(s)/Week(s)/Day(s) Ago'
        if not (lab == "Price As On" or lab.lower().endswith("ago")):
            continue
        price_type = "retail" if "Retail" in str(group[col]) else "wholesale"
        date = pd.to_datetime(str(dates[col]).strip(), format="%d/%m/%Y")
        parts.append(
            pd.DataFrame(
                {
                    "date": date,
                    "commodity": body[0].astype(str).str.strip(),
                    "price_type": price_type,
                    "price_raw": pd.to_numeric(body[col], errors="coerce"),  # '-' / NR -> NaN
                    "source_file": path.name,
                }
            )
        )
    return pd.concat(parts, ignore_index=True)


def main() -> None:
    files = sorted(RAW_DIR.glob("*.xls"))
    if not files:
        raise SystemExit(f"No .xls files found in {RAW_DIR}")

    df = pd.concat([parse_snapshot(f) for f in files], ignore_index=True)

    # the same date can appear in two files (overlap): keep one copy
    before = len(df)
    df = df.drop_duplicates(subset=["date", "commodity", "price_type"], keep="first")

    # standard unit: Rs per kg (milk: per litre)
    df["price_per_kg"] = df["price_raw"].where(df["price_type"] == "retail", df["price_raw"] / QUINTAL_TO_KG)
    df["commodity"] = df["commodity"].str.replace(" @", "", regex=False).str.replace("*", "", regex=False).str.strip()

    df = df.sort_values(["commodity", "price_type", "date"]).reset_index(drop=True)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False)

    print(f"Files read: {len(files)}")
    print(f"Rows: {before} -> {len(df)} after removing {before - len(df)} duplicates")
    print(f"Dates covered: {df['date'].min().date()} to {df['date'].max().date()} ({df['date'].nunique()} distinct dates)")
    print(f"Missing prices: {int(df['price_per_kg'].isna().sum())}")


if __name__ == "__main__":
    main()
