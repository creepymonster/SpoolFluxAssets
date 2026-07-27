#!/usr/bin/env bash
# update-orca-filaments.sh
# =========================
# Clones (or updates) the open-filament-database repo and builds OrcaSlicer
# filament preset JSON files using build-orca-filaments.py.
#
# Usage
# -----
#   ./update-orca-filaments.sh
#   ./update-orca-filaments.sh --interactive
#   ./update-orca-filaments.sh --brand Bambu --debug --seed 7
#   ./update-orca-filaments.sh --output-dir orca-bambu --brand "Bambu Lab"
#   ./update-orca-filaments.sh --compatible-printer "Snapmaker U1 (0.4 nozzle)"
#   ./update-orca-filaments.sh --bundle "Filament presets.orca_filament"
#
# Options
#   --output-dir <path>  Output directory (default: orca-filaments)
#   --bundle <path>      Also package generated JSON files into this
#                       .orca_filament file
#                       (default: <output-dir>/<output-dir-name>.orca_filament)
#   --no-bundle          Only write individual JSON files
#   --brand <name>      Only convert this manufacturer name or OFDB brand slug
#   --brands <names...> Only convert these manufacturer names or OFDB brand slugs
#   --materials <names...>
#                       Only convert these material folders, e.g. PLA PETG ABS
#   --interactive       Select brands and materials interactively
#   --debug             Convert only 10 random filaments after filtering
#   --seed <number>     Random seed for --debug sampling
#   --pretty            Pretty-print JSON with two spaces
#   --compatible-printer <name>
#                       Add a compatible OrcaSlicer printer name; repeatable
#   --orca-version <version>
#                       Version string written to preset JSON files
#                       (default: 2.3.2.60)
#   --repo <path>       Path to the local OFDB clone
#                       (default: /tmp/open-filament-database)
#   --no-update         Skip git pull if the repo already exists

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OFDB_URL="https://github.com/OpenFilamentCollective/open-filament-database.git"

# ── Defaults ──────────────────────────────────────────────────────────────────
REPO_PATH="/tmp/open-filament-database"
OUTPUT_DIR="orca-filaments"
BUNDLE_PATH=""
NO_BUNDLE=false
BRAND=""
BRANDS=()
MATERIALS=()
INTERACTIVE=false
DEBUG=false
SEED=""
PRETTY=false
COMPATIBLE_PRINTERS=()
HAS_COMPATIBLE_PRINTERS=false
ORCA_VERSION="2.3.2.60"
NO_UPDATE=false

usage() {
    sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
}

require_value() {
    local option="$1"
    local value="${2:-}"
    if [[ -z "$value" || "$value" == --* ]]; then
        echo "Missing value for $option" >&2
        exit 1
    fi
}

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir)
            require_value "$1" "${2:-}"
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --brand)
            require_value "$1" "${2:-}"
            BRAND="$2"
            shift 2
            ;;
        --brands)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                BRANDS+=("$1")
                shift
            done
            if [[ ${#BRANDS[@]} -eq 0 ]]; then
                echo "Missing value for --brands" >&2
                exit 1
            fi
            ;;
        --materials)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                MATERIALS+=("$1")
                shift
            done
            if [[ ${#MATERIALS[@]} -eq 0 ]]; then
                echo "Missing value for --materials" >&2
                exit 1
            fi
            ;;
        --interactive)
            INTERACTIVE=true
            shift
            ;;
        --bundle)
            require_value "$1" "${2:-}"
            BUNDLE_PATH="$2"
            shift 2
            ;;
        --no-bundle)
            NO_BUNDLE=true
            shift
            ;;
        --debug)
            DEBUG=true
            shift
            ;;
        --seed)
            require_value "$1" "${2:-}"
            SEED="$2"
            shift 2
            ;;
        --pretty)
            PRETTY=true
            shift
            ;;
        --compatible-printer)
            require_value "$1" "${2:-}"
            COMPATIBLE_PRINTERS+=("$2")
            HAS_COMPATIBLE_PRINTERS=true
            shift 2
            ;;
        --orca-version)
            require_value "$1" "${2:-}"
            ORCA_VERSION="$2"
            shift 2
            ;;
        --repo)
            require_value "$1" "${2:-}"
            REPO_PATH="$2"
            shift 2
            ;;
        --no-update)
            NO_UPDATE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Run '$0 --help' for usage." >&2
            exit 1
            ;;
    esac
done

# ── Clone or update ───────────────────────────────────────────────────────────
if [[ -d "$REPO_PATH/.git" ]]; then
    if [[ "$NO_UPDATE" == false ]]; then
        echo "Updating OFDB repo at '$REPO_PATH' ..."
        git -C "$REPO_PATH" pull --ff-only
    else
        echo "Using existing OFDB repo at '$REPO_PATH' (--no-update)"
    fi
else
    echo "Cloning OFDB repo to '$REPO_PATH' ..."
    git clone --depth 1 "$OFDB_URL" "$REPO_PATH"
fi

# ── Build ─────────────────────────────────────────────────────────────────────
args=("$REPO_PATH" "--output-dir" "$OUTPUT_DIR")

if [[ -n "$BRAND" ]]; then
    args+=("--brand" "$BRAND")
fi
if [[ ${#BRANDS[@]} -gt 0 ]]; then
    args+=("--brands")
    for brand in "${BRANDS[@]}"; do
        args+=("$brand")
    done
fi
if [[ ${#MATERIALS[@]} -gt 0 ]]; then
    args+=("--materials")
    for material in "${MATERIALS[@]}"; do
        args+=("$material")
    done
fi
if [[ "$INTERACTIVE" == true ]]; then
    args+=("--interactive")
fi
if [[ "$NO_BUNDLE" == true ]]; then
    args+=("--no-bundle")
elif [[ -n "$BUNDLE_PATH" ]]; then
    args+=("--bundle" "$BUNDLE_PATH")
fi
if [[ "$DEBUG" == true ]]; then
    args+=("--debug")
fi
if [[ -n "$SEED" ]]; then
    args+=("--seed" "$SEED")
fi
if [[ "$PRETTY" == true ]]; then
    args+=("--pretty")
fi
if [[ "$HAS_COMPATIBLE_PRINTERS" == true ]]; then
    for printer in "${COMPATIBLE_PRINTERS[@]}"; do
        args+=("--compatible-printer" "$printer")
    done
fi
args+=("--orca-version" "$ORCA_VERSION")

echo "Building OrcaSlicer filament presets in '$OUTPUT_DIR' ..."
python3 "$SCRIPT_DIR/build-orca-filaments.py" "${args[@]}"

echo "Done: $OUTPUT_DIR"
