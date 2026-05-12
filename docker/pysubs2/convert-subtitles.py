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
    """Represents a single subtitle track, from source to destination."""

    source_path: Path  # path to raw subtitle file (e.g., in _extracted_subs)
    video_stem: str  # base name of associated video file (e.g., "My Movie")
    lang_code: str  # ISO 639-2 language code (e.g., "en", "und")
    tag: str  # optional tag (e.g., "forced", "sdh")
    type: str  # "text" or "image"
    srt_path: Path  # final, calculated destination path for .srt file


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
            if out and out[-1].text == ev.text and ev.start <= out[-1].end + MAX_GAP_MS:
                out[-1].end = max(out[-1].end, ev.end)
            else:
                out.append(ev)
    return out


# ------------------------ I/O & Conversion Helpers ------------------------
def convert_text_sub_to_srt(input_path: Path, output_path: Path) -> bool:
    """Load any text-based subtitle file, run cleaning pipeline, and save as SRT."""
    # Try a list of common encodings for text files
    encodings_to_try = ["utf-8", "cp1251", "latin-1"]
    subs = None
    for enc in encodings_to_try:
        try:
            subs = pysubs2.load(str(input_path), encoding=enc)
            break  # Stop on the first successful load
        except Exception:
            continue  # Try the next encoding

    if subs is None:
        warn(f"Failed to load {input_path.name} with any of the attempted encodings.")
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
    Ensures uniqueness within the current script run via `generated_paths`.
    Format: [base_stem].[tag].[lang_code].[ext]
    """
    # Sanitize the tag by replacing spaces with underscores for shell safety
    safe_tag = tag.replace(" ", "-")

    # Start with the video name, then add the descriptive tag first
    name_with_tag = base_stem
    if safe_tag:
        name_with_tag = f"{base_stem}.{safe_tag}"

    # The final name part includes the language
    final_name_part = f".{lang_code}"

    counter = 1
    while True:
        suffix = f"_{counter}" if counter > 1 else ""
        # Combine parts and truncate if necessary to stay within safe limits
        final_name = f"{name_with_tag}{final_name_part}{suffix}{ext}"
        if len(final_name) > MAX_FILENAME_LEN:
            # Truncate the middle part (end of original filename) if too long
            cutoff = len(final_name) - MAX_FILENAME_LEN
            final_name = f"{base_stem[:-cutoff]}{safe_tag}{final_name_part}{suffix}{ext}"

        out_path = out_dir / final_name
        if out_path not in generated_paths:
            break
        counter += 1

    return out_path


def _parse_subtitle_filename(sub_path: Path) -> tuple[str, str, str]:
    """
    Infers language and tag from a subtitle filename.
    Example: "Movie.en.forced.srt" -> ("en", "forced", "Movie")
    Returns (lang_code, tag, stem)
    """
    # For .srt files we want to clean in-place, the stem is the filename without .srt
    if sub_path.suffix.lower() == ".srt":
        stem_parts = sub_path.stem.split(".")
        # Assumes format like "file.eng.tag"
        if len(stem_parts) > 1:
            lang = stem_parts[1]
            tag = ".".join(stem_parts[2:])
            return lang, tag, sub_path.stem
        else:
            # It's just "file.srt", so treat it as cleaning itself
            return sub_path.suffix.strip("."), "", sub_path.stem

    # For other formats, infer from the full stem
    stem = sub_path.stem
    parts = stem.split(".")
    lang_code = "und"
    tag = ""
    if len(parts) > 1:
        # Assume the second to last part is the language
        lang_code = parts[-1] if len(parts) == 2 else parts[-2]
        # Assume the last part is a tag if there are more than 2 parts
        if len(parts) > 2:
            tag = parts[-1]

    return lang_code, tag, stem


def _create_track_from_loose_file(sub_path: Path, base_path: Path, srt_dir: Path, generated_paths: List[Path]) -> SubtitleTrack:
    """Creates a SubtitleTrack object from a loose subtitle file using filename parsing."""
    lang_code, tag, stem = _parse_subtitle_filename(sub_path)

    # Try to associate with a video file of the same base name, otherwise use its own stem
    video_stem = stem.split(".")[0]
    for video_ext in VIDEO_EXTS:
        if (base_path / f"{video_stem}{video_ext}").exists():
            break  # Found associated video
    else:
        video_stem = stem  # No associated video, use the sub's own stem

    track_type = "image" if sub_path.suffix.lower() in IMAGE_EXTS else "text"

    srt_output_path = _generate_unique_filepath(video_stem, srt_dir, lang_code, tag, ".srt", generated_paths)
    generated_paths.append(srt_output_path)

    return SubtitleTrack(sub_path, video_stem, lang_code, tag, track_type, srt_output_path)


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
        extracted_path = _generate_unique_filepath(mkv_path.stem, out_dir, lang_code, tag, ext, generated_paths)
        srt_output_path = _generate_unique_filepath(mkv_path.stem, srt_dir, lang_code, tag, ".srt", generated_paths)
        generated_paths.extend([extracted_path, srt_output_path])
        this_track = SubtitleTrack(extracted_path, mkv_path.stem, lang_code, tag, track_type, srt_output_path)

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
        srt_output_path = _generate_unique_filepath(video_path.stem, srt_dir, lang_code, tag, ".srt", generated_paths)
        generated_paths.extend([extracted_path, srt_output_path])

        # Skip if the final converted file already exists
        if srt_output_path.exists() and not OVERWRITE:
            info(f"  Skipping stream {i}: final output {srt_output_path.name} already exists.")
            continue

        if DRY_RUN:
            info(f"  DRY-RUN: Would attempt to extract stream {i} to {extracted_path.name}")
            # In a dry run, we can't know if a stream exists, so we assume it does to show the full plan
            all_possible_tracks.append(SubtitleTrack(extracted_path, video_path.stem, lang_code, tag, "text", srt_output_path))
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
                all_possible_tracks.append(SubtitleTrack(extracted_path, video_path.stem, lang_code, tag, "text", srt_output_path))
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
    The srt_output_path is pre-calculated to be unique. Returns True on success.
    """
    # Check if file is empty, which can happen with sparse "signs" tracks
    if not image_sub_path.exists() or image_sub_path.stat().st_size == 0:
        warn(f"Skipping empty or missing image subtitle file: {image_sub_path.name}")
        return False

    # For VobSub (.sub), the .idx file must be used as the input for tools
    input_file_for_tool = image_sub_path
    if image_sub_path.suffix.lower() == ".sub":
        idx_path = image_sub_path.with_suffix(".idx")
        if not idx_path.exists():
            warn(f"Cannot perform OCR on '{image_sub_path.name}': Missing corresponding '.idx' file.")
            return False
        input_file_for_tool = idx_path

    # Use a simple, static filename for temporary output of subtitleedit,
    # as it cannot handle complex names (e.g. with periods)
    temp_output_path = image_sub_path.parent / f"temp_ocr_output.srt"

    # https://github.com/SubtitleEdit/subtitleedit-cli
    # subtitleedit <input_file> <format_name> /outputfilename:<full_path>
    cmd = [
        SUBTITLEEDIT,
        # str(input_file_for_tool),
        input_file_for_tool.name,  # Use relative filename
        "subrip",  # format name for .srt
        f"/outputfilename:{temp_output_path}",
        '/ocrdb:"Latin"',  # Explicitly specify the OCR database
    ]
    if OVERWRITE:
        cmd.append("/overwrite")

    if DRY_RUN:
        info(f"DRY-RUN: Would OCR: {input_file_for_tool.name} -> {srt_output_path.name}")
        info(f"DRY-RUN: Would run: {' '.join(cmd)}")
        return True
    else:
        info(f"Attempting OCR using SubtitleEdit on {input_file_for_tool.name}")

    try:
        # run_command(cmd)
        # run_command(cmd, check=True)
        run_command(cmd, check=True, cwd=input_file_for_tool.parent)

        if temp_output_path.exists():
            # Rename the temp output to its true filename
            shutil.move(str(temp_output_path), str(srt_output_path))
            info(f"Successfully OCR'd: {input_file_for_tool.name} -> {srt_output_path.name}")
            return True
        else:
            warn(f"OCR of {input_file_for_tool.name} failed.  Output file not created.")
            return False

    except Exception as e:
        warn(f"An error occurred during OCR for {input_file_for_tool.name}: {e}")
        return False
    finally:
        # Clean up the temporary file this function created (if error left behind)
        if not DRY_RUN:
            temp_output_path.unlink(missing_ok=True)


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

    # --- Phase 1: Scan for all video files and loose subtitle files ---
    videos_to_scan = find_files(path, VIDEO_EXTS)
    all_sub_files = find_files(path, TEXT_EXTS | IMAGE_EXTS)
    loose_sub_files = [f for f in all_sub_files if srt_dir.resolve() not in f.parents and extraction_dir.resolve() not in f.parents and f.suffix != ".sub"]

    if not videos_to_scan and not loose_sub_files:
        info("No video or subtitle files found to process.")
        return

    # --- Phase 2: Process each video file sequentially ---
    if videos_to_scan:
        info(f"Found {len(videos_to_scan)} video file(s) to process.")
        for video_path in videos_to_scan:
            info("")
            info(f"--- Processing video: {video_path.name} ---")
            tracks_to_process: List[SubtitleTrack] = []
            ext = video_path.suffix.lower()

            if ext == ".mkv":
                tracks_to_process = extract_subs_from_mkv(video_path, extraction_dir, srt_dir, generated_paths)
            else:
                tracks_to_process = extract_subs_with_ffmpeg(video_path, extraction_dir, srt_dir, generated_paths)

            if not tracks_to_process:
                info("No new or relevant subtitle tracks found for this video.")
                continue

            info(f"Found {len(tracks_to_process)} track(s) to convert for {video_path.name}.")
            for i, track in enumerate(tracks_to_process):
                info(f"  - Processing track {i+1}/{len(tracks_to_process)} ('{track.tag or track.type}')...")

                if track.srt_path.exists() and not OVERWRITE:
                    info(f"    Skipping, output already exists: {track.srt_path.name}")
                    skipped += 1
                    continue

                result = False
                if track.type == "text":
                    result = convert_text_sub_to_srt(track.source_path, track.srt_path)
                elif track.type == "image":
                    result = convert_image_sub_to_srt(track.source_path, track.srt_path)

                if result:
                    success += 1
                else:
                    failed += 1
            info("")  # Add a blank line for readability after processing all tracks for a video

    # --- Phase 3: Process loose subtitle files ---
    if loose_sub_files:
        info(f"--- Processing {len(loose_sub_files)} loose subtitle file(s) ---")
        for sub_file_path in loose_sub_files:
            track = _create_track_from_loose_file(sub_file_path, base_path, srt_dir, generated_paths)
            info(f"  - Processing loose file: {track.source_path.name}")

            if track.srt_path.exists() and not OVERWRITE:
                info(f"    Skipping, output already exists: {track.srt_path.name}")
                skipped += 1
                continue

            result = False
            if track.type == "text":
                result = convert_text_sub_to_srt(track.source_path, track.srt_path)
            elif track.type == "image":
                result = convert_image_sub_to_srt(track.source_path, track.srt_path)

            if result:
                success += 1
            else:
                failed += 1

    info("--- All processing complete ---")
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
