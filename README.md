# library-tools

The single home of tool details (author, organisation, year, language, the "why notable" story, links). Sites fetch these records and each shows only the ones that list it in `show_on`:

- `portfolio` - the Toolkit page on `fmfalgun.github.io` (tools outside the VAPT list)
- `vapt` - the VAPT Toolkit page in the [library](https://github.com/fmfalgun/library) repo

Records are served by GitHub Pages at `https://fmfalgun.github.io/library-tools/data/<file>.json`; the list of files is `data/manifest.json`. Record fields and how to add a tool: [`docs/RECORD_FORMAT.md`](docs/RECORD_FORMAT.md).

## Directory structure

```
library-tools/
├── README.md        repo details and structure
├── .gitignore       keeps keys, env files and local tool dirs out of git
├── data/            one JSON record per tool, plus manifest.json (the file list)
├── docs/            RECORD_FORMAT.md, the record fields
└── ci/              sync-records.py (checks records, updates the manifest)
    └── hooks/       pre-commit (blocks secrets, runs the records check)
```
