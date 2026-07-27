# README

Asset builders and update scripts for SpoolFlux filament data.

---

## build-ofdb-colors.py

Builds an `ofdb-colors.json` from a **locally cloned** [open-filament-database](https://github.com/OpenFilamentCollective/open-filament-database) repository.

The output format mirrors the official `all.json` release (flat `brands` / `materials` / `filaments` / `variants` / `sizes` arrays with UUID foreign keys), with one enhancement: **`color_hex` is preserved as an array for multi-color variants** — something the current `all.json` releases do not yet support. Once official releases add array support, only the download URL in the app needs updating; the format is already compatible.

UUIDs are deterministic (uuid5, path-based), so the same repo content always produces the same IDs across runs.

**Requirements:** Python 3.10+, no external packages.

```bash
python3 build-ofdb-colors.py /path/to/open-filament-database
```

| Option | Default | Description |
|--------|---------|-------------|
| `-o`, `--output <path>` | `ofdb-colors.json` | Output file path |
| `--pretty` | off | Pretty-print JSON (larger, easier to inspect) |

---

## build-orca-filaments.py

Builds individual OrcaSlicer filament preset `.json` files from a **locally cloned** Open Filament Database repository. Each active OFDB `filament.json` becomes one importable Orca filament preset; color variants and spool sizes are intentionally ignored.

**Requirements:** Python 3.10+, no external packages.

```bash
python3 build-orca-filaments.py /path/to/open-filament-database

# Only one manufacturer
python3 build-orca-filaments.py /path/to/open-filament-database --brand Polymaker

# Write 10 random presets for inspection
python3 build-orca-filaments.py /path/to/open-filament-database --debug --seed 42

# Restrict imported profiles to an OrcaSlicer printer profile
python3 build-orca-filaments.py /path/to/open-filament-database --compatible-printer "Snapmaker U1 (0.4 nozzle)"

# Also create one importable OrcaSlicer filament bundle
python3 build-orca-filaments.py /path/to/open-filament-database --bundle "Filament presets.orca_filament"
```

| Option | Default | Description |
|--------|---------|-------------|
| `-o`, `--output-dir <path>` | `orca-filaments` | Output directory for OrcaSlicer preset JSON files |
| `--bundle <path>` | `<output-dir>/<output-dir-name>.orca_filament` | Package generated JSON files into one importable `.orca_filament` file |
| `--no-bundle` | off | Only write individual JSON files |
| `-b`, `--brand <name>` | all brands | Only convert this manufacturer name or OFDB brand slug |
| `--debug` | off | Convert only 10 random filaments after filtering |
| `--seed <number>` | random | Deterministic random sample for `--debug` |
| `--pretty` | off | Pretty-print JSON with two spaces instead of Orca-style tabs |
| `--compatible-printer <name>` | none | Add a compatible OrcaSlicer printer name; repeat for multiple printers |
| `--orca-version <version>` | `2.3.2.60` | Version string written to importable OrcaSlicer preset JSON files |

Import the generated `.orca_filament` bundle in OrcaSlicer via **File → Import → Import Configs...**.

---

## update-orca-filaments.sh

Convenience wrapper that **clones or updates** the OFDB repo and then runs `build-orca-filaments.py`.

```bash
# Clone/update + build all Orca filament presets
./update-orca-filaments.sh

# Only one manufacturer, with 10 random files for inspection
./update-orca-filaments.sh --brand Bambu --debug --seed 7

# Interactive multi-select for brands and materials
./update-orca-filaments.sh --interactive

# Non-interactive multi-select
./update-orca-filaments.sh --brands bambu_lab rosa3d_filaments --materials PLA PETG

# Custom output directory
./update-orca-filaments.sh --brand "Bambu Lab" --output-dir orca-bambu

# Bind presets to a printer profile known to OrcaSlicer
./update-orca-filaments.sh --compatible-printer "Snapmaker U1 (0.4 nozzle)"

# Create one importable bundle like OrcaSlicer's export does
./update-orca-filaments.sh --brand Bambu --bundle "Bambu filament presets.orca_filament"

# Only write individual JSON files, without a bundle
./update-orca-filaments.sh --brand Bambu --no-bundle

# Use an existing local clone without pulling
./update-orca-filaments.sh --repo /tmp/open-filament-database --no-update
```

| Option | Default | Description |
|--------|---------|-------------|
| `--output-dir <path>` | `orca-filaments` | Output directory for OrcaSlicer preset JSON files |
| `--bundle <path>` | `<output-dir>/<output-dir-name>.orca_filament` | Package generated JSON files into one importable `.orca_filament` file |
| `--no-bundle` | off | Only write individual JSON files |
| `--brand <name>` | all brands | Only convert this manufacturer name or OFDB brand slug |
| `--brands <names...>` | all brands | Only convert these manufacturer names or OFDB brand slugs |
| `--materials <names...>` | all materials | Only convert these OFDB material folders, e.g. `PLA PETG ABS` |
| `--interactive` | off | Select brands and materials with terminal checkbox lists |
| `--debug` | off | Convert only 10 random filaments after filtering |
| `--seed <number>` | random | Deterministic random sample for `--debug` |
| `--pretty` | off | Pretty-print JSON with two spaces |
| `--compatible-printer <name>` | none | Add a compatible OrcaSlicer printer name; repeat for multiple printers |
| `--orca-version <version>` | `2.3.2.60` | Version string written to preset JSON files |
| `--repo <path>` | `/tmp/open-filament-database` | Path to local OFDB clone |
| `--no-update` | off | Skip `git pull` if repo already exists |

Interactive mode uses the cursor keys to move, Space to toggle a checkbox, `a` to select all, `n` to select none, and Enter to confirm.

---

## update-ofdb-colors.sh

Convenience wrapper that **clones or updates** the OFDB repo and then runs `build-ofdb-colors.py`.

```bash
# Clone + build (default output: ofdb-colors.json)
./update-ofdb-colors.sh

# Custom output path
./update-ofdb-colors.sh --output SpoolFlux/Resources/ofdb-colors.json

# Pretty-printed (for manual inspection)
./update-ofdb-colors.sh --pretty

# Skip git pull if the repo already exists locally
./update-ofdb-colors.sh --no-update

# Use an existing local clone instead of /tmp/open-filament-database
./update-ofdb-colors.sh --repo ~/code/open-filament-database
```

| Option | Default | Description |
|--------|---------|-------------|
| `--output <path>` | `ofdb-colors.json` | Output file path |
| `--repo <path>` | `/tmp/open-filament-database` | Path to local OFDB clone |
| `--pretty` | off | Pretty-print JSON output |
| `--no-update` | off | Skip `git pull` if repo already exists |

The repo is cloned with `--depth 1` (no history) for speed.

---

## build-filament-colors.py

Fetches all swatch data from the [filamentcolors.xyz](https://filamentcolors.xyz) API and writes `filament_colors.json`. All pages are retrieved automatically via the `next` pagination field.

**Requirements:** Python 3.10+, no external packages.

```bash
python3 build-filament-colors.py
```

| Option | Default | Description |
|--------|---------|-------------|
| `-o`, `--output <path>` | `filament_colors.json` | Output file path |
| `--pretty` | off | Pretty-print JSON (larger, easier to inspect) |

Output structure:

```json
{
  "generatedAt": "2026-04-18T10:00:00Z",
  "source": "https://filamentcolors.xyz/api/swatch/",
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "swatches": [
    {
      "brand":        "Bambu Lab",
      "filamentName": "PLA Basic",
      "variantName":  "Bambu Green",
      "colorHex":     "3EAB47",
      "td":           0.42,
      "type":         "PLA"
    }
  ]
}
```

Field mapping from the API:

| API field | JSON field |
|-----------|------------|
| `manufacturer` | `brand` |
| `filament_type.name` | `filamentName` |
| `color_name` | `variantName` |
| `hex_color` | `colorHex` |
| `td` | `td` |
| `filament_type.parent_type.name` | `type` |

---

## License note

Data published by [Open Filament Database](https://api.openfilamentdatabase.org) is [MIT-licensed](https://github.com/OpenFilamentCollective/open-filament-database/blob/main/LICENSE). When distributing the generated `ofdb-colors.json`, include its copyright notice.

Data published by [filamentcolors.xyz](https://filamentcolors.xyz) is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). When distributing the generated `filament_colors.json`, include attribution.
