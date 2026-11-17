# library-data

The single home of tool and people details (for tools: author, organisation, year, language, the "why notable" story, links; for people: era, organisation, why notable, and the tools they are linked to). Sites fetch these records and each shows only the ones that list it in `show_on`:

- `portfolio` - the Toolkit and Operatives pages on `fmfalgun.github.io` (tools outside the VAPT list, and people)
- `vapt` - the VAPT Toolkit page in the [library](https://github.com/fmfalgun/library) repo (tool details, with the linked people inside each tool)

Records are served by GitHub Pages at `https://fmfalgun.github.io/library-data/data/tools/<file>.json` and `.../data/people/<file>.json`; each folder's list of files is its `manifest.json`. Record fields and how to add a tool: [`docs/RECORD_FORMAT.md`](docs/RECORD_FORMAT.md).

## Record rules

Every record must follow these rules; `ci/sync-records.py` checks them on every commit, so a record that breaks one cannot be committed.

<!-- rules:start (generated from docs/RECORD_FORMAT.md by ci/sync-records.py; do not edit) -->
- **R1 File name.** One record per file, in `data/tools/` or `data/people/`, named lowercase-with-dashes ending in `.json`.
- **R2 Valid record.** The file is valid JSON and has a non-empty `name`.
- **R3 Sites.** `show_on` is a list that uses only known sites: `"portfolio"`, `"vapt"`. An empty list keeps the record stored but shown nowhere.
- **R4 Group.** A record shown on `portfolio` has a group: `category` for a tool, `domain` for a person.
- **R5 People link to tools.** A person has a `tools` list (it may be empty), and every entry is the exact `name` of a tool record.
- **R6 Manifests.** Each `manifest.json` lists exactly the record files in its folder and is maintained by the check; never edit it by hand. It may not list a file that does not exist.
<!-- rules:end -->

## Directory structure

```
library-tools/
├── README.md        repo details and structure
├── .gitignore       keeps keys, env files and local tool dirs out of git
├── data/
│   ├── tools/       one JSON record per tool, plus manifest.json (the file list)
│   └── people/      one JSON record per person, plus manifest.json
├── docs/            RECORD_FORMAT.md, the record fields
└── ci/              sync-records.py (checks records, updates manifests and the README rule list)
    └── hooks/       pre-commit (blocks secrets, runs the records check)
```
