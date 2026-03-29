#!/usr/bin/env python3
"""
Batch convert audio files to different formats using ffmpeg.

Usage:
  python3 convert-audio.py /path/to/folder --profile <profile_name>

Profiles:
  - normal: 128kbps, 44.1kHz, stereo
  - audiobook: 64kbps, 44.1kHz, mono, normalized audio
"""
import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# --- Configuration ---
AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus"}
OUTPUT_SUBDIR = "converted"

# Script-wide settings (set in main)
OVERWRITE = False
DRY_RUN = False

PROFILES = {
    "normal": {
        "format": "mp3",
        "bitrate": "128k",
        "sample_rate": "44100",
        "channels": 2,
        "extra_args": [],
    },
    "audiobook": {
        "format": "mp3",
        "bitrate": "64k",
        "sample_rate": "44100",
        "channels": 1,
        "extra_args": ["-af", "loudnorm"],
    },
    "audiobook-compressed": {
        "format": "mp3",
        "bitrate": "64k",
        "sample_rate": "44100",
        "channels": 1,
        # Chain filters: first compress, then normalize
        # (smooths out internal volume spikes and then makes overall loudness consistent)
        "extra_args": ["-af", "acompressor=threshold=0.089:ratio=9:attack=20:release=250,loudnorm"],
    },
}


# --- Utilities ---
def info(msg: str):
    print(f"[INFO] {msg}")


def warn(msg: str):
    print(f"[WARN] {msg}", file=sys.stderr)


def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    info(f"Running command: {' '.join(cmd)}")
    if DRY_RUN:
        return subprocess.CompletedProcess(cmd, 0)
    try:
        return subprocess.run(cmd, check=check, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        warn(f"Command failed with exit code {e.returncode}")
        warn(f"Stderr: {e.stderr}")
        warn(f"Stdout: {e.stdout}")
        raise


# --- Conversion Logic ---
def get_audio_files(path: Path) -> List[Path]:
    """Find all audio files in a directory."""
    files = []
    for ext in AUDIO_EXTS:
        files.extend(path.rglob(f"*{ext}"))
    return files


def convert_audio_file(input_path: Path, output_dir: Path, profile: Dict[str, Any]):
    """Converts a single audio file based on the selected profile."""
    output_filename = f"{input_path.stem}.{profile['format']}"
    output_path = output_dir / output_filename

    if output_path.exists() and not OVERWRITE:
        info(f"Skipping existing file: {output_path}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-b:a",
        profile["bitrate"],
        "-ar",
        profile["sample_rate"],
        "-ac",
        str(profile["channels"]),
        "-c:v",
        "copy",  # Copy video stream (e.g., album art)
        *profile["extra_args"],
        str(output_path),
    ]

    try:
        run_command(cmd)
        info(f"Converted: {input_path.name} -> {output_path.name}")
    except subprocess.CalledProcessError:
        warn(f"Failed to convert {input_path.name}")


def batch_convert(path: Path, profile_name: str):
    """Batch convert all audio files in a directory."""
    if not path.is_dir():
        warn(f"Error: Path is not a directory: {path}")
        return

    profile = PROFILES.get(profile_name)
    if not profile:
        warn(f"Error: Profile '{profile_name}' not found.")
        return

    info(f"Starting batch conversion with profile: {profile_name}")
    info(f"Source directory: {path}")

    audio_files = get_audio_files(path)
    if not audio_files:
        warn("No audio files found.")
        return

    output_dir = path / OUTPUT_SUBDIR
    info(f"Output directory: {output_dir}")

    for audio_file in audio_files:
        # Don't convert files that are already in the output directory
        if audio_file.parent.name == OUTPUT_SUBDIR:
            continue
        convert_audio_file(audio_file, output_dir, profile)

    info("Batch conversion complete.")


# --- CLI ---
def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Batch convert audio files.")
    parser.add_argument("path", type=Path, help="Path to the directory with audio files.")
    parser.add_argument("--profile", type=str, required=True, choices=PROFILES.keys(), help="Conversion profile to use.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_args()
    global OVERWRITE, DRY_RUN
    OVERWRITE = args.overwrite
    DRY_RUN = args.dry_run

    batch_convert(args.path, args.profile)


if __name__ == "__main__":
    main()


# :: Usage Example (run interactively) ::
# cd ~/Repos/pc-env/docker/audio-convert
# docker compose build --no-cache  # (only when Dockerfile changes)
# docker compose run --rm audioconvert

# --- Inside the container ---

# audio-normal "/mnt/hdd-01/path/to/your/audio/folder"
# audio-comp "/mnt/hdd-01/path/to/your/audio/folder"

# audio-comp "/mnt/hdd-01/_Downloads/_Audio (YouTube)/[VchiBan]"
# audio-comp "/mnt/hdd-01/_Downloads/_Audio (YouTube)/[Critical Role]/Campaign 1 - Vox Machina"
