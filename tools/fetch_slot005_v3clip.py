#!/usr/bin/env python3
"""Slot 005 v3: fetch the popup clip from the user-supplied Pinterest share link.

Resolves the pin.it shortlink, downloads the pin video via yt-dlp, probes it,
builds a 12-up contact sheet for window scouting, and stages everything under
assets/quran/005_maryam_19-30-31_shuraim/pinterest_v3/ for the v3 render.

Runs in GitHub Actions (full internet egress). Fails loudly on any error.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

PIN_URL = "https://pin.it/4dAF6a3gS"
MAX_BYTES = 95_000_000  # GitHub single-file ceiling guard

ROOT = Path(".")
OUT_DIR = ROOT / "assets" / "quran" / "005_maryam_19-30-31_shuraim" / "pinterest_v3"
CLIP = OUT_DIR / "v3_clip.mp4"
META_JSON = OUT_DIR / "pin_meta.json"
REPORT_JSON = OUT_DIR / "report.json"
SHEET = OUT_DIR / "sheet.png"


def log(msg: str) -> None:
    print(f"[slot-005-v3clip] {msg}", flush=True)


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    log("$ " + " ".join(cmd))
    return subprocess.run(cmd, check=True, text=True, **kw)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Resolve the shortlink (yt-dlp would follow it anyway; this records the pin id).
    resolved = PIN_URL
    try:
        req = urllib.request.Request(PIN_URL, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            resolved = resp.geturl()
        log(f"resolved {PIN_URL} -> {resolved}")
    except Exception as e:
        log(f"WARN resolve failed ({e}); passing shortlink to yt-dlp directly")
    pin_id = resolved.rstrip("/").rsplit("/", 1)[-1]

    # 2. Pin metadata (title / duration / uploader) without downloading.
    meta_proc = run(
        [sys.executable, "-m", "yt_dlp", "--no-playlist", "--skip-download",
         "--dump-single-json", PIN_URL],
        capture_output=True,
    )
    META_JSON.write_text(meta_proc.stdout, encoding="utf-8")
    meta = json.loads(meta_proc.stdout)
    log(f"pin {pin_id}: title={meta.get('title')!r} duration={meta.get('duration')} uploader={meta.get('uploader')!r}")

    # 3. Download best mp4.
    run([sys.executable, "-m", "yt_dlp", "--no-playlist",
         "-f", "best[ext=mp4]/best", "-o", str(OUT_DIR / "clip.%(ext)s"), PIN_URL])
    dl = sorted(OUT_DIR.glob("clip.*"))
    assert len(dl) == 1, f"expected one download, got {dl}"
    dl[0].rename(CLIP)
    size = CLIP.stat().st_size
    log(f"downloaded {CLIP} ({size} bytes)")
    if size > MAX_BYTES:
        raise RuntimeError(f"clip {size} bytes exceeds the {MAX_BYTES} byte commit guard")

    # 4. Probe.
    probe = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration,size,bit_rate:stream=codec_name,codec_type,width,height,r_frame_rate,avg_frame_rate,duration",
         "-of", "json", str(CLIP)], text=True))
    dur = float(probe["format"]["duration"])
    log(f"probe: {json.dumps(probe)}")

    # 5. Contact sheet: 12 stills evenly spaced, tiled 4x3 at 270x480 each.
    for i in range(12):
        t = dur * (i + 0.5) / 12.0
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-ss", f"{t:.3f}", "-i", str(CLIP), "-frames:v", "1",
             str(OUT_DIR / f"still_{i:02d}.png")])
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(OUT_DIR / "still_%02d.png"),
         "-filter_complex", "scale=270:480,tile=4x3", str(SHEET)])

    REPORT_JSON.write_text(json.dumps({
        "pin_url": PIN_URL,
        "resolved_url": resolved,
        "pin_id": pin_id,
        "title": meta.get("title"),
        "meta_duration": meta.get("duration"),
        "uploader": meta.get("uploader"),
        "file": str(CLIP),
        "probe": probe,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log("v3 clip staged + sheet built")


if __name__ == "__main__":
    main()
