#!/usr/bin/env python3
"""Slot 009: fetch the popup clip from the user-supplied Pinterest share link.

Resolves the pin.it shortlink, downloads the pin video (yt-dlp first,
gallery-dl fallback), probes it, builds a 12-up contact sheet, and stages
everything under assets/quran/009_aal-e-imran_v2_staging/pinterest_pin/.

Failure-transparent: every stage's output is captured to logs/ and a
report.json with status success/failed is ALWAYS written (exit 0), so the
workflow can commit the evidence and a later step fails the run on failure.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

PIN_URL = "https://pin.it/7FdofUUxi"
MAX_BYTES = 95_000_000  # GitHub single-file ceiling guard

ROOT = Path(".")
OUT_DIR = ROOT / "assets" / "quran" / "009_aal-e-imran_v2_staging" / "pinterest_pin"
LOGS = OUT_DIR / "logs"
CLIP = OUT_DIR / "clip.mp4"
META_JSON = OUT_DIR / "pin_meta.json"
REPORT_JSON = OUT_DIR / "report.json"
SHEET = OUT_DIR / "sheet.png"

report: dict = {"pin_url": PIN_URL, "status": "failed", "stages": {}}


def log(msg: str) -> None:
    print(f"[slot-009-clip] {msg}", flush=True)


def capture(name: str, cmd: list[str]) -> tuple[int, str, str]:
    log("$ " + " ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        rc, out, err = 124, str(e.stdout or ""), f"TIMEOUT 600s: {e}"
    except FileNotFoundError as e:
        rc, out, err = (127, "", f"NOT FOUND: {e}")
    (LOGS / f"{name}.out.txt").write_text(out[-20000:], encoding="utf-8")
    (LOGS / f"{name}.err.txt").write_text(err[-20000:], encoding="utf-8")
    report["stages"][name] = {"rc": rc, "out_tail": out[-500:], "err_tail": err[-1500:]}
    log(f"{name}: rc={rc}")
    return rc, out, err


def have_clip() -> Path | None:
    cands = sorted(OUT_DIR.glob("clip.*")) + sorted(OUT_DIR.glob("clip.*")) + sorted(OUT_DIR.rglob("*.mp4"))
    for c in cands:
        if c.is_file() and c.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv") and c.stat().st_size > 5000:
            return c
    return None


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    # A. Resolve the shortlink.
    resolved = PIN_URL
    try:
        req = urllib.request.Request(PIN_URL, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            resolved = resp.geturl()
        log(f"resolved {PIN_URL} -> {resolved}")
    except Exception as e:
        log(f"WARN resolve failed ({e}); downloaders follow redirects themselves")
        report["stages"]["resolve"] = {"rc": 1, "err_tail": str(e)[-500:]}
    report["resolved_url"] = resolved
    report["pin_id"] = resolved.rstrip("/").rsplit("/", 1)[-1]

    # B. yt-dlp metadata + download.
    rc, out, _ = capture("ytdlp_meta",
        [sys.executable, "-m", "yt_dlp", "--no-playlist", "--skip-download",
         "--dump-single-json", PIN_URL])
    if rc == 0:
        META_JSON.write_text(out, encoding="utf-8")
        try:
            meta = json.loads(out)
            report.update({"title": meta.get("title"), "meta_duration": meta.get("duration"),
                           "uploader": meta.get("uploader"), "is_video": meta.get("duration") is not None})
        except json.JSONDecodeError:
            pass
        capture("ytdlp_dl",
            [sys.executable, "-m", "yt_dlp", "--no-playlist",
             "-f", "best[ext=mp4]/best", "-o", str(OUT_DIR / "clip.%(ext)s"), PIN_URL])

    # C. gallery-dl fallback (own Pinterest extractor, often works where yt-dlp is walled).
    if have_clip() is None:
        capture("gallerydl_dl",
            ["gallery-dl", "--destination", str(OUT_DIR), "--filename", "clip.{extension}",
             "--verbose", PIN_URL])

    got = have_clip()
    if got is None:
        REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        log("FAILED: no clip downloaded by either backend; report written")
        return
    if got != CLIP:
        got.rename(CLIP)
    size = CLIP.stat().st_size
    log(f"downloaded {CLIP} ({size} bytes)")
    if size > MAX_BYTES:
        report["stages"]["size_guard"] = {"rc": 1, "err_tail": f"{size} > {MAX_BYTES}"}
        CLIP.unlink()
        REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        log("FAILED: clip exceeds commit guard; report written")
        return

    # D. Probe.
    rc, out, _ = capture("probe",
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration,size,bit_rate:stream=codec_name,codec_type,width,height,r_frame_rate,avg_frame_rate,duration",
         "-of", "json", str(CLIP)])
    probe = json.loads(out)
    dur = float(probe["format"]["duration"])
    report["probe"] = probe

    # E. Contact sheet: 12 stills evenly spaced, tiled 4x3.
    for i in range(12):
        t = dur * (i + 0.5) / 12.0
        rc, _, _ = capture(f"still_{i:02d}",
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-ss", f"{t:.3f}", "-i", str(CLIP), "-frames:v", "1",
             str(OUT_DIR / f"still_{i:02d}.png")])
        if rc != 0:
            break
    capture("sheet",
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(OUT_DIR / "still_%02d.png"),
         "-filter_complex", "scale=270:480,tile=4x3", str(SHEET)])

    report["status"] = "success"
    report["file"] = str(CLIP)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log("SUCCESS: clip staged + sheet built")


if __name__ == "__main__":
    main()
