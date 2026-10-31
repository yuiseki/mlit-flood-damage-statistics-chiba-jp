#!/usr/bin/env python3
"""Write data/README.md (the card), data/LICENSE and data/provenance.yaml. Every number comes from the Parquet files,
data/parquet/stats.json and docs/06_verify.json; nothing is typed in by hand except the quotations.

    uv run python scripts/11_card.py
"""

import hashlib
import html
import json
import re
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).parents[1]
P = ROOT / "data" / "parquet"
REPO = "yuiseki/mlit-flood-damage-statistics-chiba-jp"
DATE = "2026-10-31"


def q(sql):
    return duckdb.sql(sql).fetchall()


def terms_text() -> str:
    h = (ROOT / "evidence" / "terms-of-use.html").read_text(encoding="utf-8")
    m = re.search(r"<main.*?</main>", h, re.S) or re.search(r"<body.*?</body>", h, re.S)
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", m.group(0), flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    return re.sub(r"\n\s*\n+", "\n", t).strip() + "\n"


def listing_notes() -> list[str]:
    seen = {}
    for f in sorted((ROOT / "raw" / DATE / "listing").glob("*.html")):
        t = html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"<script.*?</script>|<style.*?</style>", "", f.read_text(encoding="utf-8"), flags=re.S)))
        for line in t.split("\n"):
            line = line.strip()
            if line.startswith("※") and "修正しました" in line:
                seen[line] = seen.get(line, 0) + 1
    return list(seen)


def main() -> None:
    st = json.loads((P / "stats.json").read_text())
    ver = json.loads((ROOT / "docs" / "06_verify.json").read_text())
    long, tab, cat, yc = (f"read_parquet('{P}/{n}.parquet')" for n in ("chiba_long", "tables", "catalog", "year_checks"))
    terms = terms_text()
    (ROOT / "evidence" / "terms-of-use.txt").write_text(terms, encoding="utf-8")
    notes = listing_notes()
    meta = json.loads((ROOT / "evidence" / "terms-of-use.meta.json").read_text())
    years = [l.split("\t") for l in (ROOT / "docs" / "08_years.tsv").read_text().splitlines()[1:]]
    ytab = "\n".join(f"| {y[0]} | {y[1]} | {y[2]} | {y[3]} | {y[4]} | {y[6]} | {y[7]} | {int(y[8]):,} | {int(y[10]):,} |" for y in years)
    fam = q(f"select table_family, min(survey_year), max(survey_year), count(distinct table_id), sum(chiba_rows) from {tab} group by 1 order by 4 desc, 1")
    ftab = "\n".join(f"| {a} | {b}-{c} | {d} | {int(e):,} |" for a, b, c, d, e in fam)
    units = q(f"select coalesce(unit,'(none)'), count(*) from {long} group by 1 order by 2 desc limit 12")
    utab = ", ".join(f"`{u}` {n:,}" for u, n in units)
    n_unit_null = q(f"select count(*) from {long} where unit is null")[0][0]
    n_code = q(f"select count(*) from {long} where area_code is not null")[0][0]
    n_tree = q(f"select coalesce(sum(chiba_rows),0) from {tab} where tree_form")[0][0]
    ty = q(f"select min(survey_year), max(survey_year) from {tab} where tree_form")[0]
    tree_years = f"survey years {ty[0]} to {ty[1]}"
    n_ditto = q(f"select coalesce(sum(ditto_rows),0) from {tab}")[0][0]
    n_inh = q(f"select coalesce(sum(inherited_rows),0) from {tab}")[0][0]
    orph = q(f"select survey_year, source_sheet, table_title, orphan_rows from {tab} where orphan_rows>0 order by 1")
    orph_txt = "; ".join(f"{a} {c} {b}: {d}" for a, b, c, d in orph) or "none"
    n_orphan = q(f"select coalesce(sum(orphan_rows),0) from {tab}")[0][0]
    labels = q(f"select pref_label, count(*) from {long} group by 1 order by 2 desc")
    ltab = ", ".join(f"`{a}` {n:,}" for a, n in labels)
    zero = (ROOT / "docs" / "08_zero_chiba.tsv").read_text().splitlines()[1:]
    r6 = q(f"select title, published from {cat} where survey_year=2024")
    add = st["additivity"]
    nonbase = q(f"select sum(checks)::bigint from (select 0 as checks) ")  # placeholder replaced below
    by_table = ver["additivity"]["by_table"]
    fam_of = dict(q(f"select table_id||'/'||source_sheet, table_family from {tab}"))
    base_chk = sum(v["checks"] for k, v in by_table.items() if "基本表" in fam_of[k])
    base_bad = sum(v["mismatches"] for k, v in by_table.items() if "基本表" in fam_of[k])
    other_chk = add["checks"] - base_chk
    other_bad = add["mismatch"] - base_bad
    del nonbase
    first_pub = q(f"select min(published), max(published) from {cat} where fetched")[0]
    card = f"""---
license: other
license_name: e-stat-terms-of-use
license_link: https://www.e-stat.go.jp/terms-of-use
language:
- ja
tags:
- japan
- flood
- statistics
- chiba
- mlit
- e-stat
size_categories:
- 100K<n<1M
pretty_name: Chiba rows of the MLIT 水害統計調査 (flood damage statistics) from e-Stat, survey years 1993 to 2023
configs:
- config_name: chiba_long
  data_files: parquet/chiba_long.parquet
- config_name: tables
  data_files: parquet/tables.parquet
- config_name: catalog
  data_files: parquet/catalog.parquet
- config_name: year_checks
  data_files: parquet/year_checks.parquet
---

# mlit-flood-damage-statistics-chiba-jp

The Chiba rows (the prefecture total and the municipalities) of the statistical tables of the **水害統計調査** (Flood Damage Statistics Survey) of the
Ministry of Land, Infrastructure, Transport and Tourism (MLIT), as published as Excel files on e-Stat (政府統計の総合窓口,
toukei 00600590). One record is one cell of a Chiba row, read **as it is in the table**: no unit conversion, no correction, no
merger of municipalities. It covers the survey years 1993 (平成5年) to 2023 (令和5年).

**Scope, stated first.** The survey is published one to two years after the flood year. At the time of fetching ({DATE}) the
e-Stat list had {st['survey_years_listed']} survey years, 平成5年 (1993) to 令和6年 (2024).
**令和6年 (2024) has one file only, the PDF overview "{r6[0][0]}" (published on the list on 2026-01-07), and no statistical table (Excel): its Chiba rows
are not in this dataset, because the tables are not yet published.** No survey year after 令和6年 (2025 onwards) is listed. Floods of 2025 and 2026 are therefore **not**
in this dataset; in particular the 令和8年8月 Chiba heavy rain and typhoon No. 25 of 2026 are not included. The last survey year with tables here
is 令和5年 (2023; list published 2026-01-14, tables 2025-07-31 and 2025-10-03).

## Source

- List of files: <https://www.e-stat.go.jp/stat-search/files?toukei=00600590> (each survey year: `tstat`; each file: `statInfId`).
- A file: `https://www.e-stat.go.jp/stat-search/file-download?statInfId=<ID>&fileKind=0` (the plain download link of the site; no API, no login).
- Fetched on {DATE}, one request at a time with a 2 s pause. {st['tables_fetched']} Excel files, no HTTP error, no block. The responses carry no `Last-Modified` header
  (null in `catalog`); the publication date of each file is the 公開（更新）日 of the list (`published`, {first_pub[0]} to {first_pub[1]}).
- The Excel files were kept unchanged locally as `raw/{DATE}/xls/` (the extension is that of the real format, `.xlsx` or `.xls`); **they are not part of this dataset** (fetch them again from e-Stat with `scripts/04_fetch_xls.py` and compare with `raw/{DATE}/MANIFEST.json`: sha256, fetch time, headers, URL),
  and the saved list pages in `raw/{DATE}/listing/`.

## Which tables are in

The list has {st['files_listed']:,} files of {st['survey_years_listed']} survey years: {st['selection'].get('selected', 0)} Excel tables were selected by a rule on the title (`docs/catalog_selected.tsv`, `scripts/03_select.py`):
the title has 都道府県別, 市区町村別 or 基本表 (a prefecture or municipality dimension, or the base tables), and not 過去NN年間. The others were not fetched:
{st['selection'].get('national', 0)} Excel tables without a prefecture dimension (national tables), {st['selection'].get('timeseries', 0)} time-series tables of the latest report (過去10年間 / 過去20年間 ... they repeat numbers of other years),
{st['selection'].get('pdf', 0)} PDF files (figures and overviews). All {st['tables_fetched']} fetched files were read; {st['tables_with_chiba_rows']} of them hold Chiba rows, {st['files_without_chiba_rows']} do not (reasons below).

Table families (the title without the table number; the numbering moves between years, e.g. 表-3 市区町村別水害被害 is 表-3 in most years but the tables before 平成12年 do not exist):

| Table family | Survey years | Files | Chiba rows |
|---|---|---|---|
{ftab}

## Files

| File | Rows | What a row is |
|---|---|---|
| `parquet/chiba_long.parquet` | {st['records']:,} | One cell of a Chiba row of a table ({st['chiba_rows']:,} Chiba rows of {st['sheets_read']} sheets) |
| `parquet/tables.parquet` | {st['sheets_read']} | One sheet read: what was found, key and data columns, the number of Chiba rows |
| `parquet/catalog.parquet` | {st['files_listed']:,} | One file of the e-Stat list (all years, all formats) with the selection and, if fetched, its sha256 |
| `parquet/year_checks.parquet` | {len(years)} | One survey year: tables, rows, cells checked, additivity checks |
| `raw/` | MANIFEST.json + list pages | The sha256, fetch time and URL of the {st['tables_fetched']} Excel files (not included), and the saved list pages |

`chiba_long` columns: `survey_year` (the western year; 平成5年 = 1993), `survey_year_label`, `table_id` (the `statInfId`), `table_no` (表-N from the title, null for the base tables),
`table_title` (the title on the list), `table_family`, `sheet_title` (the title cell of the sheet, whitespace removed; for 表-11 it holds the name of the event),
`pref_label` (the prefecture cell as in the table, whitespace removed: {ltab}), `area_code` (null in all rows: no table carries a municipality code), `area_name` (the municipality, or the
prefecture label for a prefecture-level row, as in the table, e.g. 千葉市中央区, 合計), `level` (`municipality`, or `prefecture` = a row of a prefecture table or a 合計/total row),
`row_class` (JSON: the other row labels of the table, e.g. 水系名, 異常気象名, 河川・海岸名等, 水害原因; see "Hierarchical base tables"), `measure` (the header path of the column from the top
to the bottom of the header, joined by " / ", whitespace removed), `value` (double; null for a blank or a symbol), `unit` (from the header, e.g. （㎡）, or from the table's 単位 note; null in {n_unit_null:,} records where the table gives none),
`symbol` (the text of a non-numeric cell), `note` (`blank`, `prefecture name inherited from the row above`, `ditto mark (〃) resolved ...`), `source_statInfId`, `source_file`, `source_sheet`,
`source_cell` (e.g. `B19`), `source_row`, `source_col`, `header_cells` (the cells the measure comes from).
Units found: {utab}.

## How it was read

`scripts/extract.py` (openpyxl for .xlsx, xlrd for .xls). The header of a column is collected from the first row to the last header row, through merged cells and
"center across selection" cells; a header text wrapped over several rows stays in separate segments (e.g. `公共土 / 木施設`). All whitespace
(padding, ideographic spaces, newlines) is removed from texts. Numbers are not converted: a blank cell is a null (older tables show zero as a blank: {st['blank_cells']:,} records are blank),
a symbol is kept in `symbol`. {n_inh:,} Chiba rows had no prefecture name of their own and inherit it from the row above; {n_ditto:,} rows hold the ditto mark 〃 in a label column
(resolved from the row above, flagged in `note`). Header rows repeated in the middle of a sheet (page breaks) are skipped. The sheets of a workbook are read in order, so that
a sheet that goes on with the rows of the sheet before it belongs to the right prefecture (in 平成11, 12 and 13 the tabs 公共土木N are not in the order of N and are read by N).
The footnotes of the tables: none of the fetched Excel tables carries a note row.

### Hierarchical base tables

The 基本表 of the early years ({tree_years}) use a hierarchical layout: in the first label column the prefecture, the event (異常気象名), its dates (水害発生年月) and the river system (水系・沿岸名) follow
one another in turn, and the following rows write 〃 for "same as above". The records of those sheets ({n_tree:,} Chiba rows) carry the resolved labels in `row_class`
(`異常気象名`, `（水害発生年月）`, `水系・沿岸名`, ...); a row of the prefecture or the event has null for the labels it does not have. The base tables of later years carry the labels in separate columns and write the totals as 合計.

## Verification

By a route that shares no code with the extraction (`scripts/06_verify.py`; the .xls files were converted by LibreOffice and read with a zipfile + XML reader):

- **Cells:** every one of the {ver['cells_checked']:,} records was read again from its `source_cell`: {ver['cells_equal']:,} equal; {ver.get('float_noise', 0)} of them differ by floating-point noise
  only (formula cells recomputed by the other reader, relative difference below 1e-9; the value in the table is the cached value read by the extraction); 0 differ otherwise.
- **Completeness:** every non-empty cell in a data column of an extracted row is in the table (0 missing); a scan of the first four columns of every sheet for 千葉 / 千葉県 found no row that was not extracted (0 missed);
  the rows of the hierarchical form carry no prefecture name and cannot be found by that scan ({ver.get('tree_rows_not_scannable', 0):,} rows).
- **Totals inside a table** (municipalities or other breakdowns against the 合計 row of the same table, {add['checks']:,} comparisons in {add['tables_with_checks']} sheets): {add['equal']:,} equal,
  {add['within_1_unit']} differ by at most one unit (rounding), **{add['mismatch']} differ in {add['tables_with_mismatch']} sheets**. In the municipal and prefecture tables ({other_chk:,} comparisons) the mismatches are {other_bad}.
  All the others are in the 基本表 ({base_chk:,} comparisons, {base_bad} mismatches), where the 合計 rows sit at several levels of a hierarchy and the check is not a proof either way; the differences are listed in `docs/06_verify.json` and nothing was corrected.
- **Rows before any prefecture name:** {n_orphan} rows with numbers precede the first prefecture name of a sheet ({orph_txt}; see `tables.orphan_rows`). They are not assigned to Chiba and are not included.
- {len(zero)} fetched files have no Chiba row (`docs/08_zero_chiba.tsv`): {sum(1 for z in zero if 'no prefecture name' in z)} are workbooks or sheets that hold national totals or empty templates (`水害統計基本表の合計`, `原本` sheets), the others are base-table workbooks of which some sheets hold other prefectures only.

Per survey year ({len(years)} years listed; `year_checks.parquet` has the checks):

| Survey year | Label | Files listed | Excel | PDF | Excel fetched | Files with Chiba rows | Chiba rows | Records |
|---|---|---|---|---|---|---|---|---|
{ytab}

## Licence

The data is a processed copy of public statistics of the Japanese government. The terms of e-Stat (<https://www.e-stat.go.jp/terms-of-use>, saved in `evidence/terms-of-use.html` and `evidence/terms-of-use.txt`, fetched {meta['fetched_at'][:10]}, sha256 {meta['sha256'][:16]}...) say:

> 当サイトで公開している情報（以下「コンテンツ」といいます。）は、どなたでも以下の１）～６）に従って、複製、公衆送信、翻訳・変形等の翻案等、自由に利用できます。商用利用も可能です。
> また、数値データ、簡単な表・グラフ等は著作権の対象ではありませんので、これらについては本利用ルールの適用はなく、自由に利用できます。

> イ　コンテンツを編集・加工等して利用する場合は、上記出典とは別に、編集・加工等を行ったことを記載してください。なお、編集・加工した情報を、あたかも国（又は府省等）が作成したかのような態様で公表・利用してはいけません。

> ウ　本利用ルールは、クリエイティブ・コモンズ・ライセンスの表示 4.0 国際（https://creativecommons.org/licenses/by/4.0/legalcode.ja に規定される著作権利用許諾条件。以下「CC BY」といいます。）と互換性があり、本利用ルールが適用されるコンテンツはCC BYに従うことでも利用することができます。

Maintainer's note: the terms are based on the Government Standard Terms of Use version 2.0 (政府標準利用規約 第2.0版) and are stated to be compatible with CC BY 4.0 (CC BY 4.0 と互換とされる). The licence field is
`other` on purpose, to point to the provider's own words. The terms exclude third-party rights, symbol marks and logos and content with a separate rule listed in their appendix (別紙): none of the six items of the appendix concerns the 水害統計調査.
The terms say that numerical data and simple tables are not subject to copyright; this dataset is made of such numbers, and it is offered under the same attribution conditions.

**Attribution (出典):** 出典：政府統計の総合窓口(e-Stat)（https://www.e-stat.go.jp/）、国土交通省『水害統計調査』を加工して作成

Processing notice: the numbers were extracted from the Excel files and reshaped into a long table (whitespace removed, header paths joined, labels of the hierarchical tables resolved);
the result is not a publication of the Ministry and was not made by the Ministry. The scripts are offered as is.

## Known issues

- **Revisions.** The Ministry corrects published numbers afterwards. The list pages of e-Stat carry these notes (all quoted from the saved pages `raw/{DATE}/listing/`):

{chr(10).join('  - ' + n for n in notes)}

  This dataset holds the files as they were on {DATE} (the latest version: the files are the current ones of the list; the publication date of each is in `catalog.published`). A file corrected later is not tracked by this dataset;
  to follow a correction, fetch again with `scripts/04_fetch_xls.py` and compare the sha256 in `raw/*/MANIFEST.json`.
- **Latest years.** 令和6年 (2024) has no table yet and 2025 onwards is not on the list: see Scope. 2026 events are not included.
- **Definition of 水害区域面積.** The Excel tables carry no definition or footnote of the term, and the PDF overviews that were read do not define it; **this dataset does not define it**. The unit is as in each header and differs between tables:
  ㎡ in the municipal tables, ha (ヘクタール) in 表-11, ａ (アール) in the 平成5年 base tables; check the `unit` column. The definition has to be taken from the Ministry's survey manual, which was not fetched (only www.e-stat.go.jp was used).
- **Differences between tables.** The unit of each table is the one of its own header or 単位 note (see `unit`): the same kind of amount can be in 百万円 in a prefecture table and in 千円 in a municipal table.
  A prefecture total in one table and the sum of the municipalities of another table are not meant to be equal.
- **Composition by year.** Before 平成12年 (1993 to 1999) only the four base tables (基本表) exist on the list; 平成12年 and 13年 have 17 selected tables, 平成14 to 平成23 about 18-19, 平成24 to 平成26 (45 files on the list) 19, 平成27 onwards 21 to 22; the table numbering moves between years (see `catalog.table_no`).
- **Municipalities.** Names and boundaries change by mergers; nothing is corrected. `area_code` is null: the tables carry no code. Names of the municipalities are as in each table (e.g. `千葉市中央区`).
- **Prefecture labels** are `千葉県` in most tables and `千葉` (without 県, with padding) in the older ones: {ltab}.
- **Blank and zero.** Older tables leave zeros blank; they are nulls here ({st['blank_cells']:,} records), not zeros.
- **Not read.** The {st['selection'].get('national', 0)} national Excel tables, the {st['selection'].get('timeseries', 0)} time-series tables and the {st['selection'].get('pdf', 0)} PDF files are not in the data (they are in `catalog` with `selection`).
  The 水害統計基本表の合計 holds national totals only (no prefecture). Sheets named 原本, 公共基本 and Sheet4 are templates or totals.
- **Prices.** The nominal amounts of each year are kept; no deflator is applied (the 水害被害額デフレーター table is a national table and is not included).
- **Not a flood-extent dataset.** These are statistics by municipality and by event, not inundation polygons.

## How to use

```python
import duckdb
duckdb.sql("select survey_year, area_name, measure, value, unit from 'parquet/chiba_long.parquet' "
           "where table_family='市区町村別水害被害' and level='municipality' and measure like '被害額合計%' order by 1, 2").show()
```

Scripts (`scripts/`): `01_catalog_fetch.py`, `02_catalog_build.py`, `03_select.py`, `04_fetch_xls.py`, `05_extract.py` (with `extract.py`), `06_verify.py` (with `xlsx_xml.py`), `07_catalog_parquet.py`, `08_stats.py`, `11_card.py`; tests in the GitHub repository.
"""
    (ROOT / "data" / "README.md").write_text(card, encoding="utf-8")
    (ROOT / "data" / "LICENSE").write_text(
        "The data is a processed copy of statistics published on e-Stat (政府統計の総合窓口) by the Ministry of Land, Infrastructure, Transport and Tourism (国土交通省, 水害統計調査).\n"
        "It is offered under the terms of e-Stat, https://www.e-stat.go.jp/terms-of-use , which are based on the Government Standard Terms of Use version 2.0 and are stated to be compatible with CC BY 4.0.\n\n"
        "Attribution (出典):\n出典：政府統計の総合窓口(e-Stat)（https://www.e-stat.go.jp/）、国土交通省『水害統計調査』を加工して作成\n\n"
        "The data was edited and reshaped; it was not made by the Government of Japan and must not be presented as if it were.\n"
        "Third-party rights are not cleared by this notice. The scripts of this repository are offered as is.\n\n"
        "----- The terms as fetched on " + meta["fetched_at"][:10] + " -----\n\n" + terms,
        encoding="utf-8")
    prov = {
        "dataset": REPO, "source": {"site": "e-Stat 政府統計の総合窓口", "toukei": "00600590", "name": "水害統計調査", "agency": "国土交通省",
                                     "list_url": "https://www.e-stat.go.jp/stat-search/files?toukei=00600590",
                                     "download_url_pattern": "https://www.e-stat.go.jp/stat-search/file-download?statInfId=<ID>&fileKind=0"},
        "fetched": {"date": DATE, "pause_seconds": 2, "files": st["tables_fetched"], "http_errors": 0, "api_used": False, "login_used": False},
        "licence": {"name": "e-Stat terms of use (政府標準利用規約 第2.0版 準拠; CC BY 4.0 互換とされる)", "url": "https://www.e-stat.go.jp/terms-of-use",
                    "evidence": ["evidence/terms-of-use.html", "evidence/terms-of-use.txt", "evidence/terms-of-use.meta.json"],
                    "attribution": "出典：政府統計の総合窓口(e-Stat)（https://www.e-stat.go.jp/）、国土交通省『水害統計調査』を加工して作成"},
        "coverage": {"survey_years_with_records": st["years_with_records"], "survey_years_listed": st["survey_years_listed"],
                     "latest_listed": "2024 (令和6年): PDF overview only, no table", "after_2024": "not listed at fetch time"},
        "counts": {k: st[k] for k in ("records", "chiba_rows", "sheets_read", "tables_fetched", "tables_with_chiba_rows", "files_listed")},
        "verification": {"cells_checked": ver["cells_checked"], "cells_equal": ver["cells_equal"], "float_noise": ver.get("float_noise", 0), "additivity": add},
        "parquet_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(P.glob("*.parquet"))},
        "known_revision_notes": notes,
    }
    (ROOT / "data" / "provenance.yaml").write_text(yaml.safe_dump(prov, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print("card", len(card), "chars")


if __name__ == "__main__":
    main()
