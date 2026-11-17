# Tool record format

One JSON file per tool in `data/`, named lowercase-with-dashes (`theharvester.json`). This repo is the only place tool details are written; every site fetches them from here and decides for itself what to show.

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

## Fields

| Field | Required | Meaning |
|-------|----------|---------|
| `name` | yes | Tool name. The VAPT page matches it to its own tool names (`dig` matches `dig / host / nslookup`). |
| `show_on` | yes | List of sites that show this record: `"portfolio"`, `"vapt"`. An empty list keeps the record stored but shown nowhere. |
| `category` | if shown on `portfolio` | Top-level group on the portfolio page (for example `Hacking Tools`, `Unix Tools`). |
| `phase` | no | Sub-group inside a category on the portfolio page. Leave out for a flat category. |
| `purpose`, `author`, `org`, `year`, `language`, `why_notable`, `links` | no | Shown as available. |

## Adding or changing a tool

1. Create or edit `data/<name>.json`.
2. Set `show_on` to the sites that should show it.
3. Commit. The pre-commit hook runs `ci/sync-records.py`, which checks the record and appends new files to `data/manifest.json`. Never edit the manifest by hand.

A site picks the change up on its next page load; no site repo changes.
