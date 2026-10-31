# Steps and what each produced (facts of the run of 2026-10-31)

1. Survey (`scripts/01_catalog_fetch.py`, `02_catalog_build.py`): 32 survey years (tstat) on the list, 1661 files; `docs/catalog.tsv`. The list pages are server-rendered:
   the top page lists the years, a year page lists the categories (tclass1), a category page lists the files (statInfId, formats, dates). Counts of every page agree with the parsed rows (`docs/02_catalog_build.log`).
   令和6年 (2024): 1 file (PDF overview), no Excel. No year after 2024 on the list. 平成5-11年: 3-4 files each (base tables only). 平成24-26年: 45 files; 平成12-23年: 37-77 files; 平成27-令和5年: 76-79 files.
2. Selection (`03_select.py`): the rule is in the script; `docs/catalog_selected.tsv`.
3. Fetch (`04_fetch_xls.py`): 495 files, 2 s apart, no error (`docs/04_fetch_xls.log`, `raw/2026-10-31/MANIFEST.json`). No Last-Modified header is sent.
4. Extraction (`05_extract.py`, `extract.py`): `data/parquet/chiba_long.parquet`, `tables.parquet`.
5. Verification (`06_verify.py`): `docs/06_verify.json`, `06_verify.log`; per-year counts `docs/08_years.tsv`; files without Chiba rows `docs/08_zero_chiba.tsv`.
6. Card, licence, provenance (`11_card.py`); dry run of the publication `docs/publish_dry_run.txt`.
