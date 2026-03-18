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
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pysubs2

# ---------------------- Configuration ----------------------
VIDEO_EXTS = {".mkv", ".mp4", ".m2ts", ".ts", ".webm", ".avi", ".mov"}
TEXT_EXTS = {".ass", ".ssa", ".srt", ".vtt", ".ttml", ".dfxp"}
IMAGE_EXTS = {".idx", ".sub", ".sup"}  # PGS / VobSub families

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


def process_subs(subs: pysubs2.SSAFile, *, max_gap_ms: int = MAX_GAP_MS, small_dur_ms: int = SMALL_DUR_MS, small_char_len: int = SMALL_CHAR_LEN) -> List:
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
def convert_ass_to_srt(input_path: Path, output_path: Path, *, dry_run: bool = False) -> bool:
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

    if dry_run:
        info(f"[DRY-RUN] {input_path} -> {output_path} ({len(processed)} lines)")
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    outsubs.save(str(output_path), format_="srt")
    info(f"Converted: {input_path} -> {output_path} ({len(processed)} lines)")
    return True


# ---------------------- MKV & FFmpeg extraction + auto OCR ----------------------
def extract_subs_from_mkv(mkv_path: Path, out_dir: Path, *, overwrite: bool = False) -> List[Path]:
    """Extract subtitle tracks from MKV using mkvmerge/mkvextract.
    Returns list of extracted files (both text and image-based).
    """
    extracted: List[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        # Run mkvmerge with check=False to handle cases where it exits non-zero but still provides output
        cp = run_command([MKVMERGE, "-J", str(mkv_path)], capture_output=True, check=False)
        if cp.returncode != 0 and not cp.stdout:
            warn(f"mkvmerge failed to identify tracks for {mkv_path.name}. Exit code: {cp.returncode}")
            if cp.stderr:
                warn(f"mkvmerge stderr: {cp.stderr.strip()}")
            return extracted
        info(f"Parsing track list for {mkv_path.name}")
        data = json.loads(cp.stdout)
    except Exception as e:
        warn(f"Failed to run or parse mkvmerge output for {mkv_path}: {e}")
        return extracted

    for track in data.get("tracks", []):
        if track.get("type") != "subtitles":
            continue
        tid = track.get("id")
        codec = (track.get("codec") or "").lower()
        base = out_dir / f"{mkv_path.stem}_track{tid}"
        # prefer extracting as text when codec suggests S_TEXT/ASS
        if "s_text" in codec or "ass" in codec or "srt" in codec:
            ext = ".ass" if "ass" in codec else ".srt"
            dest = base.with_suffix(ext)
            if dest.exists() and not overwrite:
                info(f"Skip extract (exists): {dest.name}")
            else:
                info(f"Extracting text track {tid} -> {dest.name}")
                try:
                    run_command([MKVEXTRACT, "tracks", str(mkv_path), f"{tid}:{str(dest)}"])
                except Exception:
                    warn(f"Failed to extract track {tid} from {mkv_path}")
                    continue
            extracted.append(dest)
        elif "s_hdmv/pgs" in codec:
            # probably image-based (PGS)
            dest = base.with_suffix(".sup")
            if dest.exists() and not overwrite:
                info(f"Skip extract (exists): {dest.name}")
            else:
                info(f"Extracting image-based track {tid} -> {dest.name}")
                try:
                    run_command([MKVEXTRACT, "tracks", str(mkv_path), f"{tid}:{str(dest)}"])
                except Exception:
                    warn(f"Failed to extract image track {tid} from {mkv_path}")
                    continue
            extracted.append(dest)
            # attempt automatic sup->srt conversion
            srt = try_convert_image_sub_to_srt(dest, overwrite=overwrite)
            if srt:
                extracted.append(srt)
        elif "s_vobsub" in codec:
            # VobSub needs both .idx and .sub files
            idx_dest = base.with_suffix(".idx")
            if idx_dest.exists() and not overwrite:
                info(f"Skip extract (exists): {idx_dest.name}")
            else:
                info(f"Extracting VobSub track {tid} -> {idx_dest.name}")
                try:
                    # mkvextract creates both .idx and .sub
                    run_command([MKVEXTRACT, "tracks", str(mkv_path), f"{tid}:{str(idx_dest)}"])
                except Exception:
                    warn(f"Failed to extract VobSub track {tid} from {mkv_path}")
                    continue
            extracted.append(idx_dest)
            srt = try_convert_image_sub_to_srt(idx_dest, overwrite=overwrite)
            if srt:
                extracted.append(srt)
    return extracted


def extract_subs_with_ffmpeg(video_path: Path, out_dir: Path, *, overwrite: bool = False) -> List[Path]:
    """Use ffmpeg to try extracting subtitle streams for non-MKV containers.
    This tries to map 0:s:0..n and convert subtitle codec to srt when possible.
    """
    extracted: List[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    # try mapping subtitle streams 0:s:0..7 (best-effort)
    for idx in range(0, 8):
        dest = out_dir / f"{video_path.stem}_ffsub{idx}.srt"
        if dest.exists() and not overwrite:
            info(f"Skip ffmpeg extract (exists): {dest.name}")
            extracted.append(dest)
            continue
        # Use -y only if overwriting, otherwise ffmpeg will prompt and hang
        overwrite_args = ["-y"] if overwrite else []
        cmd = [FFMPEG, *overwrite_args, "-hide_banner", "-loglevel", "error", "-i", str(video_path), "-map", f"0:s:{idx}", "-c:s", "srt", str(dest)]
        try:
            run_command(cmd)
            info(f"ffmpeg extracted subtitle stream {idx} -> {dest.name}")
            extracted.append(dest)
        except Exception:
            # assume no more subtitle streams at this index
            break
    return extracted


def try_convert_image_sub_to_srt(image_sub_path: Path, *, overwrite: bool = False) -> Optional[Path]:
    """Attempt to convert an image-based sub file (.sup, .idx) to .srt using Subtitle Edit."""
    srt_path = image_sub_path.with_suffix(".srt")
    if srt_path.exists() and not overwrite:
        info(f"Skipping OCR (exists): {srt_path.name}")
        return srt_path

    # Use Subtitle Edit for all image-based formats (.sup, .idx)
    try:
        info(f"Attempting OCR with Subtitle Edit on {image_sub_path.name}")
        # Command: subtitleedit /convert <input> srt
        # The output file is automatically named based on the input.
        run_command([SUBTITLEEDIT, "/convert", str(image_sub_path), "srt"])
        if srt_path.exists():
            info(f"Converted: {image_sub_path.name} -> {srt_path.name} (Subtitle Edit)")
            return srt_path
        else:
            warn(f"Subtitle Edit ran but did not produce the expected output: {srt_path.name}")
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


def scan_videos_and_extract(path: Path, *, overwrite: bool = False) -> List[Path]:
    """Scan folder for video files, extract subs and return text-subtitle files to convert."""
    found_text_subs: List[Path] = []
    for ext in VIDEO_EXTS:
        for video in path.rglob(f"*{ext}"):
            if not video.is_file():
                continue
            info(f"Video found: {video}")
            outdir = video.parent / f"{video.stem}_extracted_subs"
            # prefer mkv extraction when possible
            extracted = []
            if video.suffix.lower() == ".mkv":
                extracted = extract_subs_from_mkv(video, outdir, overwrite=overwrite)
            else:
                extracted = extract_subs_with_ffmpeg(video, outdir, overwrite=overwrite)
            for f in extracted:
                if f.suffix.lower() in TEXT_EXTS:
                    found_text_subs.append(f)
    return found_text_subs


def batch_convert(path: Path, *, overwrite: bool = False, dry_run: bool = False):
    """Top-level behavior: find all text subs and convert them to cleaned .srt."""
    if not path.exists():
        warn(f"Path does not exist: {path}")
        return

    # --- Step 1: Find all subtitle files to process ---
    # Start with text-based subs already on disk
    subs_to_process = find_sub_files(path, list(TEXT_EXTS))

    # If folder contains video files, extract from them too
    has_videos = any(path.rglob(f"*{ext}") for ext in VIDEO_EXTS)
    if has_videos:
        info("Video files detected: extracting subtitle tracks (auto OCR when possible).")
        # scan_videos_and_extract returns a list of text subs it created
        extracted_text_subs = scan_videos_and_extract(path, overwrite=overwrite)
        subs_to_process.extend(extracted_text_subs)

    # --- Step 2: Run conversion on the collected list ---
    # Deduplicate and sort the final list
    final_subs_list = sorted(list(set(subs_to_process)))

    if not final_subs_list:
        info("No text subtitle files found or extracted to convert.")
        return

    info(f"Found {len(final_subs_list)} text subtitle(s) to process.")
    success = skipped = failed = 0
    for sub_file in final_subs_list:
        out_file = sub_file.with_suffix(".srt")
        if out_file.exists() and not overwrite and not dry_run:
            info(f"Skipping (exists): {out_file.name}")
            skipped += 1
            continue

        # This check is a safeguard, but scan_videos_and_extract should only return text subs
        if sub_file.suffix.lower() in IMAGE_EXTS:
            warn(f"Skipping image-based subtitle in final conversion step: {sub_file.name}")
            failed += 1
            continue

        ok = convert_ass_to_srt(sub_file, out_file, dry_run=dry_run)
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
    target, overwrite, dry_run = parse_args()
    if not target.exists():
        warn(f"Target path does not exist: {target}")
        sys.exit(2)

    # Ensure we can write to the target (we create extracted folders & outputs)
    if not dry_run and not is_writable(target.parent if target.is_file() else target):
        warn(f"Target folder is not writable from this process: {target}")
        sys.exit(3)

    if dry_run:
        info("--- Starting DRY RUN ---")

    info(f"Starting batch subtitle conversion in: {target}")
    batch_convert(target, overwrite=overwrite, dry_run=dry_run)
    info("All done.")


if __name__ == "__main__":
    main()

# python /app/convert-subtitles.py --dry-run "/mnt/hdd-01/path/to/your/videos"
