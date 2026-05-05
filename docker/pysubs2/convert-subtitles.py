#!/usr/bin/env python3
"""
Batch convert subtitle (and video) folders -> .srt using pysubs2 with aggressive ASS cleanup.

Usage:
  python3 convert-subtitles.py /path/to/folder

Behavior:
 - If the folder contains video files (mkv/mp4/...), the script will scan videos and extract subtitle tracks.
 - Text subtitle tracks are converted to cleaned .srt.
 - Image-based tracks (.sup/.idx/.sub) will be extracted and the script will automatically
   attempt to convert them to .srt using `subtitleedit`.
 - The script is idempotent: it skips work when output files already exist.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import pysubs2

# ------------------------ Configuration ------------------------
VIDEO_EXTS = {".mkv", ".mp4", ".m2ts", ".ts", ".webm", ".avi", ".mov"}
TEXT_EXTS = {".ass", ".ssa", ".srt", ".vtt", ".ttml", ".dfxp"}
IMAGE_EXTS = {".idx", ".sub", ".sup"}  # PGS / VobSub families

# --- Script-wide settings (set in main) ---
OVERWRITE = False
DRY_RUN = False

# --- Tuning ---
MAX_GAP_MS = 200
SMALL_DUR_MS = 150
SMALL_CHAR_LEN = 2
MAX_FILENAME_LEN = 240  # Safe limit for most filesystems, including encrypted ones

# --- Regex used by cleaning pipeline ---
KARAOKE_RE = re.compile(r"{\\[kK](?:f|o|t)?\d+}")
BRACE_RE = re.compile(r"{[^}]*}")
HTML_TAG_RE = re.compile(r"<[^>]+>")
INLINE_ESCAPES_RE = re.compile(r"\\[Nn]")
MULTISPACE_RE = re.compile(r"[ \t\u00A0]+")


# ------------------------ Tool Paths ------------------------
def require_tool(name: str) -> str:
    """Find a tool on the PATH, or exit with an error if it's not found."""
    path = shutil.which(name)
    if not path:
        warn(f"Required command-line tool not found in PATH: {name}")
        warn("Please ensure this tool is installed and accessible.")
        sys.exit(1)
    return path


# These are validated at script startup
MKVMERGE = require_tool("mkvmerge")
MKVEXTRACT = require_tool("mkvextract")
FFMPEG = require_tool("ffmpeg")
SUBTITLEEDIT = require_tool("subtitleedit")


# ------------------------ Utilities ------------------------
def info(msg: str):
    print(f"[INFO] {msg}")


def warn(msg: str):
    print(f"[WARN] {msg}", file=sys.stderr)


def run_command(cmd: List[str], capture_output: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command, raise on non-zero exit while printing a helpful message."""
    # info(f"Running command: {' '.join(cmd)}")
    try:
        return subprocess.run(
            cmd,
            check=check,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        warn(f"Command failed: {' '.join(cmd)}")
        if capture_output:
            # warn(f"stdout: {e.stdout}\nstderr: {e.stderr}")
            warn(f"stderr: {e.stderr.strip()}")
        raise


def is_writable(path: Path) -> bool:
    """Check if a directory is writable by creating and deleting a test file."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".pysubs2_write_test"
        test_file.write_text("x")
        test_file.unlink()
        return True
    except Exception:
        return False


# ------------------------ Cleaning & Merge Pipeline ------------------------
def clean_ass_text(text: str) -> str:
    """Strip karaoke/override blocks, HTML tags and normalize whitespace."""
    if not text:
        return ""
    text = INLINE_ESCAPES_RE.sub("\n", text)
    text = KARAOKE_RE.sub("", text)
    text = BRACE_RE.sub("", text)
    text = HTML_TAG_RE.sub("", text)
    lines = [MULTISPACE_RE.sub(" ", l).strip() for l in text.splitlines()]
    text = "\n".join([l for l in lines if l != ""])
    return text.strip()


def duration_ms(event) -> int:
    return int(event.end - event.start)


def merge_events(a, b):
    """Merge two subtitle events into one."""
    new = a.copy()
    new.end = max(a.end, b.end)
    sep = "\n" if ("\n" in a.text or "\n" in b.text) else " "
    new.text = (a.text.rstrip() + sep + b.text.lstrip()).strip()
    return new


def process_subs(subs: pysubs2.SSAFile) -> List[pysubs2.SSAEvent]:
    """Clean, merge, and collapse subtitle events."""
    for ev in subs:
        ev.text = clean_ass_text(ev.text)

    events = [e for e in subs.events if e.text.strip()]
    events.sort(key=lambda e: (e.start, e.end))
    if not events:
        return []

    # Dedupe adjacent identicals
    deduped = []
    if events:
        prev = events[0]
        for ev in events[1:]:
            if ev.text == prev.text and ev.start <= prev.end + MAX_GAP_MS:
                prev.end = max(prev.end, ev.end)
            else:
                deduped.append(prev)
                prev = ev
        deduped.append(prev)
    events = deduped

    # Merge close/overlapping fragments
    merged = []
    if events:
        cur = events[0]
        for ev in events[1:]:
            if ev.start <= cur.end + MAX_GAP_MS:
                cur = merge_events(cur, ev)
            else:
                merged.append(cur)
                cur = ev
        merged.append(cur)
    events = merged

    # Collapse tiny fragments into neighbors
    final = []
    i = 0
    n = len(events)
    while i < n:
        ev = events[i]
        ev_text_len = len(ev.text.replace("\n", ""))
        ev_dur = duration_ms(ev)
        if (ev_text_len <= SMALL_CHAR_LEN or ev_dur <= SMALL_DUR_MS) and n > 1:
            if i > 0:
                final[-1] = merge_events(final[-1], ev)
            elif i + 1 < n:
                events[i + 1] = merge_events(ev, events[i + 1])
        else:
            final.append(ev)
        i += 1

    # Final normalization and dedupe
    out = []
    if final:
        out.append(final[0])
        for ev in final[1:]:
            ev.text = "\n".join(line.strip() for line in ev.text.splitlines() if line.strip())
            if out[-1].text == ev.text and ev.start <= out[-1].end + MAX_GAP_MS:
                out[-1].end = max(out[-1].end, ev.end)
            else:
                out.append(ev)
    return out


# ------------------------ I/O & Conversion Helpers ------------------------
def convert_ass_to_srt(input_path: Path, output_path: Path) -> bool:
    """Load any subtitle file, run cleaning pipeline, and save as SRT."""
    try:
        subs = pysubs2.load(str(input_path))
    except Exception as e:
        warn(f"Failed to load {input_path}: {e}")
        return False

    processed = process_subs(subs)
    if not processed:
        warn(f"No text after processing: {input_path}")
        return False

    outsubs = pysubs2.SSAFile()
    setattr(outsubs, "events", processed)

    if DRY_RUN:
        info(f"[DRY-RUN] Would convert: {input_path.name} -> {output_path.name} ({len(processed)} lines)")
        return True

    outsubs.save(str(output_path), format_="srt")
    info(f"Converted: {input_path.name} -> {output_path.name} ({len(processed)} lines)")
    return True


def _generate_unique_filepath(
    base_stem: str,
    out_dir: Path,
    lang_code: str,
    tag: str,
    ext: str,
    generated_paths: List[Path],
) -> Path:
    """
    Generates a unique, Plex-compliant, and length-safe filepath.
    Handles filename collisions by appending a counter (_2, _3, etc.).
    """
    final_name_part = f".{lang_code}"
    if tag:
        final_name_part += f".{tag}"

    counter = 1
    while True:
        current_suffix = f"_{counter}" if counter > 1 else ""

        # Dynamically calculate the max length for the base name
        suffix_len = len(final_name_part) + len(current_suffix) + len(ext)
        max_base_len = MAX_FILENAME_LEN - suffix_len
        truncated_stem = base_stem[:max_base_len]

        out_path = out_dir / f"{truncated_stem}{final_name_part}{current_suffix}{ext}"

        # A path is unique if it's not in our list for this run, AND
        # it either doesn't exist, or we're in overwrite mode.
        if out_path not in generated_paths and not (out_path.exists() and not OVERWRITE):
            break
        counter += 1

    return out_path


def extract_subs_from_mkv(mkv_path: Path, out_dir: Path) -> List[Path]:
    """
    Extracts subs and attachments from an MKV file.
    - Filters for English or undefined language subtitle tracks.
    - Generates Plex-compliant, length-safe, and unique filenames.
    - Returns a list of all file paths created.
    """
    extracted: List[Path] = []
    info(f"Parsing track and attachment list for {mkv_path.name}")
    try:
        cp = run_command([MKVMERGE, "-J", str(mkv_path)], capture_output=True, check=False)
        if cp.returncode != 0 and not cp.stdout:
            warn(f"mkvmerge failed for {mkv_path.name} with no output. Is it a valid MKV?")
            return extracted
        data = json.loads(cp.stdout)
    except Exception as e:
        warn(f"Failed to run or parse mkvmerge output for {mkv_path}: {e}")
        return extracted

    # --- Extract Subtitle Tracks ---
    # List prevents filename collisions from multiple tracks within same video file
    generated_filenames_this_run: List[Path] = []
    tracks = data.get("tracks", [])
    if not tracks:
        warn(f"No tracks found in mkvmerge output for {mkv_path.name}")

    for track in tracks:
        # Filter for English (eng/en) or Undefined language tracks
        if track.get("type") != "subtitles":
            continue
        props = track.get("properties", {})
        lang = props.get("language")
        if lang and lang not in ("eng", "en"):
            continue

        tid = track.get("id")
        codec_id = (props.get("codec_id") or "").lower()
        track_name = (props.get("track_name") or "").strip()

        # --- Determine File Extension ---
        if "s_text" in codec_id or "ass" in codec_id or "srt" in codec_id:
            ext = ".ass"
        elif "s_hdmv/pgs" in codec_id:
            ext = ".sup"
        elif "s_vobsub" in codec_id:
            ext = ".idx"  # VobSub is a pair (.idx + .sub)
        else:
            warn(f"Skipping unsupported subtitle codec '{codec_id}' for track {tid} in {mkv_path.name}")
            continue

        # --- Descriptive Tagging Logic ---
        sanitized_name = re.sub(r"[^a-zA-Z0-9]+", "_", track_name).lower().strip("_")
        tag = ""
        # Define keywords for track name matching
        cc_keywords = {"caption", "cc", "sdh"}
        song_keywords = {"song", "sign"}
        forced_keywords = {"forced"}
        # Broad matching for various track types
        if any(kw in sanitized_name for kw in cc_keywords):
            tag = "cc"
        elif any(kw in sanitized_name for kw in song_keywords):
            tag = "songs"
        elif any(kw in sanitized_name for kw in forced_keywords):
            tag = "forced"

        # --- Filename Generation ---
        lang_code = "eng" if lang in ("eng", "en") else "und"
        out_path = _generate_unique_filepath(mkv_path.stem, out_dir, lang_code, tag, ext, generated_filenames_this_run)
        generated_filenames_this_run.append(out_path)

        if out_path.exists() and not OVERWRITE:
            info(f"Skipping track (exists): {out_path.name}")
            extracted.append(out_path)
            continue

        info(f"Extracting track {tid} ('{track_name or 'Untitled'}') -> {out_path.name}")
        if not DRY_RUN:
            try:
                # WORKAROUND: mkvextract doesn't handle multi-part extensions well.
                # Extract to a simple temp name, then rename.
                temp_path = out_path.with_name(f"temp_{tid}{ext}")

                # For VobSub, mkvextract needs the base name and creates both .idx and .sub
                dest_arg = temp_path.with_suffix("") if ext == ".idx" else temp_path

                run_command([MKVEXTRACT, str(mkv_path), "tracks", f"{tid}:{dest_arg}"], check=False)

                # Rename the extracted file(s) to the desired final name
                if ext == ".idx":
                    # VobSub creates two files, rename both
                    temp_idx = temp_path.with_suffix(".idx")
                    temp_sub = temp_path.with_suffix(".sub")
                    final_sub_path = out_path.with_suffix(".sub")
                    if temp_idx.exists():
                        temp_idx.rename(out_path)
                    if temp_sub.exists():
                        temp_sub.rename(final_sub_path)
                elif temp_path.exists():
                    # For all other types, just rename the one file
                    temp_path.rename(out_path)
                else:
                    warn(f"Extraction command ran, but temp file not found: {temp_path}")

            except Exception as e:
                warn(f"Failed to extract track {tid} from {mkv_path.name}: {e}")

        extracted.append(out_path)

    # --- Extract Attachments (e.g., fonts) ---
    for att in data.get("attachments", []):
        att_id = att["id"]
        att_name = att.get("file_name")
        if not att_name:
            warn(f"Skipping attachment {att_id} in {mkv_path.name} due to missing filename.")
            continue

        # Sanitize attachment name and prefix with video stem to avoid collisions
        safe_att_name = "".join(c for c in att_name if c.isalnum() or c in "._-")
        final_name = f"{mkv_path.stem}_{safe_att_name}"

        # Use the unique path generator without lang/tag to place it in the extraction dir
        out_path = _generate_unique_filepath(final_name, out_dir, "", "", "", generated_filenames_this_run)
        generated_filenames_this_run.append(out_path)

        if out_path.exists() and not OVERWRITE:
            info(f"Skipping attachment (exists): {out_path.name}")
            continue

        info(f"Extracting attachment {att_id} -> {out_path.name}")
        if not DRY_RUN:
            try:
                run_command([MKVEXTRACT, str(mkv_path), "attachments", f"{att_id}:{out_path}"], check=False)
            except Exception as e:
                warn(f"Failed to extract attachment {att_id} from {mkv_path.name}: {e}")

        extracted.append(out_path)

    return extracted


def extract_subs_with_ffmpeg(video_path: Path, out_dir: Path) -> List[Path]:
    """Use ffmpeg to extract subtitle streams from non-MKV containers (best-effort)."""
    extracted: List[Path] = []
    for idx in range(0, 8):
        out_path = out_dir / f"{video_path.stem}_ffmpeg_track_{idx}.srt"
        if out_path.exists() and not OVERWRITE:
            info(f"Skipping extraction (exists): {out_path.name}")
            extracted.append(out_path)
            continue

        try:
            cmd = [FFMPEG, "-y" if OVERWRITE else "-n", "-i", str(video_path), "-map", f"0:s:{idx}", "-c:s", "srt", str(out_path)]
            if DRY_RUN:
                info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
                continue

            cp = run_command(cmd, capture_output=True, check=False)
            if out_path.exists() and out_path.stat().st_size > 0:
                info(f"Extracted with ffmpeg: {out_path.name}")
                extracted.append(out_path)
            elif out_path.exists():
                out_path.unlink()  # Clean up empty file
        except Exception as e:
            warn(f"ffmpeg extraction failed for stream {idx} of {video_path.name}: {e}")

    return extracted


def try_convert_image_sub_to_srt(image_sub_path: Path, srt_dir: Path) -> Optional[Path]:
    """Attempt to OCR an image-based subtitle file to .srt using Subtitle Edit."""
    srt_output_path = srt_dir / f"{image_sub_path.stem}.srt"
    if srt_output_path.exists() and not OVERWRITE:
        info(f"Skipping OCR (exists): {srt_output_path.name}")
        return srt_output_path

    try:
        info(f"Attempting OCR with Subtitle Edit on {image_sub_path.name}")
        # https://github.com/SubtitleEdit/subtitleedit-cli
        # subtitleedit <input_file> <format_name> /outputfilename:<full_path>
        cmd = [
            SUBTITLEEDIT,
            str(image_sub_path),
            "subrip",  # format name for .srt
            f"/outputfilename:{srt_output_path}",
        ]
        if OVERWRITE:
            cmd.append("/overwrite")

        if DRY_RUN:
            info(f"[DRY-RUN] Would run OCR: {' '.join(cmd)}")
            return srt_output_path

        run_command(cmd, capture_output=True)

        if srt_output_path.exists():
            info(f"Successfully OCR'd to: {srt_output_path.name}")
            return srt_output_path
        else:
            warn(f"OCR command ran, but expected output file not found: {srt_output_path}")

    except Exception as e:
        warn(f"OCR failed for {image_sub_path.name}: {e}")

    return None


# ------------------------ High-Level Flow ------------------------
def find_files(path: Path, exts: set[str]) -> List[Path]:
    """Find all files in a path matching a set of extensions (recursive)."""
    if path.is_file():
        return [path] if path.suffix.lower() in exts else []

    found: List[Path] = []
    for e in exts:
        found.extend(path.rglob(f"*{e}"))
    return sorted(list(set(found)))


def scan_videos_and_extract(path: Path, extraction_dir: Path):
    """
    Scans a path for video files and extracts their subtitle tracks and attachments.
    This function populates the `_extracted_subs` directory but does not return anything.
    """
    videos_to_scan = find_files(path, VIDEO_EXTS)
    if not videos_to_scan:
        return

    info(f"Found {len(videos_to_scan)} video file(s) to scan for subtitles.")
    for video in videos_to_scan:
        info(f"--- Processing video: {video.name} ---")
        if video.suffix.lower() == ".mkv":
            extract_subs_from_mkv(video, extraction_dir)
        else:
            extract_subs_with_ffmpeg(video, extraction_dir)


def batch_convert(path: Path):
    """
    Main orchestration function.
    1. Creates output directories.
    2. Scans for and extracts subtitles from all videos.
    3. Finds all subtitle files (text and image based).
    4. Converts them all to cleaned .srt files.
    """
    if not path.exists():
        warn(f"Error: Input path does not exist: {path}")
        return

    base_path = path.parent if path.is_file() else path
    extraction_dir = base_path / "_extracted_subs"
    srt_dir = base_path / "_converted_subs"
    if not DRY_RUN:
        extraction_dir.mkdir(exist_ok=True)
        srt_dir.mkdir(exist_ok=True)

    # --- Phase 1: Scan videos and extract all raw subtitle tracks ---
    scan_videos_and_extract(path, extraction_dir)

    # --- Phase 2: Collect all subtitle files to be processed ---
    all_subs_to_process = find_files(extraction_dir, TEXT_EXTS | IMAGE_EXTS)
    if not all_subs_to_process:
        info("No subtitle files found to process.")
        return

    # --- Phase 3: Process and convert every collected subtitle file ---
    info(f"Found {len(all_subs_to_process)} total subtitle file(s) to process.")
    success = skipped = failed = 0

    # List to prevent SRT filename collisions in the final output directory
    generated_srt_paths_this_run: List[Path] = []

    for sub_file in all_subs_to_process:
        # Deconstruct the source filename to get the parts for the new SRT name
        # e.g., "Movie.eng.sdh.ass" -> stem="Movie", lang="eng", tag="sdh"
        parts = sub_file.stem.split(".")
        base_stem = parts[0]
        lang_code = parts[1] if len(parts) > 1 else "und"
        tag = parts[2] if len(parts) > 2 else ""

        # Generate a unique path for the final .srt file
        srt_output_path = _generate_unique_filepath(base_stem, srt_dir, lang_code, tag, ".srt", generated_srt_paths_this_run)

        if srt_output_path.exists() and not OVERWRITE:
            info(f"Skipping conversion (exists): {srt_output_path.name}")
            skipped += 1
            continue

        # Add the generated path to our list to prevent collisions in this run
        generated_srt_paths_this_run.append(srt_output_path)

        if sub_file.suffix.lower() in TEXT_EXTS:
            if convert_ass_to_srt(sub_file, srt_output_path):
                success += 1
            else:
                failed += 1

        elif sub_file.suffix.lower() in {".idx", ".sup"}:
            # Pass the pre-calculated unique path to the OCR function
            if try_convert_image_sub_to_srt(sub_file, srt_output_path):
                success += 1
            else:
                failed += 1

    info(f"Done. Succeeded: {success}, Skipped: {skipped}, Failed: {failed}.")


# ------------------------ CLI ------------------------
def main():
    """Parses command-line arguments and kicks off the conversion process."""
    global OVERWRITE, DRY_RUN

    p = argparse.ArgumentParser(
        description="Scan folder (videos/subs) and convert subtitles to cleaned .srt (idempotent).",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Usage Example:
  # Run on a directory of videos
  python3 convert-subtitles.py "/path/to/videos"

  # Run in dry-run mode to see what would happen
  python3 convert-subtitles.py --dry-run "/path/to/videos"

  # Force overwrite of all existing extracted and converted files
  python3 convert-subtitles.py --overwrite "/path/to/videos"
""",
    )
    p.add_argument("path", type=Path, help="Folder or file to scan (recursive).")
    p.add_argument("--overwrite", action="store_true", help="Force re-extraction and re-conversion of existing files.")
    p.add_argument("--dry-run", action="store_true", help="Log what would be done without changing any files.")
    args = p.parse_args()

    # Set global flags
    OVERWRITE = args.overwrite
    DRY_RUN = args.dry_run

    if not args.path.exists():
        warn(f"Error: Input path does not exist: {args.path}")
        sys.exit(1)

    # Ensure we can write to the target directory
    write_dir = args.path.parent if args.path.is_file() else args.path
    if not DRY_RUN and not is_writable(write_dir):
        warn(f"Error: Directory is not writable: {write_dir}")
        sys.exit(1)

    if DRY_RUN:
        info("--- Starting in DRY RUN mode. No files will be changed. ---")

    info(f"Starting batch subtitle conversion in: {args.path}")
    batch_convert(args.path)
    info("All done.")


if __name__ == "__main__":
    main()


# :: Usage Example (run interactively) ::
# cd ~/Repos/pc-env/docker/pysubs2
# docker compose build --no-cache  # (only when Dockerfile changes)
# docker compose run --rm pysubs2

# --- Inside the container ---

# Run the script from the image:
# srt "/mnt/hdd-01/path/to/videos"

# Run the live-mounted dev script:
# python /app/dev/convert-subtitles.py --dry-run "/mnt/hdd-01/path/to/videos"
# python /app/dev/convert-subtitles.py "/mnt/hdd-01/path/to/videos"
