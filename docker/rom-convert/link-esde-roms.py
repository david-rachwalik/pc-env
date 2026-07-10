#!/usr/bin/env python3
"""
ES-DE ROM Symlink Mapper

Scans the source ROM storage drive for standardized folders (e.g. "(2005) Xbox 360 [xbox360]")
and safely symlinks them into the ES-DE target ROMs folder to prevent data duplication.

Usage:
  python3 link-esde-roms.py <src> <dest>
  python3 link-esde-roms.py /mnt/Z/roms /home/rhodair/ROMs
  python3 link-esde-roms.py /mnt/Z/roms /home/rhodair/ROMs --dry-run
"""

import argparse
import os
import re
import sys
from pathlib import Path


# ------------------------ Utilities ------------------------
def info(msg: str):
    print(f"[INFO] {msg}")


def warn(msg: str):
    print(f"[WARN] {msg}", file=sys.stderr)


# ------------------------ Orchestrator ------------------------
def map_symlinks(src_dir: Path, dest_dir: Path, dry_run: bool):
    if not src_dir.exists():
        warn(f"Source directory {src_dir} not found.")
        return

    if dry_run:
        info("--- DRY RUN MODE ENABLED ---")

    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
    else:
        info(f"Target directory resolved as: {dest_dir}")

    # Regex to find exactly what's inside the trailing brackets: e.g. [psx]
    sys_pattern = re.compile(r"\[([^\]]+)\]$")
    mapped = skipped = backups = 0

    for src_path in sorted(src_dir.iterdir()):
        if not src_path.is_dir() or src_path.name.startswith("_"):
            continue

        match = sys_pattern.search(src_path.name.strip())
        if not match:
            continue

        system_name = match.group(1).lower()
        dest_link = dest_dir / system_name

        info(f"\nEvaluating: '{system_name}' -> {src_path.name}")

        # Scenario 1: It's already a symlink
        if dest_link.is_symlink():
            current_target = os.readlink(dest_link)
            if current_target == str(src_path):
                info("  [OK] Symlink is healthy and correct. Skipped.")
                skipped += 1
                continue
            else:
                warn(
                    f"  [Fixing] Link points to wrong target ({current_target}). Updating..."
                )
                if not dry_run:
                    dest_link.unlink()

        # Scenario 2: It exists, but it's a real folder
        elif dest_link.exists():
            if dest_link.is_dir():
                backup_path = dest_dir / f"{system_name}-bak"
                if backup_path.exists():
                    warn(
                        f"  [Warn] Backup {backup_path.name} already exists. Skipping to avoid losing data."
                    )
                    skipped += 1
                    continue
                info(
                    f"  [Backup] Renaming existing physical directory to '{backup_path.name}'..."
                )
                if not dry_run:
                    dest_link.rename(backup_path)
                backups += 1
            else:
                warn(
                    f"  [Error] {dest_link.name} is a file, not a directory. Skipping."
                )
                skipped += 1
                continue

        # Scenario 3: Create the clean symlink
        info("  [Linked] Successfully mapped directory to ES-DE.")
        if not dry_run:
            os.symlink(src_path, dest_link)
        mapped += 1

    info("\n--- Link Mapping Complete ---")
    info(f"Done. Mapped: {mapped}, Backups Created: {backups}, Skipped: {skipped}")


# ------------------------ CLI ------------------------
def main():
    parser = argparse.ArgumentParser(description="Map ROM directories via symlinks.")
    parser.add_argument(
        "src", type=Path, help="Source folder containing organized ROMs."
    )
    parser.add_argument("dest", type=Path, help="ES-DE Target ROMs folder.")
    parser.add_argument(
        "-d", "--dry-run", action="store_true", help="Simulate without making changes."
    )

    args = parser.parse_args()
    map_symlinks(args.src, args.dest, args.dry_run)


if __name__ == "__main__":
    main()
