# mlit-flood-damage-statistics-chiba-jp-2026-10

Scripts that list, fetch, read and verify the Chiba rows of the MLIT 水害統計調査 Excel tables on e-Stat (1993 to 2023), and prepare the Hugging Face dataset
`yuiseki/mlit-flood-damage-statistics-chiba-jp-2026-10` (not yet published). See `data/README.md` (the card) and `docs/STEPS.md`.

    uv sync
    uv run pytest
    uv run python scripts/01_catalog_fetch.py && uv run python scripts/02_catalog_build.py && uv run python scripts/03_select.py
    uv run python scripts/04_fetch_xls.py && uv run python scripts/05_extract.py && uv run python scripts/07_catalog_parquet.py
    uv run python scripts/06_verify.py && uv run python scripts/08_stats.py && uv run python scripts/11_card.py
    uv run python src/publish.py          # dry run only
