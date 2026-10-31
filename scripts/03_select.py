#!/usr/bin/env python3
"""Select the EXCEL tables that can hold Chiba rows, by a rule on the table title, and write docs/catalog_selected.tsv.

Rule (every file of docs/catalog.tsv that is EXCEL):
  select    when the title has 都道府県別, 市区町村別 or 基本表 (a prefecture or municipality dimension, or the base tables),
  unless    the title has 過去NN年間 (time-series tables of the latest report that repeat other years' numbers;
            not selected: they are another reading of the same prefecture numbers, listed as 'timeseries').
Every other EXCEL table is 'national' (no prefecture dimension in the title), and PDF files are 'pdf'.

    uv run python scripts/03_select.py
"""

import csv
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def classify(title: str, formats: str) -> str:
    if "EXCEL" not in formats.split("+"):
        return "pdf"
    if re.search(r"過去\d+年間", title) or re.search(r"過去[０-９]+年間", title):
        return "timeseries"
    if re.search(r"都道府県別|市区町村別|基本表", title):
        return "selected"
    return "national"


def main() -> None:
    rows = list(csv.DictReader((ROOT / "docs" / "catalog.tsv").open(encoding="utf-8"), delimiter="\t"))
    for r in rows:
        r["selection"] = classify(r["title"], r["formats"])
    cols = list(rows[0].keys())
    with (ROOT / "docs" / "catalog_selected.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, cols, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(Counter(r["selection"] for r in rows))
    per_year = Counter(r["survey_year_label"][:6] for r in rows if r["selection"] == "selected")
    print(len([r for r in rows if r["selection"] == "selected"]), "selected")


if __name__ == "__main__":
    main()
