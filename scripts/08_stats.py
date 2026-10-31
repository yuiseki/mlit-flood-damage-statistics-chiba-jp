#!/usr/bin/env python3
"""The numbers of the card, from the Parquet files and docs/06_verify.json: data/parquet/stats.json, docs/08_years.tsv,
docs/08_zero_chiba.tsv; and the year 2024 (令和6年: PDF only, no table) added to year_checks.parquet.

    uv run python scripts/08_stats.py
"""

import json
from collections import Counter
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).parents[1]
P = ROOT / "data" / "parquet"


def q(sql):
    return duckdb.sql(sql).fetchall()


def main() -> None:
    cat, tab, long = (f"read_parquet('{P}/{n}.parquet')" for n in ("catalog", "tables", "chiba_long"))
    ver = json.loads((ROOT / "docs" / "06_verify.json").read_text())
    years = q(f"""select c.survey_year, c.survey_year_label, count(*) files, sum((formats like '%EXCEL%')::int) excel, sum((formats like '%PDF%')::int) pdf,
                  sum((selection='selected')::int) selected, sum(fetched::int) fetched, sum((chiba_rows>0)::int) with_chiba, coalesce(sum(chiba_rows),0) chiba_rows
                  from {cat} c group by 1,2 order by 1""")
    ysheets = {r[0]: r[1:] for r in q(f"select survey_year, count(*), sum(chiba_rows), sum(records) from {tab} group by 1")}
    lines = ["survey_year\tsurvey_year_label\tfiles_listed\texcel\tpdf\tselected\tfetched\tfiles_with_chiba_rows\tchiba_rows\tsheets_read\trecords"]
    for y, lab, files, ex, pdf, sel, fet, wc, cr in years:
        sh = ysheets.get(y, (0, 0, 0))
        lines.append("\t".join(map(str, [y, lab, files, ex, pdf, sel, fet, wc, sh[1] or 0, sh[0], sh[2] or 0])))
    (ROOT / "docs" / "08_years.tsv").write_text("\n".join(lines) + "\n")
    zero = q(f"""select c.survey_year, c.title, c.statInfId, c.chiba_rows, t.reasons from {cat} c left join
                 (select table_id, string_agg(distinct coalesce(reader_note, 'prefecture rows present, none of Chiba'), '; ') reasons from {tab} group by 1) t
                 on c.statInfId=t.table_id where c.fetched and coalesce(c.chiba_rows,0)=0 order by 1,3""")
    (ROOT / "docs" / "08_zero_chiba.tsv").write_text("survey_year\ttitle\tstatInfId\treasons\n" + "\n".join("\t".join(map(str, [a, b, c, e])) for a, b, c, d, e in zero) + "\n")
    n_long = q(f"select count(*) from {long}")[0][0]
    stats = {
        "records": n_long, "chiba_rows": q(f"select sum(chiba_rows) from {tab}")[0][0], "sheets_read": q(f"select count(*) from {tab}")[0][0],
        "tables_fetched": q(f"select count(*) from {cat} where fetched")[0][0], "tables_with_chiba_rows": q(f"select count(*) from {cat} where chiba_rows>0")[0][0],
        "files_listed": q(f"select count(*) from {cat}")[0][0], "selection": dict(q(f"select selection, count(*) from {cat} group by 1")),
        "survey_years_listed": q(f"select count(distinct survey_year) from {cat}")[0][0],
        "years_with_records": q(f"select min(survey_year)||'-'||max(survey_year) from {long}")[0][0],
        "files_without_chiba_rows": len(zero), "levels": dict(q(f"select level, count(*) from {long} group by 1")),
        "values_null": q(f"select count(*) from {long} where value is null")[0][0],
        "symbols": dict(q(f"select symbol, count(*) from {long} where symbol is not null group by 1")),
        "blank_cells": q(f"select count(*) from {long} where note like 'blank%'")[0][0],
        "cells_checked": ver["cells_checked"], "cells_equal": ver["cells_equal"], "float_noise": ver.get("float_noise", 0),
        "additivity": {k: ver["additivity"][k] for k in ("checks", "equal", "within_1_unit", "mismatch", "tables_with_checks", "tables_with_mismatch")},
    }
    (P / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1) + "\n")
    # year 2024: listed, PDF only, nothing to read
    yc = pq.read_table(P / "year_checks.parquet")
    rows = [r for r in yc.to_pylist() if r["survey_year"] != 2024]
    rows.append({k: 0 for k in yc.schema.names} | {"survey_year": 2024})
    pq.write_table(pa.Table.from_pylist(sorted(rows, key=lambda r: r["survey_year"]), schema=yc.schema), P / "year_checks.parquet", compression="zstd")
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print(Counter(r[4] for r in zero).most_common(6))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
