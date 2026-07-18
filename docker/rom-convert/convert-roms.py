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
ARCHIVE_EXTS = {".zip", ".rar", ".7z"}


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


def run_command(cmd: list[str], quiet: bool = False) -> subprocess.CompletedProcess:
    """Executes a system subprocess. Allows long-running progress bars to render to console."""
    try:
        return subprocess.run(
            cmd,
            check=True,
            # Let standard streams inherit terminal directly unless request silence
            stdout=subprocess.PIPE if quiet else None,
            stderr=subprocess.PIPE if quiet else None,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as e:
        warn(f"Command failed: {' '.join(cmd)}")
        if getattr(e, "stdout", None):
            warn(f"  stdout: {e.stdout.strip()}")
        if getattr(e, "stderr", None):
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
            run_command(
                [require_tool(EXTRACT_XISO, "extract-xiso"), "-l", str(path)],
                quiet=True,
            )
        elif format_type == "chd":
            run_command(
                [require_tool(CHDMAN, "chdman"), "verify", "-i", str(path)], quiet=True
            )
        elif format_type == "rvz":
            run_command(
                [require_tool(DOLPHIN_TOOL, "DolphinTool"), "verify", "-i", str(path)],
                quiet=True,
            )
        elif format_type == "archive":
            run_command([require_tool(SEVEN_ZIP, "7zip"), "t", str(path)], quiet=True)
        else:
            warn(f"Unknown format type for validation: {format_type}")
            return False
        return True
    except Exception as e:
        warn(f"Validation error: {e}")
        return False


# ------------------------ Optical File Sanitization ------------------------
def sanitize_cue(cue_path: Path):
    """Auto-fixes Windows paths and case-sensitivity issues in .cue files for Linux compatibility."""
    # Strict limit to .cue files (other descriptors like .ccd/.gdi use different schemas)
    if cue_path.suffix.lower() != ".cue":
        return

    try:
        content = cue_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        modified = False

        # Build a case-insensitive map of the physical files sitting next to the .cue
        dir_files_lower = {
            f.name.lower(): f.name for f in cue_path.parent.iterdir() if f.is_file()
        }

        new_lines = []
        # Matches typical CUE track definitions: FILE "Track01.bin" BINARY
        file_pattern = re.compile(r'^(FILE\s+")([^"]+)("\s+.*)$', re.IGNORECASE)

        for line in lines:
            match = file_pattern.search(line)
            if match:
                prefix, raw_filename, suffix = match.groups()
                # Strip absolute Windows or POSIX paths, keeping just the filename
                base_name = Path(raw_filename.replace("\\", "/")).name

                # Cross-reference directory map to get the exact physical case-sensitive name
                actual_name = dir_files_lower.get(base_name.lower(), base_name)

                if raw_filename != actual_name:
                    line = f"{prefix}{actual_name}{suffix}"
                    modified = True
            new_lines.append(line)

        if modified:
            cue_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            info(
                f"    Sanitized CUE file casing/paths for Linux compatibility: {cue_path.name}"
            )

    except Exception as e:
        warn(
            f"    Warning: Could not automatically sanitize descriptor {cue_path.name}: {e}"
        )


def generate_fallback_cue(tracks: list[Path], system_id: str) -> Path:
    """Autogenerates a .cue file for bare .bin/.img files so CHDMAN doesn't crash."""
    if not tracks:
        raise FileNotFoundError("No valid ROM or optical data found in archive.")

    # Sort alphabetical to ensure Track 01, Track 02 logic applies sequentially
    tracks.sort(key=lambda p: p.name)

    cue_path = (
        tracks[0].parent
        / f"{tracks[0].stem.split(' (Track')[0].split(' (Disc')[0]}.cue"
    )
    lines = []

    for i, track in enumerate(tracks, 1):
        if i == 1:
            # Sega CD typically uses MODE1; PSX/Saturn use MODE2
            mode = "MODE1/2352" if system_id == "segacd" else "MODE2/2352"
        else:
            mode = "AUDIO"

        lines.append(f'FILE "{track.name}" BINARY')
        lines.append(f"  TRACK {i:02d} {mode}")
        lines.append("    INDEX 01 00:00:00")

    cue_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    info(f"    Auto-generated missing .cue descriptor for {len(tracks)} raw track(s).")
    return cue_path


def handle_archive_phase(
    input_path: Path,
    output_path: Path,
    format_type: str,
    temp_dir: Path,
    system_id: str,
) -> Path | None:
    """Extracts archives to either repack them optimally or locate their internal optical targets.
    Returns the resolved Target Path, or None if the lifecycle completely finished here."""

    tool = require_tool(SEVEN_ZIP, "7zip")
    temp_dir.mkdir(parents=True, exist_ok=True)

    info(f"    Extracting archive {input_path.name}...")
    run_command([tool, "x", str(input_path), f"-o{temp_dir}", "-y"], quiet=True)

    # If the ultimate format IS an archive, repack it cleaner into LZMA2 and exit early
    if format_type == "archive":
        info(f"    Re-archiving to optimized 7z -> {output_path.name}...")
        run_command(
            [tool, "a", str(output_path), "-m0=lzma2", "-mx=9", f"{temp_dir}/*"],
            quiet=True,
        )
        if not validate(output_path, format_type):
            raise RuntimeError("Post-build validation failed.")
        return None  # None indicates full completion of processing

    # Otherwise, find the inner actionable optical file
    known_descriptors = [".cue", ".ccd", ".gdi", ".iso", ".chd", ".rvz"]
    found_targets = [
        p
        for p in temp_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in known_descriptors
    ]

    if found_targets:
        # Prefer .cue/.iso over other obscure formats if multiple lie scattered
        target_path = sorted(
            found_targets, key=lambda x: (x.suffix.lower() != ".cue", x.name)
        )[0]

        if len(found_targets) > 1:
            warn(
                f"    Warning: Multiple optical descriptors found in archive. Processing primary: {target_path.name}"
            )
    else:
        # Fallback generator for archives acting as raw unmanaged payload dumps
        raw_tracks = [
            p
            for p in temp_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in [".bin", ".img"]
        ]
        if raw_tracks:
            target_path = generate_fallback_cue(raw_tracks, system_id)
        else:
            raise RuntimeError(
                "Archive did not contain recognized optical descriptors or raw tracks."
            )

    info(f"    Target acquired from archive: {target_path.name}")
    return target_path


# ------------------------ Processing Engines ------------------------
def process_rom(input_path: Path, output_path: Path, config: dict) -> bool:
    """Core logic to transform a source file into its targeted optimal format."""
    format_type = config["format"]
    system_id = config.get("system_id", "")

    if DRY_RUN:
        info(
            f"  DRY RUN: Transforming {input_path.name} -> {output_path.name} via '{format_type}'."
        )
        return True

    # Purge existing artifacts so archive tools (like 7z) overwrite cleanly instead of appending
    if output_path.exists():
        output_path.unlink()

    # Unified session-level temporary workspace
    session_temp_dir = output_path.parent / f"_temp_{input_path.stem}"
    if session_temp_dir.exists():
        shutil.rmtree(session_temp_dir, ignore_errors=True)

    try:
        target_path = input_path

        # --- Universal Archive Phase (Extract target from within) ---
        if input_path.suffix.lower() in ARCHIVE_EXTS:
            archive_temp = session_temp_dir / "archive"
            target_path = handle_archive_phase(
                input_path, output_path, format_type, archive_temp, system_id
            )
            if target_path is None:
                return True  # Processing fully completed within archive phase

        # --- Standard Optical (MAME CHDMAN) ---
        if format_type == "chd":
            tool = require_tool(CHDMAN, "chdman")

            # Fix broken .cue files before chdman chokes on them
            sanitize_cue(target_path)

            # If already a CHD, 'copy' will recompress and update it to newest schema / best compression
            if target_path.suffix.lower() == ".chd":
                info(
                    f"    Re-compressing/Upgrading CHD (chdman copy) -> {output_path.name}..."
                )
                run_command(
                    [tool, "copy", "-i", str(target_path), "-o", str(output_path)]
                )
            else:
                info(
                    f"    Compressing to CHD (chdman createcd) -> {output_path.name}..."
                )
                run_command(
                    [tool, "createcd", "-i", str(target_path), "-o", str(output_path)]
                )

        # --- Microsoft Optical (Strip Zero Padding) ---
        elif format_type == "rebuilt_iso":
            tool = require_tool(EXTRACT_XISO, "extract-xiso")
            info(f"    Rebuilding ISO (extract-xiso) -> {output_path.name}...")

            # Use isolated xiso rebuild subfolder to prevent collision if using an archive
            iso_temp = session_temp_dir / "xiso"
            iso_temp.mkdir(parents=True, exist_ok=True)

            run_command([tool, "-x", str(target_path), "-d", str(iso_temp)])
            run_command([tool, "-c", str(iso_temp), str(output_path)])

        # --- Nintendo Optical (Dolphin RVZ) ---
        elif format_type == "rvz":
            tool = require_tool(DOLPHIN_TOOL, "DolphinTool")
            if target_path.suffix.lower() == ".rvz":
                info(f"    Re-compressing RVZ (DolphinTool) -> {output_path.name}...")
            else:
                info(f"    Compressing to RVZ (DolphinTool) -> {output_path.name}...")

            run_command(
                [
                    tool,
                    "convert",
                    "-i",
                    str(target_path),
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

        # --- Standard Cartridges (7Zip LZMA2 natively) ---
        elif format_type == "archive":
            tool = require_tool(SEVEN_ZIP, "7zip")
            info(f"    Archiving to 7z (7zip LZMA2) -> {output_path.name}...")
            run_command(
                [tool, "a", str(output_path), "-m0=lzma2", "-mx=9", str(target_path)]
            )

        else:
            warn(f"Unknown processor type: {format_type}")
            return False

        if not validate(output_path, format_type):
            raise RuntimeError("Post-build validation failed.")
        return True

    except KeyboardInterrupt:
        warn(f"\nConversion interrupted by user while processing {input_path.name}.")
        if output_path.exists():
            output_path.unlink()  # Nuke partially built corrupted files
        raise  # Re-raise so master pipeline also halts

    except Exception as e:
        warn(f"Failed converting {input_path.name}: {e}")
        if output_path.exists():
            output_path.unlink()  # Nuke partially built corrupted files
        return False

    finally:
        # Guarantee volatile workspace cleanup to prevent ghost folders filling up the disk
        if session_temp_dir.exists():
            shutil.rmtree(session_temp_dir, ignore_errors=True)


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

    if process_rom(f, out_file, config):
        info(f"  Success: {out_file.name}")
        if not DRY_RUN:
            append_tracker(tracker_file, f.stem)
            processed_set.add(f.stem)
        return "success"

    return "failed"


def generate_m3u_playlists(out_dir: Path, out_ext: str):
    """Auto-generates ES-DE friendly .m3u playlists for multi-disc games."""
    if not out_dir.exists():
        return

    import collections

    # Group files into a shared base name by stripping the (Disc X) and EVERYTHING after it
    # This prevents extra trailing tags on specific discs from splitting the grouping
    disc_pattern = re.compile(r"\s*\((?:Disc|Disk|CD)\b[^)]*\).*$", re.IGNORECASE)
    games_dict = collections.defaultdict(list)

    for f in out_dir.glob(f"*{out_ext}"):
        # Check if the filename implies it's a multi-disc set
        if disc_pattern.search(f.name):
            base_name = disc_pattern.sub("", f.stem).strip()
            games_dict[base_name].append(f.name)

    if not games_dict:
        return

    info(f"\n--- Generating M3U Playlists ({out_dir.name}) ---")
    for base_name, discs in games_dict.items():
        if len(discs) > 1:  # Only generate lists when there are actually multiple discs
            discs.sort()  # Ensures sequential order (Disc 1, Disc 2...)
            m3u_path = out_dir / f"{base_name}.m3u"
            expected_content = "\n".join(discs) + "\n"

            # Check if up-to-date
            if m3u_path.exists():
                try:
                    existing_content = m3u_path.read_text(encoding="utf-8")
                    if existing_content == expected_content:
                        info(f"  Playlist up-to-date: '{m3u_path.name}'")
                        continue
                except Exception:
                    pass  # If we fail to read it, just proceed to overwrite

            # Atomic write: Write to a temp file first, then atomically swap it
            temp_path = m3u_path.with_suffix(".tmp")
            try:
                temp_path.write_text(expected_content, encoding="utf-8")
                temp_path.replace(m3u_path)  # Atomic operation on POSIX
                info(f"  Wrote Playlist: '{m3u_path.name}' ({len(discs)} discs)")
            except Exception as e:
                warn(f"  Failed to write playlist {m3u_path.name}: {e}")
                if temp_path.exists():
                    temp_path.unlink()


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
    config["system_id"] = (
        system_key  # Inject exact ID for downstream contextual decisions
    )
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

    # # Collect pending targets matching the assigned file extensions
    # # (Avoid infinite recursion by strictly ignoring the inner output directory)
    # source_files = [
    #     f
    #     for f in base_path.rglob("*")
    #     if f.is_file()
    #     and f.suffix.lower() in config["exts"]
    #     and "_converted_roms" not in f.parts
    # ]

    # Collect pending targets matching the assigned file extensions
    # (Strictly limited to the immediate target folder; no recursive searching)
    valid_exts = config["exts"] | ARCHIVE_EXTS

    source_files = [
        f for f in base_path.iterdir() if f.is_file() and f.suffix.lower() in valid_exts
    ]

    if not source_files:
        info("\n--- Pipeline Completed ---")
        info("Done.  Found 0 raw sources requiring action.")
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

    # Only generate M3U playlists for optical media capable formats
    if not DRY_RUN and format_type in ["chd", "rvz", "rebuilt_iso"]:
        # For games moved back into the permanent root
        generate_m3u_playlists(base_path, out_ext)
        # For games currently in the staging area
        generate_m3u_playlists(out_dir, out_ext)

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

    try:
        batch_convert(args.path, args.system)
    except KeyboardInterrupt:
        warn("\nPipeline aborted by user.  Exiting cleanly.")
        sys.exit(130)


if __name__ == "__main__":
    main()
