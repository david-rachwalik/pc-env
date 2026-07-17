#!/usr/bin/env python3
"""
Universal Batch ROM Converter & Compressor for ES-DE.

Supports compressing unoptimized source formats into:
 - 7z (Cartridge formats: NES, SNES, Genesis, N64)
 - CHD (Optical media: PS1, PS2, Saturn, Dreamcast)
 - Rebuilt ISO (Zero-padding stripped: Xbox, Xbox 360)
 - RVZ (Proprietary lossless: GameCube, Wii)

Usage:
  python3 convert-roms.py /path/to/roms
  python3 convert-roms.py /path/to/roms --system ps2
  python3 convert-roms.py /path/to/roms --verify

Behavior & Pipeline:
 1. Auto-Detection: Sniff target game system based on folder naming logic (or use explicit `--system`)
 2. Validation: Scans `_converted_roms` output directory; tracks healthy items, validates untracked ones
 3. Discovery: Recursively finds matching raw source files outside the converted directory
 4. Evaluation (Idempotent): Skips files that exist, are valid, & in the `converted_log` tracker
    (unless brute-force `--verify` is provided)
 5. Execution: Purges existing artifacts, extracts inferior archives natively in a volatile temporary workspace,
    rebuilds (if necessary), and compresses targets into their designated optimal format
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from rom_configs import SYSTEM_CONFIGS

# ------------------------ Configuration State ------------------------
OVERWRITE = False
DRY_RUN = False
VERIFY_ALL = False


# ------------------------ Basic Utilities ------------------------
def info(msg: str):
    print(f"[INFO] {msg}")


def warn(msg: str):
    print(f"[WARN] {msg}", file=sys.stderr)


# Lazily resolve tool paths safely without crashing at initialization
EXTRACT_XISO = shutil.which("extract-xiso")
CHDMAN = shutil.which("chdman")
DOLPHIN_TOOL = shutil.which("dolphin-tool") or shutil.which("DolphinTool")
SEVEN_ZIP = shutil.which("7z") or shutil.which("7zz")


def require_tool(tool_path: str | None, tool_name: str) -> str:
    """Validates a tool exists right before we actually need to use it."""
    if not tool_path:
        raise RuntimeError(f"Required dependency missing from PATH: {tool_name}")
    return tool_path


def run_command(cmd: list[str]) -> subprocess.CompletedProcess:
    """Executes a system subprocess using safe payload arrays."""
    try:
        return subprocess.run(
            cmd,
            check=True,
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


# ------------------------ Integrity Validators ------------------------
def validate(path: Path, format_type: str) -> bool:
    """Routes the file to the correct native cryptographic validation tool based on type."""
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


# ------------------------ Processing Engines ------------------------
def process_rom(input_path: Path, output_path: Path, format_type: str) -> bool:
    """Core logic to transform a source file into its targeted optimal format."""
    if DRY_RUN:
        info(
            f"  DRY RUN: Transforming {input_path.name} -> {output_path.name} via '{format_type}'."
        )
        return True

    # Purge existing artifacts so archive tools (like 7z) overwrite cleanly instead of appending
    if output_path.exists():
        output_path.unlink()

    temp_dir = None
    try:
        # --- Standard Optical (MAME CHDMAN) ---
        if format_type == "chd":
            tool = require_tool(CHDMAN, "chdman")
            info(f"    Compressing to CHD (chdman) -> {output_path.name}...")
            run_command(
                [tool, "createcd", "-i", str(input_path), "-o", str(output_path)]
            )

        # --- Microsoft Optical (Strip Zero Padding) ---
        elif format_type == "rebuilt_iso":
            tool = require_tool(EXTRACT_XISO, "extract-xiso")
            info(f"    Rebuilding ISO (extract-xiso) -> {output_path.name}...")

            temp_dir = output_path.parent / f"_temp_{input_path.stem}"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)

            run_command([tool, "-x", str(input_path), "-d", str(temp_dir)])
            run_command([tool, "-c", str(temp_dir), str(output_path)])

        # --- Nintendo Optical (Dolphin RVZ) ---
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

        # --- Standard Cartridges (7Zip LZMA2) ---
        elif format_type == "archive":
            tool = require_tool(SEVEN_ZIP, "7zip")
            base_cmd = [tool, "a", str(output_path), "-m0=lzma2", "-mx=9"]

            # Fully extract source archives before repacking to prevent nested compression frames
            if input_path.suffix.lower() in [".zip", ".rar", ".7z"]:
                info(
                    f"    Extracting and re-archiving {input_path.name} to 7z (LZMA2) -> {output_path.name}..."
                )

                temp_dir = output_path.parent / f"_temp_{input_path.stem}"
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                temp_dir.mkdir(parents=True, exist_ok=True)

                run_command([tool, "x", str(input_path), f"-o{temp_dir}"])
                run_command(base_cmd + [f"{temp_dir}/*"])

            # Standard single ROM file compression (.n64, .nes, etc)
            else:
                info(f"    Archiving to 7z (7zip LZMA2) -> {output_path.name}...")
                run_command(base_cmd + [str(input_path)])

        else:
            warn(f"Unknown processor type: {format_type}")
            return False

        if not validate(output_path, format_type):
            raise RuntimeError("Post-build validation failed.")
        return True

    except Exception as e:
        warn(f"Failed converting {input_path.name}: {e}")
        if output_path.exists():
            output_path.unlink()  # Nuke partially built corrupted files
        return False

    finally:
        # Guarantee volatile workspace cleanup to prevent ghost folders filling up the disk
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


# ------------------------ Tracker IO ------------------------
def load_tracker(tracker_path: Path) -> set[str]:
    """Loads previously processed filenames from the tracker file as an O(1) Set."""
    if not tracker_path.exists():
        return set()
    with open(tracker_path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def append_tracker(tracker_path: Path, filename: str):
    """Appends a successfully processed filename to the tracker."""
    with open(tracker_path, "a", encoding="utf-8") as f:
        f.write(f"{filename}\n")


# ------------------------ Worker Functions ------------------------
def detect_system(path: Path) -> str | None:
    """Sniffs the console type by identifying brackets [sys] or aliases in the target path."""
    search_str = str(path).lower()
    search_folder = path.name.lower()

    # Exact bracket match anywhere in path (e.g., "[snes]")
    bracket_pattern = re.compile(r"\[([^\]]+)\]")
    for found_bracket in bracket_pattern.findall(search_str):
        for sys_id, config in SYSTEM_CONFIGS.items():
            if found_bracket == sys_id or found_bracket in config.get("aliases", []):
                return sys_id

    # Fallback: directory boundaries or bounded word match
    for sys_id, config in SYSTEM_CONFIGS.items():
        identifiers = [sys_id] + config.get("aliases", [])
        for ident in identifiers:
            if f"/{ident}/" in search_str:
                return sys_id
            # Match discrete word to prevent 'nes' triggering on 'snes' or 'genesis'
            if re.search(rf"\b{re.escape(ident)}\b", search_folder):
                return sys_id

    return None


def heal_and_validate_directory(
    out_dir: Path,
    format_type: str,
    out_ext: str,
    processed_set: set[str],
    tracker_file: Path,
):
    """Scans the `_converted_roms` location.  Rapidly tracks healthy items and strictly verifies questionable ones."""
    if not out_dir.exists():
        return

    info(f"--- Fast-Heal Phase in {out_dir.name} ---")
    for f in out_dir.rglob(f"*{out_ext}"):
        if not f.is_file():
            continue

        # Trust the tracker: Heavily speeds up subsequent runs unless explicitly ordered to verify via CLI (-v)
        if f.stem in processed_set and not VERIFY_ALL:
            continue

        if validate(f, format_type):
            info(f"  Valid: '{f.name}'")
            if f.stem not in processed_set and not DRY_RUN:
                append_tracker(tracker_file, f.stem)
                processed_set.add(f.stem)
        else:
            warn(f"  INVALID: '{f.name}' is corrupted! Please manually inspect.")


def evaluate_target(
    f: Path, out_dir: Path, config: dict, processed_set: set[str], tracker_file: Path
) -> str:
    """Orchestrates Skip vs Processing logic for a singular source file."""
    out_ext = config["output_ext"]
    format_type = config["format"]
    out_file = out_dir / f"{f.stem}{out_ext}"

    # --- Priority 1: Instant Skip (Tracked Files) ---
    if f.stem in processed_set and not OVERWRITE:
        if VERIFY_ALL and f.suffix.lower() == out_ext:
            info(
                f"  [Verify Engine] Re-Validating tracked optimal file sitting in root: '{f.name}'..."
            )
            validate(f, format_type)

        info(f"  Skipping: '{f.stem}' marked as optimally processed in tracker.")
        return "skipped"

    # --- Priority 2: Check Targeted Artifact State in _converted_roms ---
    if out_file.exists() and not OVERWRITE:
        info(
            f"  Untracked match found in {out_dir.name} for '{f.stem}'. Auto-healing log file..."
        )
        if validate(out_file, format_type):
            info("  Valid! Skipping conversion.")
            if not DRY_RUN:
                append_tracker(tracker_file, f.stem)
                processed_set.add(f.stem)
            return "skipped"
        else:
            warn(
                f"  INVALID: '{out_file.name}' exists but FAILED validation! (Use --overwrite)"
            )
            return "skipped"

    # --- Execution Phase (All untracked source files or explicit overwrites) ---
    if not DRY_RUN:
        out_dir.mkdir(exist_ok=True)

    if process_rom(f, out_file, format_type):
        info(f"  Success: {out_file.name}")
        if not DRY_RUN:
            append_tracker(tracker_file, f.stem)
            processed_set.add(f.stem)
        return "success"

    return "failed"


# ------------------------ Main Orchestrator ------------------------
def batch_convert(target_dir: Path, requested_system: str | None):
    """The master pipeline execution chain."""
    if not target_dir.exists():
        warn(f"Path does not exist: {target_dir}")
        return

    # Determine standard architecture
    system_key = requested_system if requested_system else detect_system(target_dir)
    if not system_key or system_key not in SYSTEM_CONFIGS:
        warn(
            "Could not determine system from folder path. Please explicitly state using --system"
        )
        return

    config = SYSTEM_CONFIGS[system_key]
    format_type = config["format"]
    out_ext = config["output_ext"]

    info(
        f"--- Detected System: {config['description']} (Format: {format_type.upper()}) ---"
    )

    # Define Workspace
    base_path = target_dir.parent if target_dir.is_file() else target_dir
    out_dir = base_path / "_converted_roms"
    tracker_file = base_path / "converted_log"

    processed_set = load_tracker(tracker_file)

    # Fast validation pass of orphaned items already resting in the output directory
    heal_and_validate_directory(
        out_dir, format_type, out_ext, processed_set, tracker_file
    )

    # Collect pending targets matching the assigned file extensions
    # (Avoid infinite recursion by strictly ignoring the inner output directory)
    source_files = [
        f
        for f in base_path.rglob("*")
        if f.is_file()
        and f.suffix.lower() in config["exts"]
        and "_converted_roms" not in f.parts
    ]

    if not source_files:
        info("\n--- Pipeline Completed ---")
        info("Done. Found 0 raw sources requiring action.")
        return

    # Execution Loop
    info(f"\n--- Discovered {len(source_files)} Source Item(s) ---")
    success = skipped = failed = 0

    for i, f in enumerate(sorted(source_files), 1):
        info(f"\nEvaluating {i}/{len(source_files)}: {f.stem}")
        result = evaluate_target(f, out_dir, config, processed_set, tracker_file)

        if result == "success":
            success += 1
        elif result == "failed":
            failed += 1
        else:
            skipped += 1

    info("\n--- Pipeline Completed ---")
    info(f"Done. Succeeded: {success}, Skipped: {skipped}, Failed: {failed}.")


# ------------------------ CLI ------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Universal Batch ROM Conversion Pipeline for ES-DE."
    )
    parser.add_argument("path", type=Path, help="Folder containing targeted ROMs.")
    parser.add_argument(
        "-s",
        "--system",
        type=str,
        help="Manually force system logic block (e.g., ps2).",
    )
    parser.add_argument(
        "-v",
        "--verify",
        action="store_true",
        help="Force deep cryptographic validation on previously tracked healthy files.",
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Nuke and re-process existing output artifacts.",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Simulate logical pipeline without executing heavy filesystem writes.",
    )

    args = parser.parse_args()

    # Apply application state globals
    global OVERWRITE, DRY_RUN, VERIFY_ALL
    OVERWRITE = args.overwrite
    DRY_RUN = args.dry_run
    VERIFY_ALL = args.verify

    if DRY_RUN:
        info("--- DRY RUN MODE ENABLED ---")
    if VERIFY_ALL:
        info("--- BRUTE FORCE CRYPTOGRAPHIC VERIFICATION ENABLED ---")

    batch_convert(args.path, args.system)


if __name__ == "__main__":
    main()
