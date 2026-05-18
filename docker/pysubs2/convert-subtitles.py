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
from dataclasses import dataclass
from pathlib import Path
from typing import List

import pysubs2


@dataclass
class SubtitleTrack:
    """Represents a subtitle track to be processed."""

    raw_path: Path  # Path to the extracted (raw) subtitle file
    video_stem: str  # Base name of the associated video file
    tag: str  # Descriptive tag (e.g., 'Signs', 'Full')
    lang: str  # Language code (e.g., 'eng')
    track_type: str  # 'text' or 'image'
    srt_path: Path  # Final destination path for converted .srt file


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


# Executes an external command as a subprocess and returns the result
# - capture_output: If true, prints the standard output and error
# - check: If true, raises a CalledProcessError if the command exits with a non-zero status
def run_command(cmd: List[str], capture_output: bool = True, check: bool = False, cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    """Run a command, raise on non-zero exit while printing a helpful message."""
    # info(f"Running command: {' '.join(cmd)}")
    try:
        # https://docs.python.org/3/library/subprocess.html
        return subprocess.run(
            cmd,
            check=check,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
        )
    except subprocess.CalledProcessError as e:
        warn(f"Command failed: {' '.join(cmd)}")
        if capture_output:
            warn(f"  stdout: {e.stdout.strip()}")
            warn(f"  stderr: {e.stderr.strip()}")
        raise


def is_writable(path: Path) -> bool:
    """Check if a directory is writable by creating and deleting a test file."""
    try:
        test_file = path / ".writable_test"
        test_file.touch()
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
                # Merge with previous if small
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
            if out and out[-1].text == ev.text and ev.start <= out[-1].end + MAX_GAP_MS:
                out[-1].end = max(out[-1].end, ev.end)
            else:
                out.append(ev)
    return out


# ------------------------ I/O & Conversion Helpers ------------------------
def convert_text_sub_to_srt(input_path: Path, output_path: Path) -> bool:
    """Load any text-based subtitle file, run cleaning pipeline, and save as SRT."""
    # Try a list of common encodings for text files
    encodings_to_try = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    subs = None
    for enc in encodings_to_try:
        try:
            subs = pysubs2.load(str(input_path), encoding=enc)
            break  # Stop on the first successful load
        except Exception:
            continue  # Try the next encoding

    if subs is None:
        warn(f"Could not decode text subtitle file: {input_path.name}")
        return False

    processed = process_subs(subs)
    if not processed:
        warn(f"No text after processing: {input_path}")
        return False

    outsubs = pysubs2.SSAFile()
    setattr(outsubs, "events", processed)

    if DRY_RUN:
        info(f"DRY RUN: Would convert {input_path.name} -> {output_path.name} ({len(processed)} lines)")
        return True

    outsubs.save(str(output_path), format_="srt")
    info(f"Converted: {input_path.name} -> {output_path.name} ({len(processed)} lines)")
    return True


def _generate_unique_filename(
    base_stem: str,
    out_dir: Path,
    tag: str,
    lang_code: str,
    ext: str,
    generated_paths: List[Path],
) -> Path:
    """
    Generates a unique, Plex-compliant, and length-safe filepath.
    Handles filename collisions by appending a counter (_2, _3, etc.).
    Ensures uniqueness within the current script run via `generated_paths`.
    Format: [base_stem].[tag].[lang_code].[ext]
    """
    safe_tag = tag.replace(" ", "-")  # Sanitize the tag for shell safety
    suffix = f".{lang_code}{ext}"

    counter = 1
    while True:
        middle_part = f".{safe_tag}" if safe_tag else ""
        if counter > 1:
            middle_part = f"{middle_part}_{counter}"

        # Ensure total filename length doesn't exceed OS limits
        ideal_name = f"{base_stem}{middle_part}{suffix}"
        if len(ideal_name) > MAX_FILENAME_LEN:
            # Calculate the maximum allowed length for the base_stem
            allowed_len = MAX_FILENAME_LEN - len(middle_part) - len(suffix)
            truncated_stem = base_stem[:allowed_len]
            out_path = out_dir / f"{truncated_stem}{middle_part}{suffix}"
        else:
            out_path = out_dir / ideal_name

        # Only check against paths generated this run
        # If it exists on disk but not in generated_paths, it's from a previous
        # run - return it so the skipped logic catches it
        if out_path not in generated_paths:
            break
        counter += 1

    return out_path


def _parse_subtitle_filename(sub_path: Path) -> tuple[str, str, str]:
    """
    Infers tag, language, and stem from a subtitle filename,
    matching the format created by _generate_unique_filepath.
    Example: "Movie.Name.Part.Signs.eng.srt" -> ("eng", "Signs", "Movie.Name.Part")
    Returns (tag, lang_code, base_stem)
    """
    stem = sub_path.stem
    parts = stem.split(".")

    # Set default values for the fallback case (whole stem as base_stem)
    tag = ""
    lang_code = "und"
    base_stem = stem

    # Attempt to parse if the filename structure matches expected format
    # Need at least 2 parts (e.g., "Movie.eng") and last part must look like a lang code (2-3 letter)
    if len(parts) >= 2 and len(parts[-1]) in (2, 3):
        lang_code = parts[-1]
        # If there are only 2 parts, there's no tag
        if len(parts) == 2:
            tag = ""
            base_stem = parts[0]
        # If more than 2 parts, tag is before the lang code
        else:
            tag = parts[-2]
            # Everything before is base stem
            base_stem = ".".join(parts[:-2])

    return tag, lang_code, base_stem


def _create_track_from_loose_file(sub_path: Path, base_path: Path, srt_dir: Path, generated_paths: List[Path]) -> SubtitleTrack:
    """Creates a SubtitleTrack object from a loose subtitle file using filename parsing."""
    tag, lang_code, stem = _parse_subtitle_filename(sub_path)

    # Try to associate with a video file of the same base name, otherwise use its own stem
    video_stem = stem.split(".")[0]
    for video_ext in VIDEO_EXTS:
        if (base_path / f"{video_stem}{video_ext}").exists():
            break  # Found associated video
    else:
        video_stem = stem  # No associated video, use the sub's own stem

    track_type = "image" if sub_path.suffix.lower() in IMAGE_EXTS else "text"

    srt_output_path = _generate_unique_filename(video_stem, srt_dir, tag, lang_code, ".srt", generated_paths)
    generated_paths.append(srt_output_path)

    return SubtitleTrack(sub_path, video_stem, tag, lang_code, track_type, srt_output_path)


def extract_subs_from_mkv(mkv_path: Path, out_dir: Path, srt_dir: Path, generated_paths: List[Path]) -> List[SubtitleTrack]:
    """
    Parses an MKV file, filters for relevant subtitle tracks, and extracts them.
    - Filters for English ('eng', 'en') or undefined ('und') language tracks.
    - Skips extraction if the raw extracted file already exists.
    - Extracts raw track data to a temporary file in `out_dir`.
    - Returns a list of SubtitleTrack objects for further processing.
    """
    all_possible_tracks: List[SubtitleTrack] = []

    # info(f"Parsing track and attachment list for {mkv_path.name}")
    info(f"Attempting to extract subtitles with mkvextract from {mkv_path.name}...")
    try:
        result = run_command([MKVMERGE, "-J", str(mkv_path)])
        data = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        warn(f"Failed to parse mkvmerge output for {mkv_path.name}: {e}")
        return []

    subtitle_tracks = [t for t in data.get("tracks", []) if t.get("type") == "subtitles"]
    if not subtitle_tracks:
        info("No subtitle tracks found in this video.")
        return []
    else:
        info(f"Found {len(subtitle_tracks)} total subtitle track(s).  Beginning extraction...")

    for track in subtitle_tracks:
        track_id = track.get("id")
        props = track.get("properties", {})
        codec = props.get("codec_id")
        lang_code = props.get("language", "und")
        track_name = props.get("track_name", "")  # This is the 'Title' field in mkvinfo
        is_forced = props.get("forced_track", False)
        info(f"(Track ID: {track_id}) using codec '{codec}'")

        # Define extension & track type based on codec
        if codec in ("S_TEXT/ASS", "S_TEXT/SSA"):
            ext, track_type = ".ass", "text"
        elif codec == "S_VOBSUB":
            ext, track_type = ".sub", "image"  # VobSub is a pair (.idx + .sub)
        elif codec == "S_HDMV/PGS":
            ext, track_type = ".sup", "image"
        else:
            warn(f"Skipping unsupported track codec '{codec}' (Track ID: {track_id})")
            continue

        # --- Filtering logic ---
        if lang_code not in {"eng", "en", "und"}:
            info(f"Skipping track #{track_id} with non-target language: '{lang_code}'")
            continue

        # --- Create a tag for the filename ---
        tag_parts = [t.strip() for t in track_name.split(",") if t.strip()]
        if is_forced and "forced" not in tag_parts:
            tag_parts.append("forced")
        tag = ".".join(tag_parts)

        # --- Determine paths ---
        extracted_path = _generate_unique_filename(mkv_path.stem, out_dir, tag, lang_code, ext, generated_paths)
        srt_output_path = _generate_unique_filename(mkv_path.stem, srt_dir, tag, lang_code, ".srt", generated_paths)
        generated_paths.extend([extracted_path, srt_output_path])
        this_track = SubtitleTrack(extracted_path, mkv_path.stem, tag, lang_code, track_type, srt_output_path)

        # --- Extraction ---
        if extracted_path.exists() and not OVERWRITE:
            info(f"Extraction skipped, file already exists: {extracted_path.name}")
        else:
            info(f"    Extracting track #{track_id} ({codec}, lang={lang_code}) to {extracted_path.name}")
            # VobSub is a pair (.idx + .sub); mkvextract creates both for .sub
            extract_target_path = extracted_path.with_suffix(".sub") if codec == "S_VOBSUB" else extracted_path
            # https://mkvtoolnix.download/doc/mkvextract.html
            extract_cmd = [MKVEXTRACT, str(mkv_path), "tracks", f"{track_id}:{extract_target_path}"]
            if DRY_RUN:
                info(f"    DRY-RUN: Would extract to {extracted_path.name}")
                info(f"    DRY-RUN: Would run: {' '.join(extract_cmd)}")
            else:
                try:
                    run_command(extract_cmd, capture_output=False, check=True)
                except subprocess.CalledProcessError as e:
                    if e.returncode == 1:
                        # Exit code 1 means mkvextract warnings occurred but file was likely still extracted
                        warn(f"    Ignoring mkvextract warning (exit code 1) for track #{track_id}.")
                    else:
                        # If extraction fails, we can't process this track further
                        warn(f"    Failed to extract track #{track_id} from {mkv_path.name}: {e}")
                        continue

        # If here, the raw file either existed or was extracted successfully
        all_possible_tracks.append(this_track)

    # --- Extract Attachments (e.g., fonts) ---
    for att in data.get("attachments", []):
        att_name = att.get("file_name")
        att_id = att.get("id")
        out_path = out_dir / f"{mkv_path.stem}.{att_name}"
        if out_path.exists() and not OVERWRITE:
            continue
        try:
            info(f"Extracting attachment: {att_name}")
            if not DRY_RUN:
                run_command([MKVEXTRACT, str(mkv_path), "attachments", f"{att_id}:{out_path}"], capture_output=False)
        except subprocess.CalledProcessError:
            warn(f"Failed to extract attachment {att_name} from {mkv_path.name}")

    return all_possible_tracks


def extract_subs_with_ffmpeg(video_path: Path, out_dir: Path, srt_dir: Path, generated_paths: List[Path]) -> List[SubtitleTrack]:
    """Use ffmpeg to extract subtitle streams from non-MKV containers (best-effort)."""
    all_possible_tracks: List[SubtitleTrack] = []
    info(f"Attempting to extract subtitles with ffmpeg from {video_path.name}...")

    # ffmpeg can extract multiple subtitle streams. We'll loop through potential streams.
    # We don't know language or tags, so we'll have to use generic names.
    for i in range(8):  # Check for up to 8 subtitle streams
        tag = f"stream_{i}"
        lang_code = "und"

        # Define paths for the extracted file and the final SRT
        extracted_path = out_dir / f"{video_path.stem}.{lang_code}.{tag}.srt"
        srt_output_path = _generate_unique_filename(video_path.stem, srt_dir, tag, lang_code, ".srt", generated_paths)
        generated_paths.extend([extracted_path, srt_output_path])

        # Skip if the final converted file already exists
        if srt_output_path.exists() and not OVERWRITE:
            info(f"  Skipping stream {i}: final output {srt_output_path.name} already exists.")
            continue

        if DRY_RUN:
            info(f"  DRY-RUN: Would attempt to extract stream {i} to {extracted_path.name}")
            # In a dry run, we can't know if a stream exists, so we assume it does to show the full plan
            all_possible_tracks.append(SubtitleTrack(extracted_path, video_path.stem, tag, lang_code, "text", srt_output_path))
            continue

        try:
            # ffmpeg command to extract a specific subtitle stream
            cmd = [FFMPEG, "-i", str(video_path), "-map", f"0:s:{i}", "-c:s", "srt", str(extracted_path)]
            if OVERWRITE:
                cmd.insert(1, "-y")  # Add overwrite flag for ffmpeg

            run_command(cmd, check=True)

            # If extraction is successful and the file is not empty, add it to the list
            if extracted_path.exists() and extracted_path.stat().st_size > 0:
                info(f"  Successfully extracted stream {i} to {extracted_path.name}")
                all_possible_tracks.append(SubtitleTrack(extracted_path, video_path.stem, tag, lang_code, "text", srt_output_path))
            else:
                # If the command succeeded but created an empty file, clean it up
                extracted_path.unlink(missing_ok=True)

        except subprocess.CalledProcessError as e:
            # This is expected when a stream doesn't exist, so we can break the loop.
            if "Subtitle stream" in e.stderr and "not found" in e.stderr:
                info(f"  No more subtitle streams found (stopped at index {i}).")
                break
            warn(f"  ffmpeg failed on stream {i} for {video_path.name}: {e.stderr}")

    if not all_possible_tracks:
        info("No new subtitle streams were extracted by ffmpeg for this video.")

    return all_possible_tracks


def convert_image_sub_to_srt(image_sub_path: Path, srt_output_path: Path) -> bool:
    """
    Attempt to OCR an image-based subtitle file to a specified .srt path.
    Copies the extracted subtitle to temporary location to avoid modifying the original.
    The srt_output_path is pre-calculated to be unique. Returns True on success.
    """
    # Check if file is empty, which can happen with sparse "signs" tracks
    if not image_sub_path.exists() or image_sub_path.stat().st_size == 0:
        warn(f"Skipping empty image subtitle file: {image_sub_path.name}")
        return False

    # For VobSub (.sub), the .idx file must be used as the input for tools
    # We must also ensure its companion .sub file is copied
    input_file_for_tool = image_sub_path
    companion_file = None
    if image_sub_path.suffix.lower() == ".sub":
        idx_path = image_sub_path.with_suffix(".idx")
        if not idx_path.exists():
            warn(f"Missing .idx file for VobSub track: {image_sub_path.name}")
            return False
        input_file_for_tool = idx_path
        companion_file = image_sub_path  # The .sub file is the companion to the .idx
    elif image_sub_path.suffix.lower() == ".idx":
        sub_path = image_sub_path.with_suffix(".sub")
        if not sub_path.exists():
            warn(f"Missing .sub file for VobSub track: {image_sub_path.name}")
            return False
        companion_file = sub_path  # The .idx file is the companion to the .sub

    # --- Safe Copy Strategy ---
    # Create a temporary directory to isolate the OCR process
    temp_work_dir = image_sub_path.parent / "_temp_ocr"
    if temp_work_dir.exists():
        shutil.rmtree(temp_work_dir)  # Clean up from any previous failed run
    temp_work_dir.mkdir()

    # Force safe names to avoid subtitleedit CLI argument parsing bugs
    safe_input_name = f"ocr_input{input_file_for_tool.suffix}"
    safe_input_path = temp_work_dir / safe_input_name
    temp_output_path = temp_work_dir / "ocr_output.srt"

    try:
        # Copy the primary file to the safe name
        shutil.copy(input_file_for_tool, safe_input_path)
        # If there's a companion file, it needs the same base name as safe input
        if companion_file:
            safe_companion_path = temp_work_dir / f"ocr_input{companion_file.suffix}"
            shutil.copy(companion_file, safe_companion_path)

        info(f"Attempting OCR using SubtitleEdit on {input_file_for_tool.name}")

        # https://github.com/SubtitleEdit/subtitleedit-cli
        # subtitleedit <input_file> <format_name> /outputfilename:<full_path>
        cmd = [
            SUBTITLEEDIT,
            safe_input_name,  # Use the simple, relative filename (ocr_input.idx)
            "subrip",  # Target format (.srt)
            f"/outputfilename:{temp_output_path.name}",  # Use a simple relative output name
            '/ocrdb:"Latin"',  # Specify OCR database to help with format detection
        ]
        if OVERWRITE:
            cmd.append("/overwrite")

        if DRY_RUN:
            info(f"DRY RUN: Would run command: {' '.join(cmd)}")
            info(f"DRY RUN: Would move {temp_output_path.name} to {srt_output_path.name}")
            return True

        # Run the command from inside the temporary directory
        # Use check=False to silently handle failures without dumping big stack traces
        se_result = run_command(cmd, check=False, cwd=temp_work_dir)

        if se_result.returncode == 0 and temp_output_path.exists():
            shutil.move(temp_output_path, srt_output_path)
            info(f"Successfully OCR'd: {input_file_for_tool.name} -> {srt_output_path.name}")
            return True
        else:
            info(f"OCR with SubtitleEdit failed for {input_file_for_tool.name}.  Falling back to ffmpeg.")

            # ffmpeg needs the original full path
            ffmpeg_cmd = [FFMPEG, "-y" if OVERWRITE else "-n", "-i", str(input_file_for_tool), str(srt_output_path)]
            ff_result = run_command(ffmpeg_cmd, check=False)

            if ff_result.returncode == 0 and srt_output_path.exists() and srt_output_path.stat().st_size > 0:
                info(f"Successfully OCR'd with ffmpeg: {input_file_for_tool.name} -> {srt_output_path.name}")
                return True

            # Intercept the exact empty-track error!
            elif ff_result.returncode != 0 and ff_result.stderr and "Output file does not contain any stream" in ff_result.stderr:
                info(f"Confirmed empty data track: {input_file_for_tool.name} (likely a blank 'Signs' stream).")
                info(f"Creating an empty SRT file to correctly skip this in future runs.")
                srt_output_path.touch()  # This satisfies the script's idempotency requirement!
                return True

            else:
                warn(f"Both OCR methods failed for {input_file_for_tool.name}.")
                if ff_result.stderr:
                    # Print just the last line to avoid spamming the ffmpeg build configuration
                    error_msg = ff_result.stderr.strip().split("\n")[-1]
                    warn(f"  ffmpeg error: {error_msg}")
                return False

    finally:
        # Clean up the entire temporary directory
        if temp_work_dir.exists():
            shutil.rmtree(temp_work_dir)


# ------------------------ High-Level Flow ------------------------
def find_files(path: Path, exts: set[str]) -> List[Path]:
    """Find all files in a path matching a set of extensions (recursive)."""
    if path.is_file():
        return [path] if path.suffix.lower() in exts else []

    found: List[Path] = []
    for e in exts:
        found.extend(path.rglob(f"*{e}"))
    return sorted(list(set(found)))


def batch_convert(path: Path):
    """
    Main orchestration function.
    1. Scans for all video and subtitle files to create a work plan.
    2. Processes each video file and its tracks sequentially (extract -> convert).
    3. Processes loose subtitle files.
    """
    if not path.exists():
        warn(f"Path does not exist: {path}")
        return

    base_path = path.parent if path.is_file() else path
    extraction_dir = base_path / "_extracted_subs"
    srt_dir = base_path / "_converted_subs"
    if not DRY_RUN:
        extraction_dir.mkdir(exist_ok=True)
        srt_dir.mkdir(exist_ok=True)

    success = skipped = failed = 0
    generated_paths: List[Path] = []  # for unique filenames
    processed_raw_paths: set[Path] = set()  # prevent Step 2 from double-processing Step 1

    # --- 1. Find and plan work for all video files ---
    video_files = find_files(base_path, VIDEO_EXTS)
    # Filter out videos inside our working directories
    video_files = [v for v in video_files if "_extracted_subs" not in str(v) and "_converted_subs" not in str(v)]
    info(f"Found {len(video_files)} video file(s) to process.")

    for video_path in video_files:
        info("\n" + f"--- Processing video: {video_path.name} ---")
        video_tracks: List[SubtitleTrack] = []
        if video_path.suffix.lower() == ".mkv":
            video_tracks = extract_subs_from_mkv(video_path, extraction_dir, srt_dir, generated_paths)
        else:
            # Fallback for mp4, etc.
            video_tracks = extract_subs_with_ffmpeg(video_path, extraction_dir, srt_dir, generated_paths)

        if not video_tracks:
            continue

        info(f"Found {len(video_tracks)} track(s) to convert for {video_path.name}.")
        for i, track in enumerate(video_tracks):
            processed_raw_paths.add(track.raw_path)  # Track what is handled in Phase 1

            info(f"  - Processing track {i+1}/{len(video_tracks)} ('{track.tag}')...")
            if not OVERWRITE and track.srt_path.exists():
                info(f"Final SRT already exists, skipping conversion: {track.srt_path.name}")
                skipped += 1
                continue

            # For ffmpeg extractions that go direct to SRT, the work is already done
            if track.raw_path.suffix == ".srt" and track.raw_path.exists():
                shutil.copy(track.raw_path, track.srt_path)
                success += 1
                continue

            if not track.raw_path.exists() or track.raw_path.stat().st_size == 0:
                warn(f"Raw subtitle file does not exist or is empty, cannot convert: {track.raw_path.name}")
                failed += 1
                continue

            if track.track_type == "text":
                if convert_text_sub_to_srt(track.raw_path, track.srt_path):
                    success += 1
                else:
                    failed += 1
            elif track.track_type == "image":
                if convert_image_sub_to_srt(track.raw_path, track.srt_path):
                    success += 1
                else:
                    failed += 1
        info("")  # Newline for readability

    # --- 2. Find and plan work for "loose" subtitle files ---
    loose_files: List[Path] = []
    all_sub_exts = TEXT_EXTS | IMAGE_EXTS

    # Grab from root dir, and explicitly grab from the extraction dir
    for ext in all_sub_exts:
        loose_files.extend(base_path.glob(f"*{ext}"))
        if extraction_dir.exists():
            loose_files.extend(extraction_dir.glob(f"*{ext}"))

    # Cleanup the loose files list
    final_loose_files: List[Path] = []
    for f in sorted(list(set(loose_files))):
        if f in processed_raw_paths:
            continue  # Already handled directly via a video in Phase 1

        # Also skip .idx if the corresponding .sub was handled in Phase 1
        if f.suffix.lower() == ".idx" and f.with_suffix(".sub") in processed_raw_paths:
            continue

        # If it's a .sub file and has an identical .idx file, ignore the .sub
        # (converts via .idx, so don't list the .sub as an independent track)
        if f.suffix.lower() == ".sub":
            idx_buddy = f.with_suffix(".idx")
            if idx_buddy.exists() or idx_buddy.with_suffix(".IDX").exists():
                continue

        final_loose_files.append(f)

    if final_loose_files:
        info(f"\n--- Processing {len(final_loose_files)} loose/extracted subtitle file(s) ---")
        for sub_path in final_loose_files:
            track = _create_track_from_loose_file(sub_path, base_path, srt_dir, generated_paths)

            info(f"  - Processing loose file: {sub_path.name}")
            if not OVERWRITE and track.srt_path.exists():
                info(f"Final SRT already exists, skipping conversion: {track.srt_path.name}")
                skipped += 1
                continue

            if track.track_type == "text":
                if convert_text_sub_to_srt(track.raw_path, track.srt_path):
                    success += 1
                else:
                    failed += 1
            elif track.track_type == "image":
                if convert_image_sub_to_srt(track.raw_path, track.srt_path):
                    success += 1
                else:
                    failed += 1

    info("\n" + "--- All processing complete ---")
    info(f"Done. Succeeded: {success}, Skipped: {skipped}, Failed: {failed}.")
    if failed > 0:
        info("Some files failed to convert. Check warnings above.")
    info("All done.")


# ------------------------ CLI ------------------------
def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Batch convert subtitle folders to .srt using pysubs2 and other tools.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Behavior:
 - Scans for video files (mkv, mp4, etc.) and extracts their subtitle tracks.
 - Also finds 'loose' subtitle files in the root of the target directory.
 - Text-based subtitles (.ass, .ssa) are cleaned and converted to .srt.
 - Image-based subtitles (.sup, .idx/.sub) are OCR'd to .srt using SubtitleEdit.
 - Creates '_extracted_subs' for raw tracks and '_converted_subs' for final .srt files.
 - Idempotent: skips work if the final .srt file already exists.
""",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to a folder containing media files, or a single media file.",
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Overwrite existing extracted and converted files.",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Simulate the process without writing any files.",
    )
    args = parser.parse_args()

    global OVERWRITE, DRY_RUN
    OVERWRITE = args.overwrite
    DRY_RUN = args.dry_run

    if DRY_RUN:
        info("--- DRY RUN MODE ENABLED ---")

    info(f"Starting batch subtitle conversion in: {args.path}")
    batch_convert(args.path)


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
