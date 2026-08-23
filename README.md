# Bootstrap Shorts Project

CLI that starts a new After Effects short-form project from two templates:

- `portrait-short-form`
- `portrait-short-form-pre-process`

Python (managed with [uv](https://docs.astral.sh/uv/)) prepares the project folder and copies footage. ExtendScript then drives After Effects: save both projects, import clips into the expected Project panel folders, and relink any existing template footage into `(Footage)/`.

Native **File → Dependencies → Collect Files** is not scriptable. This tool copies and relinks footage directly into the new project root instead of creating a temporary `<name>-deps` folder.

## Resulting layout

```text
<projects>/<name>/
  <name>.aep
  <name>-pre-process.aep
  (Footage)/
    01-footage/
      clip-a.mov
      clip-b.mov
  .bootstrap/
    job.json
    result.json
```

## Requirements

- Windows 10
- [uv](https://docs.astral.sh/uv/)
- Python 3.11+ (uv will install it if needed)
- Adobe After Effects with both template `.aep` files
- In After Effects: **Preferences → Scripting & Expressions → Allow Scripts to Write Files and Access Network**

## Install

From the repository root:

```powershell
uv sync --group dev
```

This creates `.venv`, installs runtime and test dependencies, and writes `uv.lock` as needed.

## Config

Copy [config.example.yaml](config.example.yaml) to `config.yaml` (gitignored) and fill in local paths:

```yaml
templates:
  main: "E:/path/to/portrait-short-form"
  pre_process: "E:/path/to/portrait-short-form-pre-process"
raw_footage: "E:/path/to/raw-footage"
projects: "E:/path/to/projects"
name: "client-short-01"

after_effects_exe: null

templates_map:
  main: "portrait-short-form.aep"
  pre_process: "portrait-short-form-pre-process.aep"

project_folders:
  main_import: "01-footage"
  preprocess_import: "footage"
```

| Key | Required | Meaning |
|---|---|---|
| `templates.main` | yes | Directory or `.aep` file for `portrait-short-form` |
| `templates.pre_process` | yes | Directory or `.aep` file for `portrait-short-form-pre-process` |
| `raw_footage` | yes | Directory of source clips. Only top-level `.mov` files are collected |
| `projects` | yes | Parent directory where the new project folder is created |
| `name` | yes | New project folder and `.aep` name (single path segment) |
| `after_effects_exe` | no | Full path to `AfterFX.exe`. If `null`, the newest install under Program Files is used |
| `templates_map` | no | `.aep` filenames used when a `templates.*` path is a directory |
| `project_folders` | no | After Effects Project panel folder names for imports |

Relative paths are resolved against the config file's directory.

### Template folder contract

The templates must already contain (or will get) these Project panel folders:

- `01-footage` in `portrait-short-form` — raw clips are imported here
- `footage` in `portrait-short-form-pre-process` — the same clips are imported here

On disk, raw clips always land in `(Footage)/<main_import>/`, which defaults to `(Footage)/01-footage/`.

To use different template folders or panel names later, change `templates`, `templates_map`, and `project_folders`. No code change is required. Each `templates.*` value may be a directory (joined with `templates_map`) or a direct path to an `.aep` file.

## Run

```powershell
uv run bootstrap-shorts
uv run bootstrap-shorts --config config.yaml
uv run bootstrap-shorts --name other-short --raw-footage E:\clips\session-01
uv run bootstrap-shorts --force
```

CLI flags override the config file:

| Flag | Purpose |
|---|---|
| `--config` / `-c` | YAML config path (default `config.yaml`) |
| `--name` | Override `name` |
| `--raw-footage` | Override the `raw_footage` directory |
| `--force` | Delete and replace an existing `projects/<name>` folder |
| `--timeout` | Seconds to wait for After Effects (default `600`) |

## What happens

1. Validate the config. Fail if templates, the raw footage directory, or the projects parent directory are missing.
2. Collect every top-level `.mov` file in `raw_footage` into an in-process list (`.mp4` and other types are ignored). Fail if none are found.
3. Refuse to continue if `projects/<name>` already exists, unless `--force`.
4. Create `projects/<name>/(Footage)/01-footage/` and copy the discovered `.mov` files there.
5. Write `.bootstrap/job.json` with absolute paths.
6. Launch `AfterFX.exe -s` once. The script:
   - opens the main template and saves it as `<name>.aep`
   - imports the copied files into `01-footage`
   - copies any other template `FileSource` footage into `(Footage)/<panel-folder>/` and relinks it
   - opens the pre-process template and saves it as `<name>-pre-process.aep`
   - imports the same files into `footage`
7. Python reads `.bootstrap/result.json` and exits non-zero if After Effects reported errors.

After Effects is left running. The launcher does not pass `-project` together with the script (that combination is unreliable).

## Failures

| Situation | Result |
|---|---|
| Missing `config.yaml` or invalid YAML | CLI error |
| Unknown config key | CLI error (`extra: forbid`) |
| Missing template `.aep` | CLI error |
| Missing raw footage directory | CLI error |
| No `.mov` files in `raw_footage` | CLI error |
| Duplicate footage filenames | CLI error |
| `projects/<name>` already exists | CLI error; pass `--force` to replace |
| `AfterFX.exe` not found | CLI error; set `after_effects_exe` |
| After Effects never writes `result.json` | Timeout; enable script file access in Preferences |
| Import or save error inside AE | `result.json` `ok: false` and a CLI error |

## Known limits

- Fonts are not collected. Install required fonts on the machine.
- Layered Photoshop / Illustrator sources may not relink per layer. Those items are skipped with a warning.
- Cinema 4D and some plugin-owned files are not collected.
- Image sequences are imported as single files unless you add sequence handling later.

## Development

```powershell
uv sync --group dev
uv run pytest
uv run ruff check src tests
```

Unit tests cover config validation, footage copy / `job.json` shape, and AfterFX discovery. They do not launch After Effects.

## Project layout

```text
src/bootstrap_shorts/    Python CLI, config, filesystem, AE launcher
scripts/ae/              ExtendScript helpers and job runner
config.example.yaml      Documented config template
tests/                   Unit tests (no live After Effects)
```
