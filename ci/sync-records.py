#!/usr/bin/env python3
"""File purpose: keep the manifests (data/tools/manifest.json and
data/people/manifest.json) in step with their record files, reject records
that break the rules in docs/RECORD_FORMAT.md, and keep the README's rule list
generated from that file.

Run from the repo root: python3 ci/sync-records.py
Exit codes: 0 ok (manifests and README may have been rewritten), 1 a record or
manifest is invalid (each problem is printed as "<file>: message").
"""
import json
import re
import sys
from pathlib import Path

KINDS = ("tools", "people")
DATA_DIR = Path("data")
FILE_NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.json$")
KNOWN_SITES = {"portfolio", "vapt"}
README_FILE = Path("README.md")
RULES_FILE = Path("docs/RECORD_FORMAT.md")
RULES_START = "<!-- rules:start (generated from docs/RECORD_FORMAT.md by ci/sync-records.py; do not edit) -->"
RULES_END = "<!-- rules:end -->"


def kind_dir(kind):
    """Return the folder holding the records of one kind ('tools' or 'people')."""
    return DATA_DIR / kind


def record_files(kind):
    """Return the sorted names of a kind's record files (every *.json except its manifest)."""
    return sorted(p.name for p in kind_dir(kind).glob("*.json") if p.name != "manifest.json")


def load_manifest(kind):
    """Return a kind's manifest as a list of file names, or [] if it is absent."""
    path = kind_dir(kind) / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def load_record(kind, name):
    """Return the parsed record, or None when the file is not valid JSON."""
    try:
        return json.loads((kind_dir(kind) / name).read_text(encoding="utf-8"))
    except ValueError:
        return None


def validate_record(kind, name, tool_names):
    """Return the problems found in one record (an empty list means valid).
    Checks: file name shape, valid JSON with a name, show_on as a list of known
    sites, the group field needed for the portfolio (tools: category, people:
    domain), and for people that every entry of "tools" names a tool record."""
    problems = []
    if not FILE_NAME_PATTERN.match(name):
        problems.append("file name must be lowercase-with-dashes ending in .json")
    record = load_record(kind, name)
    if not isinstance(record, dict):
        return problems + ["not a valid JSON object"]
    if not str(record.get("name", "")).strip():
        problems.append('"name" is required')
    show_on = record.get("show_on")
    if not isinstance(show_on, list) or not set(show_on) <= KNOWN_SITES:
        problems.append('"show_on" must be a list using only: %s' % ", ".join(sorted(KNOWN_SITES)))
    elif "portfolio" in show_on:
        group = "category" if kind == "tools" else "domain"
        if not record.get(group):
            problems.append('"%s" is required when shown on the portfolio' % group)
    if kind == "people":
        linked = record.get("tools")
        if not isinstance(linked, list) or not set(linked) <= tool_names:
            problems.append('"tools" must be a list of existing tool record names')
    return problems


def tool_record_names():
    """Return the set of "name" values of all valid tool records."""
    names = set()
    for file in record_files("tools"):
        record = load_record("tools", file)
        if isinstance(record, dict) and record.get("name"):
            names.add(record["name"])
    return names


def collect_problems(tool_names):
    """Return {"<kind>/<file>": [problems]} for every record and manifest entry
    that is invalid, across both kinds."""
    found = {}
    for kind in KINDS:
        files = record_files(kind)
        for file in files:
            found["%s/%s" % (kind, file)] = validate_record(kind, file, tool_names)
        for file in load_manifest(kind):
            if file not in files:
                found.setdefault("%s/%s" % (kind, file), []).append("listed in manifest.json but the file is missing")
    return {key: value for key, value in found.items() if value}


def write_manifests():
    """Append record files missing from each manifest. Returns the added names."""
    added = []
    for kind in KINDS:
        listed = load_manifest(kind)
        new = [f for f in record_files(kind) if f not in listed]
        (kind_dir(kind) / "manifest.json").write_text(json.dumps(listed + new, indent=2) + "\n", encoding="utf-8")
        added += ["%s/%s" % (kind, f) for f in new]
    return added


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
    """Validate every record, then update the manifests and the README rule
    list. Returns the process exit code."""
    problems = collect_problems(tool_record_names())
    for key, found in sorted(problems.items()):
        for message in found:
            print("%s: %s" % (key, message), file=sys.stderr)
    if problems:
        return 1
    added = write_manifests()
    if added:
        print("sync-records: added to manifests: " + ", ".join(added))
    return 0 if write_readme_rules() else 1


if __name__ == "__main__":
    sys.exit(main())
