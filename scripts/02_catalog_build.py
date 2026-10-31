#!/usr/bin/env python3
"""Build docs/catalog.tsv (every file of every survey year) from the saved listing pages, and check the counts against the pages.

    uv run python scripts/02_catalog_build.py [YYYY-MM-DD]
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import estat

ROOT = Path(__file__).parents[1]
DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-10-31"
L = ROOT / "raw" / DATE / "listing"
COLS = ["survey_year_label", "tstat", "tclass1", "group", "title", "statInfId", "survey_ym", "published", "formats", "file_ids", "release_counts"]


def main() -> None:
    top = estat.parse_top((L / "top.html").read_text(encoding="utf-8"))
    rows, problems = [], []
    for y in top:
        t = y["tstat"]
        links = estat.parse_tclass_links((L / f"{t}.html").read_text(encoding="utf-8"))
        n = 0
        for k in links:
            items = estat.parse_datalist((L / f"{t}__{k['tclass1']}.html").read_text(encoding="utf-8"))
            if k["n"] is not None and len(items) != k["n"]:
                problems.append(f"{t} {k['tclass1']}: page says {k['n']}, parsed {len(items)}")
            for it in items:
                n += 1
                rows.append({"survey_year_label": y["title"], "tstat": t, "tclass1": k["tclass1"], "group": it["group"] or "",
                             "title": it["title"], "statInfId": it["statInfId"], "survey_ym": it["survey_ym"] or "",
                             "published": it["published"] or "", "formats": "+".join(f["format"] for f in it["formats"]),
                             "file_ids": "+".join(f["file_id"] for f in it["formats"]),
                             "release_counts": "+".join(str(f["release_count"]) for f in it["formats"])})
        if n != y["n_files"]:
            problems.append(f"{t} {y['title']}: top says {y['n_files']} files, parsed {n}")
    with (ROOT / "docs" / "catalog.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows;", len(top), "survey years")
    print("problems:", json.dumps(problems, ensure_ascii=False, indent=1) if problems else "none")


if __name__ == "__main__":
    main()
