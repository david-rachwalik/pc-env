#!/usr/bin/env python3
"""
Batch convert audio files to different formats using ffmpeg.

This script scans a directory for audio files and converts them using predefined
profiles. It intelligently handles album art by probing the file first:
- If album art is present, it's copied directly.
- If no art is found, it's cleanly omitted.
- If audio filters are used, it correctly structures the ffmpeg command to
  avoid stream mapping conflicts, which was the primary challenge.

Usage:
  python3 convert-audio.py /path/to/folder --profile <profile_name>

Profiles:
  - normal: 128kbps, 44.1kHz, stereo
  - audiobook: 64kbps, 44.1kHz, mono, normalized audio
"""
import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# --- Configuration ---
AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus"}
OUTPUT_SUBDIR = "_converted"

# Script-wide settings (set in main)
OVERWRITE = False
DRY_RUN = False

PROFILES = {
    "music": {
        "format": "mp3",
        "bitrate": "128k",
        "sample_rate": "44100",
        "channels": 2,
        "filters": "",
    },
    "music-clean": {
        "format": "mp3",
        "bitrate": "128k",
        "sample_rate": "44100",
        "channels": 2,
        # A more gentle filter chain for music:
        # 1. highpass:  Removes very low-end rumble below 40Hz, preserving more bass frequencies than the vocal filter
        # 2. afftdn:  Applies very light noise reduction
        # 3. loudnorm:  Normalize to a standard loudness without extra compression
        "filters": "highpass=f=40,afftdn=nr=10:nf=-30,loudnorm",
    },
    "vocal": {
        "format": "mp3",
        "bitrate": "64k",
        "sample_rate": "44100",
        "channels": 1,
        "filters": "loudnorm",
    },
    "vocal-clean": {
        "format": "mp3",
        "bitrate": "64k",
        "sample_rate": "44100",
        "channels": 1,
        # Chain of filters:
        # 1. highpass:  Remove low-frequency rumble/hum below 80Hz
        # 2. afftdn:  Apply gentle broadband noise reduction
        # 3. acompressor:  Smooth out volume spikes
        # 4. loudnorm:  Normalize to a standard loudness
        "filters": "highpass=f=80,afftdn=nr=12:nf=-25,acompressor=threshold=0.089:ratio=9:attack=20:release=250,loudnorm",
    },
}


# --- Utilities ---
def info(msg: str):
    """Logs an informational message to stdout."""
    print(f"[INFO] {msg}")


def warn(msg: str):
    """Logs a warning message to stderr."""
    print(f"[WARN] {msg}", file=sys.stderr)


def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Executes a command, logging it and handling dry runs."""
    # Using shlex.join for a safe, accurate representation of the command in log
    cmd_str = shlex.join(cmd)
    if DRY_RUN:
        info(f"Dry Run Command:  {cmd_str}")
        return subprocess.CompletedProcess(cmd, 0)

    info(f"Running Command:  {cmd_str}")
    try:
        return subprocess.run(cmd, check=check, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        warn(f"Command failed with exit code {e.returncode}")
        warn(f"Stderr: {e.stderr.strip()}")
        warn(f"Stdout: {e.stdout.strip()}")
        raise


# --- FFprobe & FFmpeg Logic ---
def _has_video_stream(input_path: Path) -> bool:
    """Uses ffprobe to determine if the input file contains a video stream."""
    info(f"  Probing for video stream...")
    try:
        probe_cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "v",
            str(input_path),
        ]
        probe_result = run_command(probe_cmd)
        probe_data = json.loads(probe_result.stdout)
        if probe_data.get("streams"):
            info("  -> Video stream found.")
            return True
    except (subprocess.CalledProcessError, json.JSONDecodeError, IndexError) as e:
        warn(f"Could not probe for video stream in {input_path.name}. Proceeding as if there is none. Reason: {e}")

    info("  -> No video stream found.")
    return False


def _build_ffmpeg_command(input_path: Path, output_path: Path, profile: Dict[str, Any], has_video: bool) -> List[str]:
    """
    Constructs the ffmpeg command list with correct argument order.

    The key to avoiding errors is to define all stream mappings first,
    then define the codecs and settings for those mapped streams.
    """
    cmd = ["ffmpeg", "-i", str(input_path)]

    # --- Step 1: Define all stream mappings ---
    audio_filters = profile["filters"]
    if audio_filters:
        # Use -filter_complex to apply filters and map its output
        filter_graph = f"[0:a]{audio_filters}[a_out]"
        cmd.extend(["-filter_complex", filter_graph, "-map", "[a_out]"])
        # info("Applied audio filters via -filter_complex.")
    else:
        # No filters, so map the original audio stream directly
        cmd.extend(["-map", "0:a"])

    if has_video:
        # If a video stream exists, map it
        cmd.extend(["-map", "0:v?"])

    # --- Step 2: Define codecs and settings for the mapped streams ---
    if has_video:
        # Use the efficient 'copy' codec for the video stream
        # info("Video stream found.  Copying directly.")
        cmd.extend(["-c:v", "copy", "-disposition:v", "attached_pic"])
    else:
        # info("No video stream found.")
        cmd.append("-vn")

    # Configure the audio stream's encoding
    cmd.extend(
        [
            "-c:a",
            profile["format"],
            "-ar",
            profile["sample_rate"],
            "-ac",
            str(profile["channels"]),
            "-b:a",
            profile["bitrate"],
        ]
    )

    # --- Step 3: Define the output file ---
    cmd.append(str(output_path))
    return cmd


# --- Conversion Logic ---
def get_audio_files(path: Path) -> List[Path]:
    """Find all audio files in the specified directory (non-recursive)."""
    info(f"Searching for audio files in {path} (non-recursive)...")
    files = []
    for ext in AUDIO_EXTS:
        files.extend(path.glob(f"*{ext}"))

    info(f"Found {len(files)} audio file(s) to process.")
    return files


def convert_audio_file(input_path: Path, output_dir: Path, profile: Dict[str, Any]):
    """Probes, builds, and executes the ffmpeg command for a single file."""
    file_start_time = time.monotonic()
    output_filename = f"{input_path.stem}.{profile['format']}"
    output_path = output_dir / output_filename

    info(f"Converting: {input_path.name}")

    if output_path.exists() and not OVERWRITE:
        info(f"  -> Skipping, output file already exists: {output_path.name}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    # Probe the file for a video stream (album/thumbnail art)
    has_video = _has_video_stream(input_path)
    # Build and run the ffmpeg command
    cmd = _build_ffmpeg_command(input_path, output_path, profile, has_video)
    run_command(cmd)

    elapsed_time = time.monotonic() - file_start_time
    info(f"  -> Successfully converted in {elapsed_time:.2f}s: {output_path.name}")


def batch_convert(path: Path, profile_name: str):
    """Batch convert all audio files in a directory."""
    batch_start_time = time.monotonic()
    if not path.is_dir():
        warn(f"Error: Source path '{path}' is not a directory.")
        sys.exit(1)

    profile = PROFILES.get(profile_name)
    if not profile:
        # This should not happen with argparse choices, but is good practice
        warn(f"Error: Profile '{profile_name}' not found.")
        sys.exit(1)

    info(f"Starting batch conversion with profile: '{profile_name}'")
    info(f"Source directory: {path}")

    audio_files = get_audio_files(path)
    if not audio_files:
        warn("No audio files found to convert.")
        return

    output_dir = path / OUTPUT_SUBDIR
    info(f"Output directory: {output_dir}")

    for i, audio_file in enumerate(audio_files, 1):
        info(f"\n--- Processing file {i} of {len(audio_files)} ---")
        try:
            convert_audio_file(audio_file, output_dir, profile)
        except Exception as e:
            # The 'raise' in run_command will stop the script, but this catches other errors
            warn(f"FATAL: A critical error occurred while processing {audio_file.name}. Halting. Reason: {e}")
            sys.exit(1)

    total_elapsed_time = time.monotonic() - batch_start_time
    info(f"\n--- Batch conversion complete in {total_elapsed_time:.2f}s ---")


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

# music-clean "/mnt/hdd-01/path/to/your/audio/folder"
# vocal-clean "/mnt/hdd-01/path/to/your/audio/folder"

# vocal-clean "/mnt/hdd-01/_Downloads/_Audio (YouTube)/[VchiBan]"
# vocal-clean "/mnt/hdd-01/_Downloads/_Audio (YouTube)/[Critical Role]/Campaign 1 - Vox Machina"

# python /app/dev/convert-audio.py --profile vocal-clean "/mnt/hdd-01/_Downloads/_Audio (YouTube)/[Critical Role]/Campaign 1 (test)"
