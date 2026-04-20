#!/usr/bin/env bash
# update-ofdb-colors.sh
# =====================
# Clones (or updates) the open-filament-database repo and builds
# ofdb-colors.json using build-ofdb-colors.py.
#
# Usage
# -----
#   ./scripts/update-ofdb-colors.sh
#   ./scripts/update-ofdb-colors.sh --pretty
#   ./scripts/update-ofdb-colors.sh --output path/to/ofdb-colors.json
#
# Options
#   --pretty          Pretty-print the output JSON
#   --output <path>   Output file path (default: ofdb-colors.json)
#   --repo   <path>   Path to the local OFDB clone
#                     (default: /tmp/open-filament-database)
#   --no-update       Skip git pull if the repo already exists

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OFDB_URL="https://github.com/OpenFilamentCollective/open-filament-database.git"

# ── Defaults ──────────────────────────────────────────────────────────────────
REPO_PATH="/tmp/open-filament-database"
OUTPUT="ofdb-colors.json"
PRETTY=""
NO_UPDATE=false

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pretty)     PRETTY="--pretty"; shift ;;
        --output)     OUTPUT="$2"; shift 2 ;;
        --repo)       REPO_PATH="$2"; shift 2 ;;
        --no-update)  NO_UPDATE=true; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
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
echo "Building '$OUTPUT' ..."
python3 "$SCRIPT_DIR/build-ofdb-colors.py" "$REPO_PATH" --output "$OUTPUT" $PRETTY

echo "Done: $OUTPUT"
