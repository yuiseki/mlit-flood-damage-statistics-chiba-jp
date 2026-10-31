#!/usr/bin/env python3
"""Push the card, licence, provenance, raw MANIFEST and listing pages (not the Excel files), Parquet, scripts and docs of this dataset.

uv run python src/publish.py             # dry run: list the files and their sizes
uv run python src/publish.py --push      # one commit; prints the sha and writes docs/revision.json  (NOT to be run before the owner approves)
"""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPO = "yuiseki/mlit-flood-damage-statistics-chiba-jp"


def collect() -> dict[str, Path]:
    card = (DATA / "README.md").read_text(encoding="utf-8")
    if "license: other" not in card or "license_name:" not in card:
        raise SystemExit("the card does not declare license: other with a license_name")
    stats = json.loads((DATA / "parquet" / "stats.json").read_text())
    for key in ("records", "chiba_rows", "tables_fetched"):
        if f"{stats[key]:,}" not in card:
            raise SystemExit(f"the card does not give {stats[key]:,} ({key})")
    files: dict[str, Path] = {"README.md": DATA / "README.md", "LICENSE": DATA / "LICENSE", "provenance.yaml": DATA / "provenance.yaml"}
    for p in sorted((DATA / "parquet").glob("*.parquet")):
        files[f"parquet/{p.name}"] = p
    for p in sorted((ROOT / "raw").rglob("*")):
        # the Excel files themselves are not published (the user's decision): their sha256 are in MANIFEST.json
        if p.is_file() and "/xls/" not in p.relative_to(ROOT).as_posix():
            files[p.relative_to(ROOT).as_posix()] = p
    for p in sorted((ROOT / "evidence").glob("*")):
        files[f"evidence/{p.name}"] = p
    for p in sorted((ROOT / "scripts").glob("*")):
        if p.is_file() and p.suffix in (".py", ".sh"):
            files[f"scripts/{p.name}"] = p
    for p in sorted((ROOT / "docs").glob("*")):
        if p.is_file() and p.name not in ("revision.json", "verify_hub.json"):
            files[f"docs/{p.name}"] = p
    return files


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()
    files = collect()
    total = sum(p.stat().st_size for p in files.values())
    print(f"{a.repo}\n  {len(files)} files, {total:,} bytes")
    groups: dict[str, list[int]] = {}
    for k, p in files.items():
        g = k.split("/")[0] if "/" in k else "(top)"
        if k.startswith("raw/"):
            g = "/".join(k.split("/")[:3])
        s = groups.setdefault(g, [0, 0])
        s[0] += 1
        s[1] += p.stat().st_size
    for g, (n, b) in sorted(groups.items()):
        print(f"  {g:32s} {n:5d} files {b:>14,} bytes")
    if not a.push:
        print("\ndry run. pass --push to upload")
        return 0
    from huggingface_hub import CommitOperationAdd, HfApi

    api = HfApi()
    api.create_repo(a.repo, repo_type="dataset", exist_ok=True, private=False)
    ops = [CommitOperationAdd(path_in_repo=k, path_or_fileobj=str(v)) for k, v in files.items()]
    c = api.create_commit(a.repo, ops, repo_type="dataset", commit_message="Chiba rows of the MLIT 水害統計調査 (e-Stat), 1993 to 2023, without the raw Excel files")
    rev = {"repo": a.repo, "revision": c.oid, "pushed": datetime.now(UTC).isoformat(timespec="seconds"),
           "sha256": {k: sha256(v) for k, v in files.items() if k.startswith("parquet/") or k in ("README.md", "LICENSE")}}  # fmt: skip
    (ROOT / "docs" / "revision.json").write_text(json.dumps(rev, indent=1) + "\n")
    print(f"pushed {a.repo} revision {c.oid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
