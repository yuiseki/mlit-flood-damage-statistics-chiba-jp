---
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

**Scope, stated first.** The survey is published one to two years after the flood year. At the time of fetching (2026-10-31) the
e-Stat list had 32 survey years, 平成5年 (1993) to 令和6年 (2024).
**令和6年 (2024) has one file only, the PDF overview "令和６年の水害被害の概要" (published on the list on 2026-01-07), and no statistical table (Excel): its Chiba rows
are not in this dataset, because the tables are not yet published.** No survey year after 令和6年 (2025 onwards) is listed. Floods of 2025 and 2026 are therefore **not**
in this dataset; in particular the 令和8年8月 Chiba heavy rain and typhoon No. 25 of 2026 are not included. The last survey year with tables here
is 令和5年 (2023; list published 2026-01-14, tables 2025-07-31 and 2025-10-03).

## Source

- List of files: <https://www.e-stat.go.jp/stat-search/files?toukei=00600590> (each survey year: `tstat`; each file: `statInfId`).
- A file: `https://www.e-stat.go.jp/stat-search/file-download?statInfId=<ID>&fileKind=0` (the plain download link of the site; no API, no login).
- Fetched on 2026-10-31, one request at a time with a 2 s pause. 495 Excel files, no HTTP error, no block. The responses carry no `Last-Modified` header
  (null in `catalog`); the publication date of each file is the 公開（更新）日 of the list (`published`, 2015-04-24 to 2025-10-03).
- The Excel files were kept unchanged locally as `raw/2026-10-31/xls/` (the extension is that of the real format, `.xlsx` or `.xls`); **they are not part of this dataset** (fetch them again from e-Stat with `scripts/04_fetch_xls.py` and compare with `raw/2026-10-31/MANIFEST.json`: sha256, fetch time, headers, URL),
  and the saved list pages in `raw/2026-10-31/listing/`.

## Which tables are in

The list has 1,661 files of 32 survey years: 495 Excel tables were selected by a rule on the title (`docs/catalog_selected.tsv`, `scripts/03_select.py`):
the title has 都道府県別, 市区町村別 or 基本表 (a prefecture or municipality dimension, or the base tables), and not 過去NN年間. The others were not fetched:
357 Excel tables without a prefecture dimension (national tables), 409 time-series tables of the latest report (過去10年間 / 過去20年間 ... they repeat numbers of other years),
400 PDF files (figures and overviews). All 495 fetched files were read; 461 of them hold Chiba rows, 34 do not (reasons below).

Table families (the title without the table number; the numbering moves between years, e.g. 表-3 市区町村別水害被害 is 表-3 in most years but the tables before 平成12年 do not exist):

| Table family | Survey years | Files | Chiba rows |
|---|---|---|---|
| 主要異常気象別都道府県別水害被害 | 2000-2023 | 43 | 98 |
| 一般資産等水害統計基本表 | 1993-2023 | 31 | 4,158 |
| 公共土木施設水害統計基本表 | 1993-2023 | 31 | 9,360 |
| 公益事業等水害統計基本表 | 1993-2023 | 31 | 707 |
| 水害統計基本表の合計 | 1993-2023 | 30 | 0 |
| 水害原因別市区町村別一般資産等被害額 | 2000-2023 | 24 | 417 |
| 水害原因別都道府県別公益事業等被害額 | 2000-2023 | 24 | 24 |
| 水害原因別都道府県別水害被害額(一般資産等被害額・公益事業等被害額合計) | 2000-2023 | 24 | 24 |
| 水害原因別都道府県別農作物被害額 | 2000-2023 | 24 | 24 |
| 河川等種類別市区町村別一般資産等被害額 | 2000-2023 | 24 | 419 |
| 河川等種類別都道府県別一般資産等被害額 | 2000-2023 | 24 | 24 |
| 河川等種類別都道府県別公共土木施設被害額 | 2000-2023 | 24 | 24 |
| 河川等種類別都道府県別公益事業等被害額 | 2000-2023 | 24 | 24 |
| 河川等種類別都道府県別水害被害額 | 2000-2023 | 24 | 24 |
| 都道府県別水害被害 | 2000-2023 | 24 | 30 |
| 市区町村別水系別一般資産等水害被害 | 2001-2023 | 23 | 837 |
| 水害原因別都道府県別一般資産等被害額(農作物被害額を除く) | 2001-2023 | 23 | 23 |
| 市区町村別主要異常気象別一般資産等水害被害 | 2000-2023 | 20 | 600 |
| 市区町村別水害被害 | 2007-2023 | 17 | 493 |
| 市区町村別水害被害一覧 | 2002-2006 | 5 | 163 |
| 水害原因別都道府県別一般資産等被害額(営業停止損失分含む) | 2000-2000 | 1 | 1 |

## Files

| File | Rows | What a row is |
|---|---|---|
| `parquet/chiba_long.parquet` | 244,476 | One cell of a Chiba row of a table (17,474 Chiba rows of 649 sheets) |
| `parquet/tables.parquet` | 649 | One sheet read: what was found, key and data columns, the number of Chiba rows |
| `parquet/catalog.parquet` | 1,661 | One file of the e-Stat list (all years, all formats) with the selection and, if fetched, its sha256 |
| `parquet/year_checks.parquet` | 32 | One survey year: tables, rows, cells checked, additivity checks |
| `raw/` | MANIFEST.json + list pages | The sha256, fetch time and URL of the 495 Excel files (not included), and the saved list pages |

`chiba_long` columns: `survey_year` (the western year; 平成5年 = 1993), `survey_year_label`, `table_id` (the `statInfId`), `table_no` (表-N from the title, null for the base tables),
`table_title` (the title on the list), `table_family`, `sheet_title` (the title cell of the sheet, whitespace removed; for 表-11 it holds the name of the event),
`pref_label` (the prefecture cell as in the table, whitespace removed: `千葉` 188,475, `千葉県` 56,001), `area_code` (null in all rows: no table carries a municipality code), `area_name` (the municipality, or the
prefecture label for a prefecture-level row, as in the table, e.g. 千葉市中央区, 合計), `level` (`municipality`, or `prefecture` = a row of a prefecture table or a 合計/total row),
`row_class` (JSON: the other row labels of the table, e.g. 水系名, 異常気象名, 河川・海岸名等, 水害原因; see "Hierarchical base tables"), `measure` (the header path of the column from the top
to the bottom of the header, joined by " / ", whitespace removed), `value` (double; null for a blank or a symbol), `unit` (from the header, e.g. （㎡）, or from the table's 単位 note; null in 85,346 records where the table gives none),
`symbol` (the text of a non-numeric cell), `note` (`blank`, `prefecture name inherited from the row above`, `ditto mark (〃) resolved ...`), `source_statInfId`, `source_file`, `source_sheet`,
`source_cell` (e.g. `B19`), `source_row`, `source_col`, `header_cells` (the cells the measure comes from).
Units found: `千円` 89,999, `(none)` 85,346, `棟` 39,950, `㎡` 19,185, `cm` 4,713, `百万円` 3,826, `ａ` 851, `ha` 294, `延べ数` 216, `人` 96.

## How it was read

`scripts/extract.py` (openpyxl for .xlsx, xlrd for .xls). The header of a column is collected from the first row to the last header row, through merged cells and
"center across selection" cells; a header text wrapped over several rows stays in separate segments (e.g. `公共土 / 木施設`). All whitespace
(padding, ideographic spaces, newlines) is removed from texts. Numbers are not converted: a blank cell is a null (older tables show zero as a blank: 33,729 records are blank),
a symbol is kept in `symbol`. 2,302 Chiba rows had no prefecture name of their own and inherit it from the row above; 9,831 rows hold the ditto mark 〃 in a label column
(resolved from the row above, flagged in `note`). Header rows repeated in the middle of a sheet (page breaks) are skipped. The sheets of a workbook are read in order, so that
a sheet that goes on with the rows of the sheet before it belongs to the right prefecture (in 平成11, 12 and 13 the tabs 公共土木N are not in the order of N and are read by N).
The footnotes of the tables: none of the fetched Excel tables carries a note row.

### Hierarchical base tables

The 基本表 of the early years (survey years 1993 to 2013) use a hierarchical layout: in the first label column the prefecture, the event (異常気象名), its dates (水害発生年月) and the river system (水系・沿岸名) follow
one another in turn, and the following rows write 〃 for "same as above". The records of those sheets (10,803 Chiba rows) carry the resolved labels in `row_class`
(`異常気象名`, `（水害発生年月）`, `水系・沿岸名`, ...); a row of the prefecture or the event has null for the labels it does not have. The base tables of later years carry the labels in separate columns and write the totals as 合計.

## Verification

By a route that shares no code with the extraction (`scripts/06_verify.py`; the .xls files were converted by LibreOffice and read with a zipfile + XML reader):

- **Cells:** every one of the 244,476 records was read again from its `source_cell`: 244,476 equal; 44 of them differ by floating-point noise
  only (formula cells recomputed by the other reader, relative difference below 1e-9; the value in the table is the cached value read by the extraction); 0 differ otherwise.
- **Completeness:** every non-empty cell in a data column of an extracted row is in the table (0 missing); a scan of the first four columns of every sheet for 千葉 / 千葉県 found no row that was not extracted (0 missed);
  the rows of the hierarchical form carry no prefecture name and cannot be found by that scan (10,734 rows).
- **Totals inside a table** (municipalities or other breakdowns against the 合計 row of the same table, 14,966 comparisons in 122 sheets): 14,297 equal,
  38 differ by at most one unit (rounding), **631 differ in 31 sheets**. In the municipal and prefecture tables (3,895 comparisons) the mismatches are 0.
  All the others are in the 基本表 (11,071 comparisons, 631 mismatches), where the 合計 rows sit at several levels of a hierarchy and the check is not a proof either way; the differences are listed in `docs/06_verify.json` and nothing was corrected.
- **Rows before any prefecture name:** 6 rows with numbers precede the first prefecture name of a sheet (1999 一般資産等水害統計基本表 合計: 1; 1999 公益事業等水害統計基本表 合計: 1; 2000 一般資産等水害統計基本表 合計: 1; 2000 公益事業等水害統計基本表 合計: 1; 2001 一般資産等水害統計基本表 合計: 1; 2001 公益事業等水害統計基本表 合計: 1; see `tables.orphan_rows`). They are not assigned to Chiba and are not included.
- 34 fetched files have no Chiba row (`docs/08_zero_chiba.tsv`): 30 are workbooks or sheets that hold national totals or empty templates (`水害統計基本表の合計`, `原本` sheets), the others are base-table workbooks of which some sheets hold other prefectures only.

Per survey year (32 years listed; `year_checks.parquet` has the checks):

| Survey year | Label | Files listed | Excel | PDF | Excel fetched | Files with Chiba rows | Chiba rows | Records |
|---|---|---|---|---|---|---|---|---|
| 1993 | 平成５年水害統計調査 | 4 | 4 | 0 | 4 | 3 | 890 | 11,054 |
| 1994 | 平成６年水害統計調査 | 4 | 4 | 0 | 4 | 2 | 240 | 3,795 |
| 1995 | 平成７年水害統計調査 | 4 | 4 | 0 | 4 | 3 | 910 | 10,792 |
| 1996 | 平成８年水害統計調査 | 3 | 3 | 0 | 3 | 3 | 2,553 | 31,782 |
| 1997 | 平成９年水害統計調査 | 4 | 4 | 0 | 4 | 3 | 77 | 1,292 |
| 1998 | 平成１０年水害統計調査 | 4 | 4 | 0 | 4 | 3 | 69 | 1,032 |
| 1999 | 平成１１年水害統計調査 | 4 | 4 | 0 | 4 | 3 | 651 | 7,569 |
| 2000 | 平成１２年水害統計調査 | 42 | 30 | 12 | 17 | 16 | 347 | 4,441 |
| 2001 | 平成１３年水害統計調査 | 38 | 27 | 11 | 17 | 16 | 441 | 6,205 |
| 2002 | 平成１４年水害統計調査 | 37 | 29 | 8 | 18 | 17 | 230 | 3,165 |
| 2003 | 平成１５年水害統計調査 | 69 | 52 | 17 | 18 | 17 | 356 | 4,443 |
| 2004 | 平成１６年水害統計調査 | 74 | 57 | 17 | 18 | 17 | 1,269 | 17,000 |
| 2005 | 平成１７年水害統計調査 | 75 | 58 | 17 | 19 | 18 | 436 | 5,369 |
| 2006 | 平成１８年水害統計調査 | 77 | 58 | 19 | 19 | 18 | 857 | 10,896 |
| 2007 | 平成１９年水害統計調査 | 77 | 58 | 19 | 19 | 18 | 461 | 6,501 |
| 2008 | 平成２０年水害統計調査 | 77 | 58 | 19 | 19 | 18 | 469 | 8,011 |
| 2009 | 平成２１年水害統計調査 | 77 | 58 | 19 | 19 | 18 | 290 | 4,558 |
| 2010 | 平成２２年水害統計調査 | 77 | 58 | 19 | 19 | 18 | 767 | 11,778 |
| 2011 | 平成２３年水害統計調査 | 77 | 57 | 20 | 19 | 18 | 351 | 5,380 |
| 2012 | 平成２４年水害統計調査 | 45 | 31 | 14 | 19 | 18 | 161 | 2,648 |
| 2013 | 平成２５年水害統計調査 | 45 | 31 | 14 | 19 | 18 | 1,518 | 24,417 |
| 2014 | 平成２６年水害統計調査 | 45 | 31 | 14 | 19 | 18 | 387 | 6,007 |
| 2015 | 平成２７年水害統計調査 | 78 | 60 | 18 | 21 | 19 | 307 | 5,244 |
| 2016 | 平成２８年水害統計調査 | 78 | 60 | 18 | 21 | 20 | 369 | 5,825 |
| 2017 | 平成２９年水害統計調査 | 78 | 60 | 18 | 21 | 20 | 491 | 7,059 |
| 2018 | 平成３０年水害統計調査 | 78 | 60 | 18 | 21 | 20 | 128 | 1,895 |
| 2019 | 令和元年水害統計調査 | 78 | 60 | 18 | 21 | 20 | 1,181 | 17,816 |
| 2020 | 令和２年水害統計調査 | 79 | 61 | 18 | 22 | 19 | 29 | 578 |
| 2021 | 令和３年水害統計調査 | 78 | 60 | 18 | 21 | 20 | 427 | 5,866 |
| 2022 | 令和４年水害統計調査 | 76 | 60 | 16 | 21 | 20 | 108 | 1,766 |
| 2023 | 令和５年水害統計調査 | 78 | 60 | 18 | 21 | 20 | 704 | 10,292 |
| 2024 | 令和６年水害統計調査 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |

## Licence

The data is a processed copy of public statistics of the Japanese government. The terms of e-Stat (<https://www.e-stat.go.jp/terms-of-use>, saved in `evidence/terms-of-use.html` and `evidence/terms-of-use.txt`, fetched 2026-10-31, sha256 0efa0be58bb58a5d...) say:

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

- **Revisions.** The Ministry corrects published numbers afterwards. The list pages of e-Stat carry these notes (all quoted from the saved pages `raw/2026-10-31/listing/`):

  - ※「平成２８年水害統計」の数値等について、平成３１年４月２６日修正しました。
  - ※「平成２７年水害統計」、「平成２６年水害統計」、「平成２５年水害統計」、「平成２４年水害統計」の数値等について、令和元年６月２８日修正しました。
  - ※「平成２９年水害統計」の数値等について、令和元年１２月２５日修正しました。
  - ※「令和元年水害統計」、「平成３０年水害統計」、「平成２９年水害統計」、「平成２８年水害統計」、「平成２７年水害統計」の数値等について令和４年８月１０日修正しました。
  - ※「平成１９年水害統計」、「平成２１年水害統計」、「平成２２年水害統計」、「平成２３年水害統計」、「平成２４年水害統計」の数値等について令和５年４月２６日修正しました。
  - ※「平成14年水害統計」～「平成21年水害統計」、「平成26年水害統計」～「令和3年水害統計」の基本表について、令和6年9月18日修正しました。
  - ※「「平成24年水害統計」、「平成26年水害統計」、「平成28年水害統計」、「平成29年水害統計」、「令和2年水害統計」～「令和5年水害統計」の参考等について、令和７年１０月３日修正しました。

  This dataset holds the files as they were on 2026-10-31 (the latest version: the files are the current ones of the list; the publication date of each is in `catalog.published`). A file corrected later is not tracked by this dataset;
  to follow a correction, fetch again with `scripts/04_fetch_xls.py` and compare the sha256 in `raw/*/MANIFEST.json`.
- **Latest years.** 令和6年 (2024) has no table yet and 2025 onwards is not on the list: see Scope. 2026 events are not included.
- **Definition of 水害区域面積.** The Excel tables carry no definition or footnote of the term, and the PDF overviews that were read do not define it; **this dataset does not define it**. The unit is as in each header and differs between tables:
  ㎡ in the municipal tables, ha (ヘクタール) in 表-11, ａ (アール) in the 平成5年 base tables; check the `unit` column. The definition has to be taken from the Ministry's survey manual, which was not fetched (only www.e-stat.go.jp was used).
- **Differences between tables.** The unit of each table is the one of its own header or 単位 note (see `unit`): the same kind of amount can be in 百万円 in a prefecture table and in 千円 in a municipal table.
  A prefecture total in one table and the sum of the municipalities of another table are not meant to be equal.
- **Composition by year.** Before 平成12年 (1993 to 1999) only the four base tables (基本表) exist on the list; 平成12年 and 13年 have 17 selected tables, 平成14 to 平成23 about 18-19, 平成24 to 平成26 (45 files on the list) 19, 平成27 onwards 21 to 22; the table numbering moves between years (see `catalog.table_no`).
- **Municipalities.** Names and boundaries change by mergers; nothing is corrected. `area_code` is null: the tables carry no code. Names of the municipalities are as in each table (e.g. `千葉市中央区`).
- **Prefecture labels** are `千葉県` in most tables and `千葉` (without 県, with padding) in the older ones: `千葉` 188,475, `千葉県` 56,001.
- **Blank and zero.** Older tables leave zeros blank; they are nulls here (33,729 records), not zeros.
- **Not read.** The 357 national Excel tables, the 409 time-series tables and the 400 PDF files are not in the data (they are in `catalog` with `selection`).
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
