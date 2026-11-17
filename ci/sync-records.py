#!/usr/bin/env python3
"""File purpose: keep data/manifest.json (the list of tool records) in step
with the data/*.json files, reject records that break the rules in
docs/RECORD_FORMAT.md, and keep the README's rule list generated from that file.

Run from the repo root: python3 ci/sync-records.py
Exit codes: 0 ok (the manifest may have been rewritten), 1 a record or the
manifest is invalid (each problem is printed as "<file>: message").
"""
import json
import re
import sys
from pathlib import Path

DATA_DIR = Path("data")
MANIFEST_FILE = DATA_DIR / "manifest.json"
FILE_NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.json$")
KNOWN_SITES = {"portfolio", "vapt"}
README_FILE = Path("README.md")
RULES_FILE = Path("docs/RECORD_FORMAT.md")
RULES_START = "<!-- rules:start (generated from docs/RECORD_FORMAT.md by ci/sync-records.py; do not edit) -->"
RULES_END = "<!-- rules:end -->"


def record_files():
    """Return the sorted names of the record files (every data/*.json except the manifest)."""
    return sorted(p.name for p in DATA_DIR.glob("*.json") if p.name != MANIFEST_FILE.name)


def load_manifest():
    """Return the manifest's list of file names, or an empty list if the file is absent."""
    if not MANIFEST_FILE.exists():
        return []
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def validate_record(name):
    """Return the problems found in one record file (an empty list means valid).
    Checks: file name shape, valid JSON object, a name, show_on as a list of
    known sites, and a category when the record is shown on the portfolio."""
    problems = []
    if not FILE_NAME_PATTERN.match(name):
        problems.append("file name must be lowercase-with-dashes ending in .json")
    try:
        record = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    except ValueError as err:
        return problems + ["invalid JSON: %s" % err]
    if not str(record.get("name", "")).strip():
        problems.append('"name" is required')
    show_on = record.get("show_on")
    if not isinstance(show_on, list) or not set(show_on) <= KNOWN_SITES:
        problems.append('"show_on" must be a list using only: %s' % ", ".join(sorted(KNOWN_SITES)))
    elif "portfolio" in show_on and not record.get("category"):
        problems.append('"category" is required when shown on the portfolio')
    return problems


def write_readme_rules():
    """Replace the text between the rules markers in README.md with the R<n>
    lines of docs/RECORD_FORMAT.md. Returns False (and writes nothing) when a
    marker is missing."""
    rules = "\n".join(line for line in RULES_FILE.read_text(encoding="utf-8").splitlines() if re.match(r"^- \*\*R\d+ ", line))
    text = README_FILE.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(RULES_START) + r".*?" + re.escape(RULES_END), re.S)
    if not pattern.search(text):
        print("sync-records: README.md has no rules:start / rules:end markers", file=sys.stderr)
        return False
    README_FILE.write_text(pattern.sub(lambda _: RULES_START + "\n" + rules + "\n" + RULES_END, text), encoding="utf-8")
    return True


def main():
    """Validate every record, then append new files to the manifest.
    Returns the process exit code."""
    files = record_files()
    problems = {name: validate_record(name) for name in files}
    listed = load_manifest()
    for name in listed:
        if name not in files:
            problems.setdefault(name, []).append("listed in manifest.json but the file is missing")
    failed = {name: found for name, found in problems.items() if found}
    for name, found in sorted(failed.items()):
        for message in found:
            print("%s: %s" % (name, message), file=sys.stderr)
    if failed:
        return 1
    new = [name for name in files if name not in listed]
    MANIFEST_FILE.write_text(json.dumps(listed + new, indent=2) + "\n", encoding="utf-8")
    if new:
        print("sync-records: added to manifest.json: " + ", ".join(new))
    return 0 if write_readme_rules() else 1


if __name__ == "__main__":
    sys.exit(main())
