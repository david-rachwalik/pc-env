#!/usr/bin/env python3
"""
Batch convert ROMs for ES-DE emulation.
Currently supports:
 - Xbox 360 (.iso) -> Rebuilt Padding-Stripped .iso

Usage:
  python3 convert-roms.py /path/to/roms

Behavior:
 - Scans video games based on extension.
 - Processes into a clean '_converted_roms' output directory.
 - Idempotent: Skips processing if output file already exists.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# ------------------------ Configuration ------------------------
OVERWRITE = False
DRY_RUN = False

SYSTEM_CONFIGS = {
    "xbox360": {
        "exts": {".iso"},
        "output_ext": ".iso",
    }
}


# ------------------------ Utilities ------------------------
def info(msg: str):
    print(f"[INFO] {msg}")


def warn(msg: str):
    print(f"[WARN] {msg}", file=sys.stderr)


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        warn(f"Required tool not found: {name}")
        sys.exit(1)
    return path


EXTRACT_XISO = require_tool("extract-xiso")
# CHDMAN = require_tool("chdman")  # Ready for PS2/GC support


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as e:
        warn(f"Command failed: {' '.join(cmd)}")
        warn(f"  stdout: {e.stdout.strip()}")
        warn(f"  stderr: {e.stderr.strip()}")
        raise


# ------------------------ Processors ------------------------
def validate_iso(iso_path: Path) -> bool:
    """Runs extract-xiso list command to verify structural integrity."""
    if DRY_RUN and not iso_path.exists():
        return True
    info(f"    Validating ISO integrity: {iso_path.name}")
    try:
        run_command([EXTRACT_XISO, "-l", str(iso_path)])
        return True
    except Exception:
        return False


def process_xbox360(input_path: Path, output_path: Path) -> bool:
    """Uses extract-xiso to unpack and dynamically rebuild the ISO without padding."""
    temp_dir = output_path.parent / f"_temp_{input_path.stem}"

    if DRY_RUN:
        info(
            f"  DRY RUN: Would unpack {input_path.name} and rebuild as {output_path.name}"
        )
        return True

    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        info("    Extracting (stripping padding)...")
        run_command([EXTRACT_XISO, "-x", str(input_path), "-d", str(temp_dir)])

        info("    Rebuilding optimized ISO...")
        run_command([EXTRACT_XISO, "-c", str(temp_dir), str(output_path)])

        if not validate_iso(output_path):
            raise RuntimeError("Validation failed after rebuild.")

        return True
    except Exception as e:
        warn(f"Failed converting {input_path.name}: {e}")
        if output_path.exists():
            output_path.unlink()
        return False
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


# ------------------------ Tracker IO ------------------------
def load_tracker(tracker_path: Path) -> set[str]:
    """Loads previously processed filenames from the tracker file."""
    if not tracker_path.exists():
        return set()
    with open(tracker_path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def append_tracker(tracker_path: Path, filename: str):
    """Appends a successfully processed filename to the tracker."""
    with open(tracker_path, "a", encoding="utf-8") as f:
        f.write(f"{filename}\n")


# ------------------------ Orchestrator ------------------------
def batch_convert(target_dir: Path):
    if not target_dir.exists():
        warn(f"Path does not exist: {target_dir}")
        return

    base_path = target_dir.parent if target_dir.is_file() else target_dir
    out_dir = base_path / "_converted_roms"
    tracker_file = base_path / "_converted_tracker.txt"

    success = skipped = failed = 0
    processed_set = load_tracker(tracker_file)

    # --- Standalone Validation Pass ---
    # Validate files currently sitting in _converted_roms
    if out_dir.exists():
        info(f"--- Validating items in {out_dir.name} ---")
        for out_file in out_dir.rglob("*.iso"):
            if validate_iso(out_file):
                info(f"  Valid: '{out_file.name}'")
            else:
                warn(
                    f"  INVALID: '{out_file.name}' is corrupted! Please manually inspect."
                )

    # Collect all Xbox 360 targets (ignoring the output folder)
    x360_files = [
        f
        for f in base_path.rglob("*")
        if f.is_file()
        and f.suffix.lower() in SYSTEM_CONFIGS["xbox360"]["exts"]
        and "_converted_roms" not in str(f)
    ]

    if x360_files:
        info(f"\n--- Found {len(x360_files)} Source Xbox 360 ISO(s) ---")
        for i, f in enumerate(sorted(x360_files), 1):
            info(f"\nProcessing {i}/{len(x360_files)}: {f.name}")
            out_file = out_dir / f"{f.stem}{SYSTEM_CONFIGS['xbox360']['output_ext']}"

            if not OVERWRITE:
                # Scenario 1: Output file already exists
                if out_file.exists():
                    if validate_iso(out_file):
                        info(
                            f"  Skipping: '{out_file.name}' already exists and is valid."
                        )
                    else:
                        warn(
                            f"  Skipping: '{out_file.name}' already exists but FAILED validation! Please manually inspect."
                        )

                    if f.name not in processed_set and not DRY_RUN:
                        append_tracker(tracker_file, f.name)
                        processed_set.add(f.name)
                    skipped += 1
                    continue

                # Scenario 2: Processing previously marked completed in tracker
                elif f.name in processed_set:
                    info(
                        f"  Tracker match found for '{f.name}'. Validating source file..."
                    )
                    if validate_iso(f):
                        info(
                            f"  Skipping: '{f.name}' marked as processed in tracker and is valid."
                        )
                    else:
                        warn(
                            f"  Skipping: '{f.name}' marked as processed in tracker but FAILED validation! Please manually inspect."
                        )
                    skipped += 1
                    continue

            # Scenario 3: Process the ROM
            if not DRY_RUN:
                out_dir.mkdir(exist_ok=True)

            if process_xbox360(f, out_file):
                info(f"  Success: {out_file.name}")
                if not DRY_RUN:
                    append_tracker(tracker_file, f.name)
                    processed_set.add(f.name)
                success += 1
            else:
                failed += 1

    info("\n" + "--- All processing complete ---")
    info(f"Done. Succeeded: {success}, Skipped: {skipped}, Failed: {failed}.")


# ------------------------ CLI ------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Batch convert/compress ROMs for ES-DE."
    )
    parser.add_argument("path", type=Path, help="Folder containing ROMs.")
    parser.add_argument(
        "-o", "--overwrite", action="store_true", help="Overwrite existing output."
    )
    parser.add_argument(
        "-d", "--dry-run", action="store_true", help="Simulate without converting."
    )
    args = parser.parse_args()

    global OVERWRITE, DRY_RUN
    OVERWRITE = args.overwrite
    DRY_RUN = args.dry_run

    if DRY_RUN:
        info("--- DRY RUN MODE ENABLED ---")

    batch_convert(args.path)


if __name__ == "__main__":
    main()
