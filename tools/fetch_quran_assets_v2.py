#!/usr/bin/env python3
"""One-shot importer for the second Quran verse-card video.

GitHub Actions has the egress needed to fetch:
  * user-supplied Pinterest board "K" video clips, and
  * Quran Foundation Surah Al-Baqarah audio for Yasser ad-Dussary.

It saves candidate clips + a contact sheet under assets/, writes a trimmed
2:152-153 recitation with a silent intro, and keeps the full-surah MP3 only in
ignored .cache/. No raw QF API JSON is committed.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

UA = "content-plug-quran-assets-v2/1.0 (+https://github.com/jawad1020bhn/content-plug)"
PIN_SHORT_URL = "https://pin.it/4pKEOoyfx"
BOARD_URL = "https://www.pinterest.com/jawed1025t/k/?invite_code=516f29ecb56e4a40a891ccc8089d146a&sender=1119215082304641687"
QF_AUDIO = "https://download.quranicaudio.com/quran/yasser_ad-dussary//002.mp3"
QF_TIMING_URL = "https://api.quran.com/api/v4/chapter_recitations/97/2?segments=true"
QF_START_MS = 3274050
QF_END_MS = 3299050
INTRO_S = 0.8
CLIP_S = (QF_END_MS - QF_START_MS) / 1000.0  # 25.000

ROOT = Path(".")
ASSETS = ROOT / "assets" / "al-baqarah-2-152-153"
CANDIDATES = ASSETS / "pinterest_candidates"
CACHE = ROOT / ".cache"
THUMBS = CACHE / "pinterest_thumbs"
FULL_AUDIO = CACHE / "quran_surah2_full.mp3"
RECITATION = ASSETS / "recitation_2_152_153.m4a"
CANDIDATES_JSON = ASSETS / "candidates.json"
CANDIDATES_SHEET = ASSETS / "candidates_sheet.png"
SOURCE_MD = ASSETS / "SOURCE.md"


def log(msg: str) -> None:
    print("[fetch-quran-v2] " + msg, flush=True)


def download(url: str, dest: Path, min_bytes: int = 10000) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_bytes:
        log("already have %s (%d bytes)" % (dest, dest.stat().st_size))
        return
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    log("downloading %s -> %s" % (url, dest))
    with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    if dest.stat().st_size < min_bytes:
        raise RuntimeError("downloaded file is too small: %s" % dest)
    log("saved %s (%d bytes)" % (dest, dest.stat().st_size))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ffprobe_json(path: Path) -> dict:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
            "-of", "json", str(path),
        ],
        text=True,
    )
    return json.loads(out)


def trim_audio() -> None:
    fade_out_start = INTRO_S + CLIP_S - 0.5
    af = "adelay=800:all=1,afade=t=in:st=0.80:d=0.20,afade=t=out:st=%.3f:d=0.50" % fade_out_start
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", "%.3f" % (QF_START_MS / 1000.0),
        "-t", "%.3f" % CLIP_S,
        "-i", str(FULL_AUDIO),
        "-vn", "-af", af,
        "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
        str(RECITATION),
    ]
    log("trimming %s -> %s" % (FULL_AUDIO, RECITATION))
    subprocess.run(cmd, check=True)


def video_filter(info: dict, *args, **kwargs) -> str | None:
    if info.get("vcodec") == "none":
        return "not a video pin"
    duration = info.get("duration") or 0
    if duration and duration < 3:
        return "shorter than 3 seconds"
    return None


def fetch_pinterest_clips() -> dict:
    import yt_dlp

    if CANDIDATES.exists():
        shutil.rmtree(CANDIDATES)
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    if THUMBS.exists():
        shutil.rmtree(THUMBS)
    THUMBS.mkdir(parents=True, exist_ok=True)

    opts = {
        "quiet": False,
        "no_warnings": False,
        "noprogress": True,
        "ignoreerrors": True,
        "extract_flat": False,
        "lazy_playlist": False,
        "noplaylist": False,
        "playlistend": 29,
        "max_downloads": 12,
        "match_filter": video_filter,
        "format": "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(CANDIDATES / "%(playlist_index)03d_%(id)s.%(ext)s"),
        "writethumbnail": False,
        "writeinfojson": False,
        "http_headers": {"User-Agent": UA},
    }
    log("extracting Pinterest board %s" % BOARD_URL)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(BOARD_URL, download=True)
    if not info:
        raise RuntimeError("yt-dlp returned no board metadata")

    entries = [e for e in (info.get("entries") or []) if isinstance(e, dict)]
    by_id = {str(e.get("id")): e for e in entries if e.get("id")}
    files = sorted(p for p in CANDIDATES.iterdir() if p.is_file() and p.suffix.lower() == ".mp4")
    if not files:
        raise RuntimeError("no video clips were downloaded from the Pinterest board")

    candidates = []
    for i, path in enumerate(files, start=1):
        m = re.fullmatch(r"(\d{3})_(\d+)\.mp4", path.name)
        pin_id = m.group(2) if m else ""
        entry = by_id.get(pin_id, {})
        probe = ffprobe_json(path)
        candidates.append(
            {
                "index": i,
                "filename": path.name,
                "pin_id": pin_id,
                "webpage_url": entry.get("webpage_url") or ("https://www.pinterest.com/pin/%s/" % pin_id if pin_id else ""),
                "title": entry.get("title") or "",
                "duration": entry.get("duration"),
                "width": entry.get("width"),
                "height": entry.get("height"),
                "thumbnail": entry.get("thumbnail"),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "ffprobe": probe,
            }
        )
        thumb = THUMBS / ("thumb_%03d.png" % i)
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", "0.5", "-i", str(path),
                "-vf", "scale=270:480:force_original_aspect_ratio=increase,crop=270:480",
                "-frames:v", "1", "-update", "1", str(thumb),
            ],
            check=True,
        )

    CANDIDATES_JSON.write_text(
        json.dumps(
            {
                "short_url": PIN_SHORT_URL,
                "board_url": BOARD_URL,
                "board_title": info.get("title") or "K",
                "board_owner": "Jaqqd / jawed1025t",
                "downloaded_count": len(candidates),
                "candidates": candidates,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    make_contact_sheet(len(candidates))
    return {"count": len(candidates), "board_title": info.get("title") or "K"}


def make_contact_sheet(n: int) -> None:
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    tw, th, pad = 270, 480, 8
    cols = min(3, n)
    rows = math.ceil(n / cols)
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + pad) + pad), (12, 12, 14))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i in range(1, n + 1):
        thumb = THUMBS / ("thumb_%03d.png" % i)
        if not thumb.exists():
            continue
        img = Image.open(thumb).convert("RGB")
        img = ImageOps.fit(img, (tw, th), method=Image.Resampling.LANCZOS)
        x = pad + ((i - 1) % cols) * (tw + pad)
        y = pad + ((i - 1) // cols) * (th + pad)
        sheet.paste(img, (x, y))
        label = "%02d" % i
        draw.rectangle((x + 6, y + 6, x + 52, y + 24), fill=(0, 0, 0))
        draw.text((x + 10, y + 9), label, fill=(255, 255, 255), font=font)
    sheet.save(CANDIDATES_SHEET)
    log("wrote %s" % CANDIDATES_SHEET)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    download(QF_AUDIO, FULL_AUDIO, min_bytes=1_000_000)
    trim_audio()
    pinterest = fetch_pinterest_clips()

    rec_probe = ffprobe_json(RECITATION)
    SOURCE_MD.write_text(
        "\n".join(
            [
                "# Source assets — Al-Baqarah 2:152–153 verse card",
                "",
                "Local review assets. Post caption/description credits are generated separately; no credit text is",
                "burned into the video and no social upload is performed by this importer.",
                "",
                "## Recitation",
                "",
                "- Reciter: Yasser ad-Dussary, Murattal (Hafs), QF chapter-reciter ID 97.",
                "- QF segment/timing source: %s" % QF_TIMING_URL,
                "- Full chapter audio: %s" % QF_AUDIO,
                "- Trim: %d–%d ms (2:152–153), %.3f s; plus %.1f s leading silence and 0.2 s / 0.5 s fades." % (QF_START_MS, QF_END_MS, CLIP_S, INTRO_S),
                "- Output: `recitation_2_152_153.m4a` (AAC 44.1 kHz stereo, %.3f s total)." % (INTRO_S + CLIP_S),
                "- SHA-256 `%s` (%d bytes)." % (sha256(RECITATION), RECITATION.stat().st_size),
                "- ffprobe: %s" % json.dumps(rec_probe, ensure_ascii=False),
                "",
                "## Pinterest background candidates",
                "",
                "- Supplied short link: %s" % PIN_SHORT_URL,
                "- Board: %s" % BOARD_URL,
                "- Public signed-out metadata names the board “%s” by Jaqqd (jawed1025t)." % pinterest["board_title"],
                "- Downloaded %d video clips into `pinterest_candidates/`." % pinterest["count"],
                "- Pin IDs, source URLs, durations, hashes and ffprobe data: `candidates.json`.",
                "- Visual contact sheet: `candidates_sheet.png`.",
                "- Rights: the user supplied this board and explicitly stated “no licence issue” for using the clips",
                "  as the popup background. This record does not claim a public stock licence; clear rights before",
                "  any public or commercial release.",
                "",
                "## Credits to carry into the post caption/description",
                "",
                "- “Quran data provided by Quran Foundation.”",
                "- Arabic: QPC Hafs / UthmanicHafs1Ver18 — King Fahd Glorious Quran Printing Complex (KFGQPC).",
                "- Translation: English Translation - Noor International Center (`english_saheeh` v1.1.2 / QuranEnc.com).",
                "- Reciter: Yasser ad-Dussary (Murattal, Hafs).",
                "- Fonts: KFGQPC Uthmanic Hafs + Cormorant Garamond (SIL OFL 1.1).",
                "- Background: Pinterest board “K” by Jaqqd / jawed1025t (user-supplied clips).",
                "",
                "QF Connected Apps notes that commercial use or redistribution of licensed recitations may require a",
                "separate written content license; KFGQPC reproduction/commercial release may require written approval.",
                "Full-surah MP3 is kept only in ignored `.cache/`; raw QF API JSON is not committed.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    log("wrote %s" % SOURCE_MD)
    log("done: %d Pinterest clips + trimmed recitation" % pinterest["count"])


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("ERROR: %s" % e)
        raise
