# Record format

This repo is the only place tool and people details are written; every site fetches them from here and decides for itself what to show. There are two kinds of record, one JSON file each:

- **tools** in `data/tools/` (for example `theharvester.json`)
- **people** in `data/people/`, the researchers behind the tools (for example `paul-vixie.json`)

Files are named lowercase-with-dashes. Each folder has a `manifest.json` listing its files.

## Tool record

```json
{
  "name": "subfinder",
  "purpose": "One-line summary of what the tool does",
  "author": "Bhomesh Koli (Ice3man543)",
  "org": "ProjectDiscovery",
  "year": "2018",
  "language": "Go",
  "phase": "Phase 1 — Reconnaissance",
  "category": "Hacking Tools",
  "why_notable": "Paragraph on who built it, why, and why it matters.",
  "links": { "GitHub": "https://github.com/projectdiscovery/subfinder" },
  "show_on": ["vapt"]
}
```

## Rules (checked automatically)

`ci/sync-records.py` checks these on every commit; a record that breaks one cannot be committed. The README's rule list is generated from the `R<n>` lines below; edit the rules here, never in the README.

- **R1 File name.** One record per file, in `data/tools/` or `data/people/`, named lowercase-with-dashes ending in `.json`.
- **R2 Valid record.** The file is valid JSON and has a non-empty `name`.
- **R3 Sites.** `show_on` is a list that uses only known sites: `"portfolio"`, `"vapt"`. An empty list keeps the record stored but shown nowhere.
- **R4 Group.** A record shown on `portfolio` has a group: `category` for a tool, `domain` for a person.
- **R5 People link to tools.** A person has a `tools` list (it may be empty), and every entry is the exact `name` of a tool record.
- **R6 Manifests.** Each `manifest.json` lists exactly the record files in its folder and is maintained by the check; never edit it by hand. It may not list a file that does not exist.

## Tool fields

| Field | Required | Meaning |
|-------|----------|---------|
| `name` | yes | Tool name. The VAPT page matches it to its own tool names (`dig` matches `dig / host / nslookup`). |
| `show_on` | yes | List of sites that show this record: `"portfolio"`, `"vapt"`. An empty list keeps the record stored but shown nowhere. |
| `category` | if shown on `portfolio` | Top-level group on the portfolio page (for example `Hacking Tools`, `Unix Tools`). |
| `phase` | no | Sub-group inside a category on the portfolio page. Leave out for a flat category. |
| `purpose`, `author`, `org`, `year`, `language`, `why_notable`, `links` | no | Shown as available. |

## Person record

```json
{
  "name": "Paul Vixie",
  "handle": null,
  "domain": "DNS & Internet Infrastructure",
  "era": "1980s-present",
  "org": "UC Berkeley, DEC, ISC",
  "why_notable": "One paragraph.",
  "links": { "Label": "https://..." },
  "tools": ["dig"],
  "show_on": ["portfolio", "vapt"]
}
```

| Field | Required | Meaning |
|-------|----------|---------|
| `name` | yes | The person's name. |
| `show_on` | yes | Sites that show this record. On `vapt` the person appears inside the Origin block of each tool in `tools` (only if that tool is shown there). |
| `tools` | yes | Tool record names this person is linked to; may be empty. The link lives on the person only. |
| `domain` | if shown on `portfolio` | Section on the Operatives page. |
| `handle`, `era`, `org`, `why_notable`, `links` | no | Shown as available. |

## Study notes

Longer Markdown study notes for a tool live in `notes/tools/<tool>.md` (one file per tool, lowercase-with-dashes, same stem as the tool record where possible). They are plain reading material: sites do not fetch them, and the record checker does not read them. A tool record links to its note with `links["Study notes"]`, using the GitHub URL `https://github.com/fmfalgun/library-data/blob/main/notes/tools/<tool>.md`. Never put a real target's hostname, credentials, session data or other client material in a note: this repo is public.

## Adding or changing a record

1. Create or edit the file in `data/tools/` or `data/people/`.
2. Set `show_on` to the sites that should show it.
3. Commit. The pre-commit hook runs `ci/sync-records.py`, which checks the record and appends new files to the manifest. Never edit a manifest by hand.

A site picks the change up on its next page load; no site repo changes.
