# library-tools

The single home of tool details (author, organisation, year, language, the "why notable" story, links). Sites fetch these records and each shows only the ones that list it in `show_on`:

- `portfolio` - the Toolkit page on `fmfalgun.github.io` (tools outside the VAPT list)
- `vapt` - the VAPT Toolkit page in the [library](https://github.com/fmfalgun/library) repo

Records are served by GitHub Pages at `https://fmfalgun.github.io/library-tools/data/<file>.json`; the list of files is `data/manifest.json`. Record fields and how to add a tool: [`docs/RECORD_FORMAT.md`](docs/RECORD_FORMAT.md).

## Record rules

Every record must follow these rules; `ci/sync-records.py` checks them on every commit, so a record that breaks one cannot be committed.

<!-- rules:start (generated from docs/RECORD_FORMAT.md by ci/sync-records.py; do not edit) -->
- **R1 File name.** One record per file in `data/`, named lowercase-with-dashes ending in `.json` (`theharvester.json`).
- **R2 Valid record.** The file is valid JSON and has a non-empty `name`.
- **R3 Sites.** `show_on` is a list that uses only known sites: `"portfolio"`, `"vapt"`. An empty list keeps the record stored but shown nowhere.
- **R4 Category.** A record shown on `portfolio` has a `category`.
- **R5 Manifest.** `data/manifest.json` lists exactly the record files and is maintained by the check; never edit it by hand. It may not list a file that does not exist.
<!-- rules:end -->

## Directory structure

```
library-tools/
├── README.md        repo details and structure
├── .gitignore       keeps keys, env files and local tool dirs out of git
├── data/            one JSON record per tool, plus manifest.json (the file list)
├── docs/            RECORD_FORMAT.md, the record fields
└── ci/              sync-records.py (checks records, updates the manifest and README rule list)
    └── hooks/       pre-commit (blocks secrets, runs the records check)
```
