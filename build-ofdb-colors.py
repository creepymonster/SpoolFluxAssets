#!/usr/bin/env python3
"""
build-ofdb-colors.py
====================
Builds a JSON file from a locally cloned open-filament-database repository.
The output format mirrors the official all.json release (brands / materials /
filaments / variants / sizes arrays with UUID foreign keys), but preserves
color_hex as an array for multi-color variants — something the current
all.json releases do not yet support.

Usage
-----
    python3 scripts/build-ofdb-colors.py /path/to/open-filament-database
    python3 scripts/build-ofdb-colors.py /path/to/open-filament-database -o my-colors.json

The output file defaults to ofdb-colors.json in the current directory.

License note
------------
The Open Filament Database is MIT-licensed.
When distributing the generated file include its copyright notice:
  https://github.com/OpenFilamentCollective/open-filament-database/blob/main/LICENSE
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ── Deterministic UUID namespace ──────────────────────────────────────────────
# A fixed, project-specific namespace so that the same slug path always
# produces the same UUID across script runs.  IDs are therefore stable
# without requiring a separate ID-store file.
_NS = uuid.UUID("b7e9f2a1-4c3d-5e6f-8a9b-0c1d2e3f4a5b")


def _uid(path: str) -> str:
    """Return a deterministic UUID-v5 string for a slug path."""
    return str(uuid.uuid5(_NS, path))


# ── JSON helpers ──────────────────────────────────────────────────────────────

def _load(path: Path) -> dict | list | None:
    """Load a JSON file; return None on error (missing / malformed)."""
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _norm_hex(value: str | list | None) -> str | list[str] | None:
    """
    Normalise color_hex to match the official all.json format.

    Single colour  → "#RRGGBB"  (string, with '#' prefix)
    Multi-colour   → ["#RRGGBB", "#RRGGBB", ...]  (list of strings with '#')

    Values that are already prefixed are left unchanged; values without '#'
    have it added.  Empty / invalid values are dropped.
    """
    if value is None:
        return None
    if isinstance(value, list):
        cleaned = [
            v if v.startswith("#") else f"#{v}"
            for v in value
            if isinstance(v, str) and v.strip()
        ]
        return cleaned if cleaned else None
    if isinstance(value, str) and value.strip():
        v = value.strip()
        return v if v.startswith("#") else f"#{v}"
    return None


# ── Crawler ───────────────────────────────────────────────────────────────────

def crawl(repo_root: Path) -> dict:
    """
    Walk repo_root/data/ and build the all.json-compatible dictionary.

    Returns
    -------
    dict with keys: brands, materials, filaments, variants, sizes
    """
    data_dir = repo_root / "data"
    if not data_dir.is_dir():
        sys.exit(f"Error: 'data' directory not found inside '{repo_root}'")

    brands: list[dict] = []
    materials: list[dict] = []
    filaments: list[dict] = []
    variants: list[dict] = []
    sizes: list[dict] = []

    brand_dirs = sorted(p for p in data_dir.iterdir() if p.is_dir())

    for brand_dir in brand_dirs:
        brand_slug = brand_dir.name

        # ── brand ──────────────────────────────────────────────────────────
        brand_json = _load(brand_dir / "brand.json") or {}
        brand_id = _uid(f"brand:{brand_slug}")

        brands.append({
            "id":        brand_id,
            "slug":      brand_slug,
            "name":      brand_json.get("name", brand_slug),
            "website":   brand_json.get("website"),
            "logo_name": brand_json.get("logo"),
            "origin":    brand_json.get("origin"),
            "source":    brand_json.get("source"),
        })

        material_dirs = sorted(p for p in brand_dir.iterdir() if p.is_dir())

        for material_dir in material_dirs:
            material_type = material_dir.name  # e.g. "PLA", "PETG"
            material_slug = material_type.lower()

            # ── material ────────────────────────────────────────────────────
            mat_json = _load(material_dir / "material.json") or {}
            material_id = _uid(f"material:{brand_slug}:{material_slug}")

            # material.json only contains {"material": "PLA"} – use dir name
            # as canonical type value.
            materials.append({
                "id":             material_id,
                "brand_id":       brand_id,
                "slug":           material_slug,
                "material":       mat_json.get("material", material_type),
                "material_class": "FFF",
            })

            filament_dirs = sorted(p for p in material_dir.iterdir() if p.is_dir())

            for filament_dir in filament_dirs:
                filament_slug = filament_dir.name

                # ── filament ─────────────────────────────────────────────────
                fil_json = _load(filament_dir / "filament.json") or {}
                filament_id = _uid(f"filament:{brand_slug}:{material_slug}:{filament_slug}")

                filaments.append({
                    "id":                   filament_id,
                    "brand_id":             brand_id,
                    "material_id":          material_id,
                    "slug":                 filament_slug,
                    "name":                 fil_json.get("name", filament_slug),
                    "density":              fil_json.get("density"),
                    "diameter_tolerance":   fil_json.get("diameter_tolerance"),
                    "min_print_temperature": fil_json.get("min_print_temperature"),
                    "max_print_temperature": fil_json.get("max_print_temperature"),
                    "min_bed_temperature":   fil_json.get("min_bed_temperature"),
                    "max_bed_temperature":   fil_json.get("max_bed_temperature"),
                    "discontinued":         fil_json.get("discontinued", False),
                    "slicer_settings":      fil_json.get("slicer_settings"),
                    "data_sheet_url":       fil_json.get("data_sheet_url"),
                    "safety_sheet_url":     fil_json.get("safety_sheet_url"),
                })

                variant_dirs = sorted(p for p in filament_dir.iterdir() if p.is_dir())

                for variant_dir in variant_dirs:
                    variant_slug = variant_dir.name

                    # ── variant ──────────────────────────────────────────────
                    var_json = _load(variant_dir / "variant.json") or {}
                    variant_id = _uid(
                        f"variant:{brand_slug}:{material_slug}:{filament_slug}:{variant_slug}"
                    )

                    raw_hex = var_json.get("color_hex")
                    color_hex = _norm_hex(raw_hex)

                    variants.append({
                        "id":           variant_id,
                        "filament_id":  filament_id,
                        "slug":         variant_slug,
                        "name":         var_json.get("name", variant_slug),
                        # color_hex: string for single colour, list for multi-colour.
                        # The official all.json always uses a string here; this script
                        # preserves the array so SpoolFlux can import multi-colour data.
                        # When OFDB releases native array support, the format is already
                        # compatible.
                        "color_hex":    color_hex,
                        "hex_variants": var_json.get("hex_variants"),
                        "traits":       var_json.get("traits"),
                        "discontinued": var_json.get("discontinued", False),
                        # Colour standard designations (optional)
                        "ral":          var_json.get("ral"),
                        "ncs":          var_json.get("ncs"),
                        "pantone":      var_json.get("pantone"),
                    })

                    # ── sizes ─────────────────────────────────────────────────
                    sizes_raw = _load(variant_dir / "sizes.json")
                    if isinstance(sizes_raw, list):
                        for idx, sz in enumerate(sizes_raw):
                            if not isinstance(sz, dict):
                                continue
                            size_id = _uid(
                                f"size:{brand_slug}:{material_slug}:{filament_slug}:{variant_slug}:{idx}"
                            )
                            sizes.append({
                                "id":                size_id,
                                "variant_id":        variant_id,
                                "filament_weight":   sz.get("filament_weight"),
                                "diameter":          sz.get("diameter"),
                                "empty_spool_weight": sz.get("empty_spool_weight"),
                                "spool_core_diameter": sz.get("spool_core_diameter"),
                                "spool_refill":      sz.get("spool_refill", False),
                                "gtin":              sz.get("gtin") or sz.get("ean"),
                                "article_number":    sz.get("article_number"),
                                "discontinued":      sz.get("discontinued", False),
                            })

    return {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source":      "https://github.com/OpenFilamentCollective/open-filament-database",
        "license":     "https://github.com/OpenFilamentCollective/open-filament-database/blob/main/LICENSE",
        "brands":    brands,
        "materials": materials,
        "filaments": filaments,
        "variants":  variants,
        "sizes":     sizes,
    }


# ── Statistics ────────────────────────────────────────────────────────────────

def _stats(db: dict) -> None:
    multi = sum(1 for v in db["variants"] if isinstance(v["color_hex"], list))
    print(f"  brands:    {len(db['brands'])}")
    print(f"  materials: {len(db['materials'])}")
    print(f"  filaments: {len(db['filaments'])}")
    print(f"  variants:  {len(db['variants'])}  ({multi} with multi-color arrays)")
    print(f"  sizes:     {len(db['sizes'])}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build an all.json-compatible color file from a cloned OFDB repo."
    )
    parser.add_argument(
        "repo",
        type=Path,
        help="Path to the root of the cloned open-filament-database repository",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("ofdb-colors.json"),
        help="Output file path (default: ofdb-colors.json)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=False,
        help="Pretty-print the JSON output (larger file, easier to inspect)",
    )
    args = parser.parse_args()

    if not args.repo.is_dir():
        sys.exit(f"Error: '{args.repo}' is not a directory")

    print(f"Crawling '{args.repo}' ...")
    db = crawl(args.repo)

    print("Result:")
    _stats(db)

    indent = 2 if args.pretty else None
    separators = None if args.pretty else (",", ":")

    print(f"Writing '{args.output}' ...")
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=indent, separators=separators)

    size_kb = args.output.stat().st_size / 1024
    print(f"Done. File size: {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
