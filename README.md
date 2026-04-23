# README

Utility scripts for SpoolFlux development.

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
