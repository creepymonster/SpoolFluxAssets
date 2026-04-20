#!/usr/bin/env python3
"""
build-filament-colors.py
========================
Fetches all swatch data from filamentcolors.xyz and writes filament_colors.json.

Usage
-----
    python3 fetch-filament-colors.py
    python3 fetch-filament-colors.py -o my-colors.json
    python3 fetch-filament-colors.py --pretty

Options
-------
    -o / --output <path>   Output file (default: filament_colors.json)
    --pretty               Pretty-print the JSON output
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

START_URL = "https://filamentcolors.xyz/api/swatch/?format=json&page_size=100"
SOURCE    = "https://filamentcolors.xyz/api/swatch/"


def fetch_all() -> list[dict]:
    records = []
    url: str | None = START_URL
    page = 1
    while url:
        print(f"  Page {page}: {url}", flush=True)
        req = urllib.request.Request(url, headers={"User-Agent": "SpoolFluxAssets/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        records.extend(data.get("results", []))
        url = data.get("next")
        page += 1
    return records


def map_swatch(s: dict) -> dict:
    ft     = s.get("filament_type") or {}
    parent = ft.get("parent_type") or {}
    return {
        "brand":        (s.get("manufacturer") or {}).get("name"),
        "filamentName": ft.get("name"),
        "variantName":  s.get("color_name"),
        "colorHex":     s.get("hex_color"),
        "td":           s.get("td"),
        "type":         parent.get("name"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch all swatch data from filamentcolors.xyz and write filament_colors.json."
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("filament_colors.json"),
        help="Output file path (default: filament_colors.json)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output",
    )
    args = parser.parse_args()

    print("Fetching swatches from filamentcolors.xyz ...")
    raw = fetch_all()
    print(f"  Total records fetched: {len(raw)}")

    output = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source":      SOURCE,
        "license":     "https://creativecommons.org/licenses/by/4.0/",
        "swatches":    [map_swatch(s) for s in raw],
    }

    indent     = 2    if args.pretty else None
    separators = None if args.pretty else (",", ":")

    print(f"Writing '{args.output}' ...")
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=indent, separators=separators)

    size_kb = args.output.stat().st_size / 1024
    print(f"Done. File size: {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
