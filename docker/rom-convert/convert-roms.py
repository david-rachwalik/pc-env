#!/usr/bin/env python3
"""
Universal Batch ROM Converter & Compressor for ES-DE.

Supports compressing unoptimized source formats into:
 - 7z (Cartridge formats)
 - CHD (PS1, PS2, Saturn, Dreamcast)
 - Rebuilt ISO (Xbox, Xbox 360)
 - RVZ (GameCube, Wii)

Usage:
  python3 convert-roms.py /path/to/roms
  python3 convert-roms.py /path/to/roms --system ps2

Behavior:
 - Auto-detects the target game system based on folder naming.
 - Extracts, rebuilds, and compresses ROMs cleanly into `_converted_roms`.
 - Automatically validates output integrity.
 - Idempotent: Skips processing and validates existing files.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from rom_configs import SYSTEM_CONFIGS

# ------------------------ Configuration ------------------------
OVERWRITE = False
DRY_RUN = False


# ------------------------ Utilities ------------------------
def info(msg: str):
    print(f"[INFO] {msg}")


def warn(msg: str):
    print(f"[WARN] {msg}", file=sys.stderr)


# Map tool bins once at startup (resolves to None if not found instead of crashing)
EXTRACT_XISO = shutil.which("extract-xiso")
CHDMAN = shutil.which("chdman")
DOLPHIN_TOOL = shutil.which("dolphin-tool") or shutil.which("DolphinTool")
SEVEN_ZIP = shutil.which("7z") or shutil.which("7zz")


def require_tool(tool_path: str | None, tool_name: str) -> str:
    """Validates a tool exists right before we actually need to use it."""
    if not tool_path:
        raise RuntimeError(
            f"Required tool is not installed or not in PATH: {tool_name}"
        )
    return tool_path


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


# ------------------------ Validators ------------------------
def validate(path: Path, format_type: str) -> bool:
    """Routes the file to the correct validation tool based on type."""
    if DRY_RUN and not path.exists():
        return True

    info(f"    Validating integrity ({format_type}): {path.name}")
    try:
        if format_type == "rebuilt_iso":
            run_command([require_tool(EXTRACT_XISO, "extract-xiso"), "-l", str(path)])
        elif format_type == "chd":
            run_command([require_tool(CHDMAN, "chdman"), "verify", "-i", str(path)])
        elif format_type == "rvz":
            run_command(
                [require_tool(DOLPHIN_TOOL, "DolphinTool"), "verify", "-i", str(path)]
            )
        elif format_type == "archive":
            run_command([require_tool(SEVEN_ZIP, "7zip"), "t", str(path)])
        else:
            warn(f"Unknown format type for validation: {format_type}")
            return False

        return True
    except Exception as e:
        warn(f"Validation error: {e}")
        return False


# ------------------------ Processors ------------------------
def process_rom(input_path: Path, output_path: Path, format_type: str) -> bool:
    """Routes the source file to its corresponding processor."""
    if DRY_RUN:
        info(
            f"  DRY RUN: Would compress {input_path.name} into {output_path.name} via '{format_type}' processor."
        )
        return True

    # Pre-emptively remove target to prevent tools (like 7z) from appending instead of overwriting
    if output_path.exists():
        output_path.unlink()

    temp_dir = None
    try:
        # --- Xbox / Xbox 360 (Strip Padding) ---
        if format_type == "rebuilt_iso":
            tool = require_tool(EXTRACT_XISO, "extract-xiso")
            info(f"    Rebuilding ISO (extract-xiso) -> {output_path.name}...")
            temp_dir = output_path.parent / f"_temp_{input_path.stem}"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)

            run_command([tool, "-x", str(input_path), "-d", str(temp_dir)])
            run_command([tool, "-c", str(temp_dir), str(output_path)])

        # --- PS1 / PS2 / Saturn / Dreamcast (MAME CHDMAN) ---
        elif format_type == "chd":
            tool = require_tool(CHDMAN, "chdman")
            info(f"    Compressing to CHD (chdman) -> {output_path.name}...")
            run_command(
                [tool, "createcd", "-i", str(input_path), "-o", str(output_path)]
            )

        # --- GameCube / Wii (Dolphin RVZ) ---
        elif format_type == "rvz":
            tool = require_tool(DOLPHIN_TOOL, "DolphinTool")
            info(f"    Compressing to RVZ (DolphinTool) -> {output_path.name}...")
            run_command(
                [
                    tool,
                    "convert",
                    "-i",
                    str(input_path),
                    "-o",
                    str(output_path),
                    "-f",
                    "rvz",
                    "-b",
                    "131072",
                    "-c",
                    "zstd",
                ]
            )

        # --- Cartridges (7Zip LZMA2) ---
        elif format_type == "archive":
            tool = require_tool(SEVEN_ZIP, "7zip")
            info(f"    Archiving to 7z (7zip LZMA2) -> {output_path.name}...")
            run_command(
                [tool, "a", str(output_path), str(input_path), "-m0=lzma2", "-mx=9"]
            )

        else:
            warn(f"Unknown processor type: {format_type}")
            return False

        # Post-compression integrity check
        if not validate(output_path, format_type):
            raise RuntimeError("Validation failed after build.")

        return True

    except Exception as e:
        warn(f"Failed converting {input_path.name}: {e}")
        if output_path.exists():
            output_path.unlink()
        return False

    finally:
        # Guarantee cleanup: Prevents ghost files if extract-xiso crashes mid-extract
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


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
def detect_system(path: Path) -> str | None:
    """Attempts to figure out which console is in the folder by matching names using ES-DE conventions and aliases."""
    search_str = str(path).lower()
    search_folder = path.name.lower()

    for sys_id, config in SYSTEM_CONFIGS.items():
        identifiers = [sys_id] + config.get("aliases", [])
        for ident in identifiers:
            # Match strict pathing ([sys] or /sys/) OR broad substring in the target folder's name (e.g. "gamecube")
            if (
                f"[{ident}]" in search_str
                or f"/{ident}/" in search_str
                or ident in search_folder
            ):
                return sys_id
    return None


def batch_convert(target_dir: Path, requested_system: str | None):
    if not target_dir.exists():
        warn(f"Path does not exist: {target_dir}")
        return

    # Determine system
    system_key = requested_system if requested_system else detect_system(target_dir)
    if not system_key or system_key not in SYSTEM_CONFIGS:
        warn("Could not determine system from folder path.")
        warn(
            f"Please use --system to designate one of: {', '.join(SYSTEM_CONFIGS.keys())}"
        )
        return

    config = SYSTEM_CONFIGS[system_key]
    format_type = config["format"]

    info(
        f"--- Detected System: {config['description']} (Format: {format_type.upper()}) ---"
    )

    base_path = target_dir.parent if target_dir.is_file() else target_dir
    out_dir = base_path / "_converted_roms"
    tracker_file = base_path / "_converted_tracker.txt"

    success = skipped = failed = 0
    processed_set = load_tracker(tracker_file)

    # --- Standalone Validation Pass ---
    # Validate files currently sitting in _converted_roms using the appropriate sys validator
    if out_dir.exists():
        info(f"--- Validating items in {out_dir.name} ---")
        for out_file in out_dir.rglob(f"*{config['output_ext']}"):
            if validate(out_file, format_type):
                info(f"  Valid: '{out_file.name}'")
            else:
                warn(
                    f"  INVALID: '{out_file.name}' is corrupted! Please manually inspect."
                )

    # Collect targets
    source_files = [
        f
        for f in base_path.rglob("*")
        if f.is_file()
        and f.suffix.lower() in config["exts"]
        and "_converted_roms" not in str(f)
    ]

    if source_files:
        info(f"\n--- Found {len(source_files)} Source ROM(s) ---")
        for i, f in enumerate(sorted(source_files), 1):
            info(f"\nProcessing {i}/{len(source_files)}: {f.name}")
            out_file = out_dir / f"{f.stem}{config['output_ext']}"

            if not OVERWRITE:
                # Scenario 1: Output file exists (skip & validate)
                if out_file.exists():
                    if validate(out_file, format_type):
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

                # Scenario 2: Main folder file matches tracker (skip & validate)
                elif f.name in processed_set:
                    info(
                        f"  Tracker match found for '{f.name}'. Validating source file..."
                    )
                    if validate(
                        f, format_type
                    ):  # Run the validator on the source file!
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

            if process_rom(f, out_file, format_type):
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
    parser = argparse.ArgumentParser(description="Universal Batch ROM Compressor.")
    parser.add_argument("path", type=Path, help="Folder containing ROMs.")
    parser.add_argument(
        "-s",
        "--system",
        type=str,
        help="Manually override system detection (e.g. ps2, gc, xbox360).",
    )
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

    batch_convert(args.path, args.system)


if __name__ == "__main__":
    main()
