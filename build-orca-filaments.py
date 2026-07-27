#!/usr/bin/env python3
from __future__ import annotations

"""
build-orca-filaments.py
=======================
Builds OrcaSlicer-compatible filament preset JSON files from a locally cloned
open-filament-database repository.

Usage
-----
    python3 build-orca-filaments.py /path/to/open-filament-database
    python3 build-orca-filaments.py /path/to/open-filament-database --brand Polymaker
    python3 build-orca-filaments.py /path/to/open-filament-database --brands Bambu Polymaker
    python3 build-orca-filaments.py /path/to/open-filament-database --materials PLA PETG
    python3 build-orca-filaments.py /path/to/open-filament-database --debug
    python3 build-orca-filaments.py /path/to/open-filament-database --compatible-printer "Snapmaker U1 (0.4 nozzle)"
    python3 build-orca-filaments.py /path/to/open-filament-database --bundle "Filament presets.orca_filament"

The output directory defaults to orca-filaments in the current directory.

License note
------------
The Open Filament Database is MIT-licensed.
When distributing generated presets include its copyright notice:
  https://github.com/OpenFilamentCollective/open-filament-database/blob/main/LICENSE
"""

import argparse
import curses
import hashlib
import json
import random
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


GENERIC_INHERITS = {
    "ABS": "Generic ABS @System",
    "ASA": "Generic ASA @System",
    "HIPS": "Generic HIPS @System",
    "PA": "Generic PA @System",
    "PA-CF": "Generic PA-CF @System",
    "PC": "Generic PC @System",
    "PET": "Generic PET @System",
    "PETG": "Generic PETG @System",
    "PLA": "Generic PLA @System",
    "PLA-CF": "Generic PLA-CF @System",
    "PVA": "Generic PVA @System",
    "TPU": "Generic TPU @System",
}


@dataclass(frozen=True)
class FilamentPreset:
    brand_name: str
    brand_slug: str
    material: str
    filament_name: str
    filament_slug: str
    density: float | int | None
    min_print_temperature: int | float | None
    max_print_temperature: int | float | None
    min_bed_temperature: int | float | None
    max_bed_temperature: int | float | None


def _load(path: Path) -> dict[str, Any] | list[Any] | None:
    """Load a JSON file; return None on error (missing / malformed)."""
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _brand_options(repo_root: Path) -> list[tuple[str, str]]:
    data_dir = repo_root / "data"
    options: list[tuple[str, str]] = []
    for brand_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        brand_slug = brand_dir.name
        brand_json = _load(brand_dir / "brand.json") or {}
        brand_name = str(brand_json.get("name") or brand_slug)
        options.append((f"{brand_name} ({brand_slug})", brand_slug))
    return options


def _material_options(repo_root: Path, brand_slugs: list[str]) -> list[tuple[str, str]]:
    data_dir = repo_root / "data"
    material_names: set[str] = set()
    brand_dirs = [data_dir / slug for slug in brand_slugs] if brand_slugs else sorted(
        p for p in data_dir.iterdir() if p.is_dir()
    )
    for brand_dir in brand_dirs:
        if not brand_dir.is_dir():
            continue
        for material_dir in sorted(p for p in brand_dir.iterdir() if p.is_dir()):
            material_names.add(material_dir.name)
    return [(name, name) for name in sorted(material_names)]


def _curses_multiselect(stdscr: Any, title: str, options: list[tuple[str, str]]) -> list[str]:
    if not options:
        return []

    try:
        curses.curs_set(0)
    except curses.error:
        pass
    selected: set[int] = set()
    cursor = 0
    offset = 0

    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        list_height = max(1, height - 5)

        if cursor < offset:
            offset = cursor
        elif cursor >= offset + list_height:
            offset = cursor - list_height + 1

        stdscr.addnstr(0, 0, title, width - 1, curses.A_BOLD)
        stdscr.addnstr(
            1,
            0,
            "↑/↓ bewegen, Space wählen, a alle, n keine, Enter bestätigen",
            width - 1,
        )
        stdscr.addnstr(2, 0, f"Ausgewählt: {len(selected)}", width - 1)

        for screen_row, option_idx in enumerate(range(offset, min(len(options), offset + list_height)), start=4):
            label, _value = options[option_idx]
            marker = "[x]" if option_idx in selected else "[ ]"
            prefix = f"{marker} {label}"
            attr = curses.A_REVERSE if option_idx == cursor else curses.A_NORMAL
            stdscr.addnstr(screen_row, 0, prefix, width - 1, attr)

        if offset > 0:
            stdscr.addnstr(3, max(0, width - 12), "↑ mehr", 11)
        if offset + list_height < len(options):
            stdscr.addnstr(height - 1, max(0, width - 12), "↓ mehr", 11)

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = min(len(options) - 1, cursor + 1)
        elif key in (curses.KEY_NPAGE,):
            cursor = min(len(options) - 1, cursor + list_height)
        elif key in (curses.KEY_PPAGE,):
            cursor = max(0, cursor - list_height)
        elif key in (ord(" "),):
            if cursor in selected:
                selected.remove(cursor)
            else:
                selected.add(cursor)
        elif key in (ord("a"), ord("A")):
            selected = set(range(len(options)))
        elif key in (ord("n"), ord("N")):
            selected.clear()
        elif key in (10, 13, curses.KEY_ENTER):
            return [options[i][1] for i in sorted(selected)]
        elif key in (27, ord("q"), ord("Q")):
            raise KeyboardInterrupt


def interactive_filters(repo_root: Path) -> tuple[list[str], list[str]]:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        sys.exit("Error: --interactive requires a terminal")

    def run(stdscr: Any) -> tuple[list[str], list[str]]:
        brands = _curses_multiselect(
            stdscr,
            "Welche Brands sollen konvertiert werden? (keine Auswahl = alle)",
            _brand_options(repo_root),
        )
        materials = _curses_multiselect(
            stdscr,
            "Welche Materialien sollen konvertiert werden? (keine Auswahl = alle)",
            _material_options(repo_root, brands),
        )
        return brands, materials

    return curses.wrapper(run)


def _as_string_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    return [str(value)]


def _avg_temperature(min_value: Any, max_value: Any) -> int | None:
    values = [
        value
        for value in (min_value, max_value)
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    if not values:
        return None
    return int(round(sum(values) / len(values)))


def _norm_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _norm_filters(values: list[str] | None) -> set[str]:
    return {_norm_name(value) for value in values or [] if value.strip()}


def _safe_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:180] or "filament"


def _short_id(*parts: str, prefix: str) -> str:
    digest = hashlib.sha1("::".join(parts).encode("utf-8")).hexdigest().upper()
    return f"{prefix}{digest[:10]}"


def _material_key(material: str, filament_name: str) -> str:
    haystack = f"{material} {filament_name}".upper()
    if "PLA" in haystack and "CF" in haystack:
        return "PLA-CF"
    if "PA" in haystack and "CF" in haystack:
        return "PA-CF"
    if "PETG" in haystack:
        return "PETG"
    if "TPU" in haystack or "TPE" in haystack:
        return "TPU"
    for key in GENERIC_INHERITS:
        if key in haystack:
            return key
    return material.upper()


def _preset_name(item: FilamentPreset) -> str:
    pieces = [item.brand_name, item.filament_name]
    return " ".join(piece for piece in pieces if piece).strip()


def _preset_id(item: FilamentPreset) -> str:
    return _short_id(
        item.brand_slug,
        item.material,
        item.filament_slug,
        prefix="OFDB_",
    )


def _orca_profile(
    item: FilamentPreset,
    compatible_printers: list[str],
    orca_version: str,
) -> dict[str, Any]:
    material_key = _material_key(item.material, item.filament_name)
    name = _preset_name(item)

    profile: dict[str, Any] = {
        "version": orca_version,
        "name": name,
        "inherits": GENERIC_INHERITS.get(material_key, "Generic PLA @System"),
        "from": "User",
        "filament_settings_id": [name],
        "filament_extruder_variant": ["Direct Drive Standard"],
        "filament_vendor": [item.brand_name],
        "filament_type": [material_key],
    }
    if compatible_printers:
        profile["compatible_printers"] = compatible_printers

    nozzle_temp = _avg_temperature(
        item.min_print_temperature,
        item.max_print_temperature,
    )
    bed_temp = _avg_temperature(item.min_bed_temperature, item.max_bed_temperature)

    optional_fields = {
        "nozzle_temperature": nozzle_temp,
        "nozzle_temperature_initial_layer": nozzle_temp,
        "hot_plate_temp": bed_temp,
        "hot_plate_temp_initial_layer": bed_temp,
        "filament_density": item.density,
    }
    for key, value in optional_fields.items():
        values = _as_string_list(value)
        if values:
            profile[key] = values

    return profile


def crawl(
    repo_root: Path,
    brand_filters: list[str] | None = None,
    material_filters: list[str] | None = None,
) -> list[FilamentPreset]:
    data_dir = repo_root / "data"
    if not data_dir.is_dir():
        sys.exit(f"Error: 'data' directory not found inside '{repo_root}'")

    wanted_brands = _norm_filters(brand_filters)
    wanted_materials = _norm_filters(material_filters)
    presets: list[FilamentPreset] = []
    available_brands: list[str] = []
    available_materials: set[str] = set()

    for brand_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        brand_slug = brand_dir.name
        brand_json = _load(brand_dir / "brand.json") or {}
        brand_name = str(brand_json.get("name") or brand_slug)
        available_brands.append(brand_name)

        brand_slug_norm = _norm_name(brand_slug)
        brand_name_norm = _norm_name(brand_name)
        if wanted_brands and not any(
            wanted_brand in brand_slug_norm
            or wanted_brand in brand_name_norm
            or brand_slug_norm in wanted_brand
            or brand_name_norm in wanted_brand
            for wanted_brand in wanted_brands
        ):
            continue

        for material_dir in sorted(p for p in brand_dir.iterdir() if p.is_dir()):
            material = material_dir.name
            available_materials.add(material)
            material_norm = _norm_name(material)
            if wanted_materials and material_norm not in wanted_materials:
                continue

            for filament_dir in sorted(p for p in material_dir.iterdir() if p.is_dir()):
                filament_slug = filament_dir.name
                fil_json = _load(filament_dir / "filament.json") or {}
                if fil_json.get("discontinued", False):
                    continue

                filament_name = str(fil_json.get("name") or filament_slug)
                presets.append(FilamentPreset(
                    brand_name=brand_name,
                    brand_slug=brand_slug,
                    material=material,
                    filament_name=filament_name,
                    filament_slug=filament_slug,
                    density=fil_json.get("density"),
                    min_print_temperature=fil_json.get("min_print_temperature"),
                    max_print_temperature=fil_json.get("max_print_temperature"),
                    min_bed_temperature=fil_json.get("min_bed_temperature"),
                    max_bed_temperature=fil_json.get("max_bed_temperature"),
                ))

    if wanted_brands and not presets:
        wanted_label = ", ".join(brand_filters or [])
        close = [
            name for name in available_brands
            if any(wanted_brand in _norm_name(name) or _norm_name(name) in wanted_brand for wanted_brand in wanted_brands)
        ][:10]
        hint = f" Similar brands: {', '.join(close)}" if close else ""
        sys.exit(f"Error: no active filaments found for brand filter '{wanted_label}'.{hint}")

    if wanted_materials and not presets:
        wanted_label = ", ".join(material_filters or [])
        available_label = ", ".join(sorted(available_materials))
        hint = f" Available materials after brand filtering: {available_label}" if available_label else ""
        sys.exit(f"Error: no active filaments found for material filter '{wanted_label}'.{hint}")

    return presets


def write_presets(
    items: list[FilamentPreset],
    output_dir: Path,
    pretty: bool,
    compatible_printers: list[str],
    orca_version: str,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    used_names: set[str] = set()
    written: list[Path] = []
    indent = 2 if pretty else "\t"

    for item in items:
        profile = _orca_profile(item, compatible_printers, orca_version)
        filename = _safe_filename(f"{profile['name']}.json")
        if filename in used_names:
            stem = filename[:-5] if filename.endswith(".json") else filename
            filename = _safe_filename(f"{stem} {_preset_id(item)}.json")
        used_names.add(filename)

        path = output_dir / filename
        with path.open("w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=indent)
            f.write("\n")
        written.append(path)

    return written


def write_zip(paths: list[Path], zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in paths:
            info = zipfile.ZipInfo(path.name)
            # OrcaSlicer's own preset export writes FAT/MS-DOS style entries.
            # Matching that avoids macOS/Unix ZIP metadata confusing older import paths.
            info.create_system = 0
            info.external_attr = 0
            info.compress_type = zipfile.ZIP_DEFLATED
            info.date_time = (2026, 1, 1, 0, 0, 0)
            with path.open("rb") as f:
                zf.writestr(info, f.read())


def bundle_paths(bundle_path: Path | None, zip_path: Path | None) -> list[Path]:
    paths: list[Path] = []
    for path in (bundle_path, zip_path):
        if path and path not in paths:
            paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build OrcaSlicer filament preset JSON files from a cloned OFDB repo."
    )
    parser.add_argument(
        "repo",
        type=Path,
        help="Path to the root of the cloned open-filament-database repository",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path("orca-filaments"),
        help="Output directory for OrcaSlicer filament JSON files (default: orca-filaments)",
    )
    parser.add_argument(
        "--bundle",
        dest="bundle_path",
        type=Path,
        default=None,
        help="Also package the generated JSON files into this importable .orca_filament bundle (default: <output-dir>/<output-dir-name>.orca_filament)",
    )
    parser.add_argument(
        "--no-bundle",
        action="store_true",
        default=False,
        help="Only write individual JSON files; do not create the .orca_filament bundle",
    )
    parser.add_argument(
        "-b", "--brand",
        help="Only convert filaments from this manufacturer name or OFDB brand slug",
    )
    parser.add_argument(
        "--brands",
        nargs="+",
        default=None,
        help="Only convert filaments from these manufacturer names or OFDB brand slugs",
    )
    parser.add_argument(
        "--materials",
        nargs="+",
        default=None,
        help="Only convert these OFDB material folders, e.g. PLA PETG ABS",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        default=False,
        help="Select brands and materials with a cursor-driven terminal UI",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Convert only 10 random filaments after filtering",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for --debug sampling",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=False,
        help="Pretty-print JSON with two spaces instead of Orca-style tabs",
    )
    parser.add_argument(
        "--compatible-printer",
        action="append",
        default=[],
        help="Add a compatible OrcaSlicer printer name; repeat for multiple printers",
    )
    parser.add_argument(
        "--orca-version",
        default="2.3.2.60",
        help="Version string written to importable OrcaSlicer preset JSON files (default: 2.3.2.60)",
    )
    args = parser.parse_args()

    if not args.repo.is_dir():
        sys.exit(f"Error: '{args.repo}' is not a directory")

    brand_filters = args.brands or ([args.brand] if args.brand else None)
    material_filters = args.materials
    if args.interactive:
        selected_brands, selected_materials = interactive_filters(args.repo)
        brand_filters = selected_brands or None
        material_filters = selected_materials or None

    print(f"Crawling '{args.repo}' ...", flush=True)
    presets = crawl(args.repo, brand_filters, material_filters)
    total = len(presets)

    if args.debug and len(presets) > 10:
        rng = random.Random(args.seed)
        presets = rng.sample(presets, 10)

    print(f"Found {total} active filaments.")
    if brand_filters:
        print(f"Brand filter: {', '.join(brand_filters)}")
    if material_filters:
        print(f"Material filter: {', '.join(material_filters)}")
    if args.debug:
        print(f"Debug mode: writing {len(presets)} random filaments.")
    if args.compatible_printer:
        print(f"Compatible printers: {', '.join(args.compatible_printer)}")

    print(f"Writing {len(presets)} OrcaSlicer presets to '{args.output_dir}' ...")
    written = write_presets(
        presets,
        args.output_dir,
        args.pretty,
        args.compatible_printer,
        args.orca_version,
    )
    default_bundle_path = args.output_dir / f"{args.output_dir.name}.orca_filament"
    bundle_targets = [] if args.no_bundle else bundle_paths(args.bundle_path or default_bundle_path, None)
    for path in bundle_targets:
        print(f"Writing import bundle '{path}' ...")
        write_zip(written, path)
    if bundle_targets:
        print("Import the .orca_filament file in OrcaSlicer via File -> Import -> Import Configs....")
    print("Done.")


if __name__ == "__main__":
    main()
