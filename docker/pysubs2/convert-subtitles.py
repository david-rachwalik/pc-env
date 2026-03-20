#!/usr/bin/env python3
"""
Batch convert subtitle (and video) folders -> .srt using pysubs2 with aggressive ASS cleanup.

Usage:
  python3 convert-subtitles.py /path/to/folder

Behavior:
 - If the folder contains video files (mkv/mp4/...), the script will scan videos and extract subtitle tracks.
 - Text subtitle tracks are converted to cleaned .srt.
 - Image-based tracks (.sup/.idx/.sub) will be extracted and the script will automatically
   attempt to convert them to .srt using `subtitleedit` (for .sup) and `vobsub2srt` (for .idx).
 - The script is idempotent: it skips work when output files already exist.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import pysubs2

# ---------------------- Configuration ----------------------
VIDEO_EXTS = {".mkv", ".mp4", ".m2ts", ".ts", ".webm", ".avi", ".mov"}
TEXT_EXTS = {".ass", ".ssa", ".srt", ".vtt", ".ttml", ".dfxp"}
IMAGE_EXTS = {".idx", ".sub", ".sup"}  # PGS / VobSub families

# Script-wide settings (set in main)
OVERWRITE = False
DRY_RUN = False

# Tuning
MAX_GAP_MS = 200
SMALL_DUR_MS = 150
SMALL_CHAR_LEN = 2

# Regex used by cleaning pipeline
KARAOKE_RE = re.compile(r"{\\[kK](?:f|o|t)?\d+}")
BRACE_RE = re.compile(r"{[^}]*}")
HTML_TAG_RE = re.compile(r"<[^>]+>")
INLINE_ESCAPES_RE = re.compile(r"\\[Nn]")
MULTISPACE_RE = re.compile(r"[ \t\u00A0]+")


# --- Tool Paths ---
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


# ---------------------- Utilities ----------------------
def info(msg: str):
    print(f"[INFO] {msg}")


def warn(msg: str):
    print(f"[WARN] {msg}", file=sys.stderr)


def run_command(cmd: List[str], capture_output: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command, raise on non-zero exit while printing a helpful message."""
    # info(f"Running command: {' '.join(cmd)}")
    try:
        # The 'check' parameter is passed to subprocess.run
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
            warn(f"stdout: {e.stdout}\nstderr: {e.stderr}")
        # Re-raise the exception if check=True
        raise


def is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        test = path / ".pysubs2_write_test"
        test.write_text("x")
        test.unlink()
        return True
    except Exception:
        return False


# ---------------------- Cleaning & merge pipeline (unchanged behavior) ----------------------
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


def merge_events(a, b, join_with_space=True):
    new = a.copy()
    new.end = max(a.end, b.end)
    sep = "\n" if ("\n" in a.text or "\n" in b.text) else " "
    new.text = (a.text.rstrip() + sep + b.text.lstrip()).strip()
    return new


def process_subs(subs: pysubs2.SSAFile, max_gap_ms: int = MAX_GAP_MS, small_dur_ms: int = SMALL_DUR_MS, small_char_len: int = SMALL_CHAR_LEN) -> List:
    """Clean, merge and collapse karaoke fragments. Returns list of SSA events."""
    for ev in subs:
        ev.text = clean_ass_text(ev.text)

    events = [e for e in subs.events if e.text.strip()]
    events.sort(key=lambda e: (e.start, e.end))
    if not events:
        return []

    # Dedupe adjacent identicals
    deduped = []
    prev = events[0]
    for ev in events[1:]:
        if ev.text == prev.text and ev.start <= prev.end + max_gap_ms:
            prev.end = max(prev.end, ev.end)
        else:
            deduped.append(prev)
            prev = ev
    deduped.append(prev)
    events = deduped

    # Merge close/overlapping fragments
    merged = []
    cur = events[0]
    for ev in events[1:]:
        if ev.start <= cur.end + max_gap_ms:
            cur = merge_events(cur, ev)
        else:
            merged.append(cur)
            cur = ev
    merged.append(cur)
    events = merged

    # Collapse tiny karaoke fragments into neighbors
    final = []
    i = 0
    n = len(events)
    while i < n:
        ev = events[i]
        ev_text_len = len(ev.text.replace("\n", ""))
        ev_dur = duration_ms(ev)
        if (ev_text_len <= small_char_len or ev_dur <= small_dur_ms) and n > 1:
            if final and ev.start <= final[-1].end + max_gap_ms:
                final[-1] = merge_events(final[-1], ev)
            elif i + 1 < n and events[i + 1].start <= ev.end + max_gap_ms:
                events[i + 1] = merge_events(ev, events[i + 1])
            else:
                final.append(ev)
        else:
            final.append(ev)
        i += 1

    # Normalize and final dedupe
    out = []
    for ev in final:
        ev.text = "\n".join(line.strip() for line in ev.text.splitlines() if line.strip())
        if out and out[-1].text == ev.text and ev.start <= out[-1].end + max_gap_ms:
            out[-1].end = max(out[-1].end, ev.end)
        else:
            out.append(ev)
    return out


# ---------------------- I/O conversion helpers ----------------------
def convert_ass_to_srt(input_path: Path, output_path: Path) -> bool:
    """Load any subtitle file with pysubs2, run the cleaning/merge pipeline, and save as SRT."""
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
    # assign events at runtime (avoid static-linter issues)
    setattr(outsubs, "events", processed)

    if DRY_RUN:
        info(f"[DRY-RUN] {input_path} -> {output_path} ({len(processed)} lines)")
        return True

    outsubs.save(str(output_path), format_="srt")
    info(f"Converted: {input_path} -> {output_path} ({len(processed)} lines)")
    return True


# ---------------------- MKV & FFmpeg extraction + auto OCR ----------------------
def extract_subs_from_mkv(mkv_path: Path, out_dir: Path) -> List[Path]:
    """Extract subtitle tracks from MKV using mkvmerge/mkvextract.
    Returns list of extracted files (both text and image-based).
    """
    extracted: List[Path] = []
    info(f"Parsing track list for {mkv_path.name}")
    try:
        # run mkvmerge to identify tracks and handle cases where it exits non-zero
        cp = run_command([MKVMERGE, "-J", str(mkv_path)], capture_output=True, check=False)
        if cp.returncode != 0 and not cp.stdout:
            warn(f"mkvmerge failed to identify tracks for {mkv_path.name}.  Exit code: {cp.returncode}")
            if cp.stderr:
                warn(f"mkvmerge stderr: {cp.stderr.strip()}")
            return extracted
        # info(f"Parsing track list for {mkv_path.name}")
        data = json.loads(cp.stdout)
    except Exception as e:
        warn(f"Failed to run or parse mkvmerge output for {mkv_path}: {e}")
        return extracted

    tracks = data.get("tracks", [])
    if not tracks:
        warn(f"No tracks found in mkvmerge output for {mkv_path.name}")
        return extracted

    for track in tracks:
        if track.get("type") != "subtitles":
            continue

        tid = track.get("id")
        codec = (track.get("properties", {}).get("codec_id") or "").lower()
        out_path_base = out_dir / f"{mkv_path.stem}_track{tid}"

        # prefer extracting as text when codec suggests S_TEXT/ASS
        if "s_text" in codec or "ass" in codec or "srt" in codec:
            ext = ".ass" if "ass" in codec else ".srt"
            dest = out_path_base.with_suffix(ext)
            if dest.exists() and not OVERWRITE:
                info(f"Skip extract (exists): {dest.name}")
            else:
                info(f"Extracting text track {tid} -> {dest.name}")
                if not DRY_RUN:
                    try:
                        run_command([MKVEXTRACT, "tracks", str(mkv_path), f"{tid}:{str(dest)}"])
                    except Exception:
                        warn(f"Failed to extract track {tid} from {mkv_path}")
                        continue
            extracted.append(dest)
        elif "s_hdmv/pgs" in codec:
            # probably image-based (PGS)
            dest = out_path_base.with_suffix(".sup")
            if dest.exists() and not OVERWRITE:
                info(f"Skip extract (exists): {dest.name}")
            else:
                info(f"Extracting image-based track {tid} -> {dest.name}")
                if not DRY_RUN:
                    try:
                        run_command([MKVEXTRACT, "tracks", str(mkv_path), f"{tid}:{str(dest)}"])
                    except Exception:
                        warn(f"Failed to extract image track {tid} from {mkv_path}")
                        continue
            extracted.append(dest)
        elif "s_vobsub" in codec:
            # VobSub needs both .idx and .sub files
            idx_dest = out_path_base.with_suffix(".idx")
            if idx_dest.exists() and not OVERWRITE:
                info(f"Skip extract (exists): {idx_dest.name}")
            else:
                info(f"Extracting VobSub track {tid} -> {idx_dest.name}")
                if not DRY_RUN:
                    try:
                        # mkvextract creates both .idx and .sub
                        run_command([MKVEXTRACT, "tracks", str(mkv_path), f"{tid}:{str(idx_dest)}"])
                    except Exception:
                        warn(f"Failed to extract VobSub track {tid} from {mkv_path}")
                        continue
            extracted.append(idx_dest)
    return extracted


def extract_subs_with_ffmpeg(video_path: Path, out_dir: Path) -> List[Path]:
    """Use ffmpeg to try extracting subtitle streams for non-MKV containers.
    This tries to map 0:s:0..n and convert subtitle codec to srt when possible.
    """
    extracted: List[Path] = []
    # try mapping subtitle streams 0:s:0..7 (best-effort)
    for idx in range(0, 8):
        dest = out_dir / f"{video_path.stem}_ffsub{idx}.srt"
        if dest.exists() and not OVERWRITE:
            info(f"Skip ffmpeg extract (exists): {dest.name}")
            extracted.append(dest)
            continue
        # Use -y only if overwriting, otherwise ffmpeg will prompt and hang
        overwrite_args = ["-y"] if OVERWRITE else []
        cmd = [FFMPEG, *overwrite_args, "-hide_banner", "-loglevel", "error", "-i", str(video_path), "-map", f"0:s:{idx}", "-c:s", "srt", str(dest)]
        if not DRY_RUN:
            try:
                run_command(cmd)
                info(f"ffmpeg extracted subtitle stream {idx} -> {dest.name}")
                extracted.append(dest)
            except Exception:
                # assume no more subtitle streams at this index
                break
        else:
            # In dry run, we can't know if ffmpeg would succeed, so we just log the intent
            info(f"[DRY-RUN] Would attempt to extract subtitle stream {idx} with ffmpeg.")
            # We don't append to extracted list in dry-run as the file won't exist
    return extracted


def try_convert_image_sub_to_srt(image_sub_path: Path, srt_output_path: Path) -> Optional[Path]:
    """Attempt to convert an image-based sub file (.sup, .idx) to .srt using Subtitle Edit."""
    if srt_output_path.exists() and not OVERWRITE:
        info(f"Skipping OCR (exists): {srt_output_path.name}")
        return srt_output_path

    # Use Subtitle Edit for all image-based formats (.sup, .idx)
    try:
        info(f"Attempting OCR with Subtitle Edit on {image_sub_path.name}")
        if DRY_RUN:
            info(f"[DRY-RUN] Would run Subtitle Edit on {image_sub_path.name} -> {srt_output_path.name}")
            return srt_output_path  # Pretend it worked for the final report

        # https://github.com/SubtitleEdit/subtitleedit-cli
        # subtitleedit <input_file> <format_name> /outputfilename:<full_path>
        run_command(
            [
                SUBTITLEEDIT,
                str(image_sub_path),
                "subrip",  # format name for .srt
                # f"/outputfolder:{str(srt_output_path.parent)}",
                f"/outputfilename:{str(srt_output_path)}",
            ],
            capture_output=True,
        )
        # - uses the system's Tesseract installation
        # - capture output to hide verbose OCR progress from the main log
        # - use `outputfolder` for batch processing and `outputfilename` for single-file

        if srt_output_path.exists():
            info(f"Converted: {image_sub_path.name} -> {srt_output_path.name} (Subtitle Edit)")
            return srt_output_path
        else:
            warn(f"Subtitle Edit ran but did not produce the expected output: {srt_output_path.name}")
    except Exception:
        warn(f"Subtitle Edit failed during OCR of {image_sub_path.name}")

    return None


# ---------------------- High level flow ----------------------
def find_sub_files(path: Path, exts: List[str]) -> List[Path]:
    """Find files matching extensions (recursive)."""
    if path.is_file():
        return [path] if path.suffix.lower() in exts else []
    found: List[Path] = []
    for e in exts:
        found.extend(list(path.rglob(f"*{e}")))
    # dedupe & sort
    return sorted(list(set(found)))


def scan_videos_and_extract(path: Path, extraction_dir: Path, srt_dir: Path) -> List[Path]:
    """Scan folder for video files, extract subs, run OCR, and return text-subtitle files."""
    found_text_subs: List[Path] = []
    # Find all videos to scan
    videos_to_scan = []
    if path.is_file() and path.suffix.lower() in VIDEO_EXTS:
        videos_to_scan = [path]
    elif path.is_dir():
        for ext in VIDEO_EXTS:
            videos_to_scan.extend(list(path.rglob(f"*{ext}")))

    if not videos_to_scan:
        return []

    info(f"Found {len(videos_to_scan)} video file(s) to scan for subtitles.")

    for video in sorted(list(set(videos_to_scan))):
        if not video.is_file():
            continue
        info(f"Processing video: {video.name}")

        # Extract all subtitle types (text and image)
        extracted_files = []
        if video.suffix.lower() == ".mkv":
            extracted_files = extract_subs_from_mkv(video, extraction_dir)
        else:
            extracted_files = extract_subs_with_ffmpeg(video, extraction_dir)

        # Process the extracted files
        for f in extracted_files:
            if f.suffix.lower() in TEXT_EXTS:
                found_text_subs.append(f)
            elif f.suffix.lower() in IMAGE_EXTS:
                # Define the final SRT path and run OCR
                srt_output_path = srt_dir / f.with_suffix(".srt").name
                srt_file = try_convert_image_sub_to_srt(f, srt_output_path)
                if srt_file:
                    found_text_subs.append(srt_file)

    return found_text_subs


def batch_convert(path: Path):
    """Top-level behavior: find all text subs and convert them to cleaned .srt."""
    if not path.exists():
        warn(f"Path does not exist: {path}")
        return

    # --- Define and create output directories once ---
    base_path = path.parent if path.is_file() else path
    extraction_dir = base_path / "_extracted_subs"
    srt_dir = base_path / "_converted_subs"
    if not DRY_RUN:
        extraction_dir.mkdir(parents=True, exist_ok=True)
        srt_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: Find all subtitle files to process ---
    # Start with text-based subs already on disk
    subs_to_process = find_sub_files(path, list(TEXT_EXTS))
    # Scan for videos, extract their subs, and run OCR
    # (returns a list of text-based subs, original or from OCR)
    extracted_text_subs = scan_videos_and_extract(path, extraction_dir, srt_dir)
    subs_to_process.extend(extracted_text_subs)

    # Deduplicate and sort the final list
    final_subs_list = sorted(list(set(subs_to_process)))

    if not final_subs_list:
        info("No text subtitle files found or extracted to convert.")
        return

    # --- Step 2: Run conversion on the collected list ---
    info(f"Found {len(final_subs_list)} text subtitle(s) to process.")
    success = skipped = failed = 0
    for sub_file in final_subs_list:
        # All final outputs go to the "_converted_subs" directory
        out_file = srt_dir / sub_file.with_suffix(".srt").name

        # --- Idempotency Check: Skip if output already exists and we're not overwriting ---
        if out_file.exists() and not OVERWRITE:
            # Handle case where the source is the same as the destination
            if sub_file.resolve() == out_file.resolve():
                info(f"Skipping (already in output dir): {sub_file.name}")
            else:
                info(f"Skipping (exists in output dir): {out_file.name}")
            skipped += 1
            continue

        # --- Main Conversion/Copy Logic ---
        if sub_file.suffix.lower() == ".srt":
            # Copy existing SRT to the converted folder for consistency
            if not DRY_RUN:
                shutil.copy(sub_file, out_file)
            info(f"Copied to output directory: {out_file.name}")
            success += 1
        else:
            # For non-SRT files, perform the full conversion pipeline
            ok = convert_ass_to_srt(sub_file, out_file)
            if ok:
                success += 1
            else:
                failed += 1
    info(f"Done. Succeeded: {success}, Skipped: {skipped}, Failed: {failed}.")


# ---------------------- CLI ----------------------
def parse_args():
    import argparse

    p = argparse.ArgumentParser(description="Scan folder (videos/subs) and convert subtitles to cleaned .srt (idempotent).")
    p.add_argument("path", help="Folder or file to scan (recursive). Must be accessible from container.")
    p.add_argument("--overwrite", action="store_true", help="Force re-extraction and re-conversion of existing files.")
    p.add_argument("--dry-run", action="store_true", help="Log what would be done without changing any files.")
    args = p.parse_args()
    return Path(args.path), args.overwrite, args.dry_run


def main():
    global OVERWRITE
    global DRY_RUN
    target, overwrite_arg, dry_run_arg = parse_args()
    OVERWRITE = overwrite_arg
    DRY_RUN = dry_run_arg

    if not target.exists():
        warn(f"Target path does not exist: {target}")
        sys.exit(2)

    # Ensure we can write to the target (we create extracted folders & outputs)
    if not DRY_RUN and not is_writable(target.parent if target.is_file() else target):
        warn(f"Target folder is not writable from this process: {target}")
        sys.exit(3)

    if DRY_RUN:
        info("--- Starting DRY RUN ---")

    info(f"Starting batch subtitle conversion in: {target}")
    batch_convert(target)
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

# python /app/dev/convert-subtitles.py "/mnt/hdd-01/_Downloads/_Torrents/Done/That '70s Show (1998) Season 1-8 S01-S08 (1080p BluRay x265 HEVC 10bit AAC 5.1 FreetheFish)/Season 1"
