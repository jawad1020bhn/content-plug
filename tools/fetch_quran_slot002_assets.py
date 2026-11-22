#!/usr/bin/env python3
"""Importer for Slot 002: Surah Al-Baqarah 2:155-157 · Sheikh Ali Jaber + Pinterest Candidate 011."""

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

UA = "content-plug-quran-slot002/1.0 (+https://github.com/jawad1020bhn/content-plug)"

AUDIO_URLS = [
    "https://cdn.mp3quran.net/audio/ali-jaber/r1/002.mp3",
    "https://server11.mp3quran.net/a_jbr/002.mp3",
]
TIMING_SOURCE_URL = "https://www.mp3quran.net/api/v3/ayat_timing?surah=2&read=76"

# Official mp3quran read=76 timestamps for 2:155-157:
#   2:155: 2822600 -> 2837860 ms
#   2:156: 2837860 -> 2849780 ms
#   2:157: 2849780 -> 2862800 ms
# Trim exact 2822600 -> 2862800 ms (40.200s) raw without extra leading silence yet
# so local acoustic waveform analysis can trim silence & place the scroll-settle intro to the ms.
START_MS = 2822400
END_MS = 2862900

PIN_ID = "e1_AfqPShzEtwAnD7ThMX5sHbgIPsLcRUnHp5Gze2TSoZqKuuDXknyc-g"
PIN_URL = f"https://www.pinterest.com/pin/{PIN_ID}/"
BOARD_URL = "https://www.pinterest.com/jawed1025t/k/?invite_code=516f29ecb56e4a40a891ccc8089d146a&sender=1119215082304641687"

ROOT = Path(".")
SLOT = "002_al-baqarah_2-155-157_ali-jaber"
ASSETS = ROOT / "assets" / "quran" / SLOT
PINTEREST_DIR = ASSETS / "pinterest"
CACHE = ROOT / ".cache"
FULL_AUDIO = CACHE / "ali_jaber_002.mp3"
RAW_RECITATION = ASSETS / "recitation_raw.m4a"
PIN_CLIP = PINTEREST_DIR / f"011_{PIN_ID}.mp4"
SOURCE_MD = ASSETS / "SOURCE.md"


def log(msg: str) -> None:
    print(f"[slot-002] {msg}", flush=True)


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
            "format=duration,size,bit_rate:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
            "-of", "json", str(path),
        ],
        text=True,
    )
    return json.loads(out)


def download_audio() -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    last_err = None
    for url in AUDIO_URLS:
        try:
            log(f"downloading {url} -> {FULL_AUDIO}")
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=300) as resp, FULL_AUDIO.open("wb") as out:
                while True:
                    buf = resp.read(1024 * 1024)
                    if not buf:
                        break
                    out.write(buf)
            if FULL_AUDIO.stat().st_size > 5_000_000:
                log(f"saved {FULL_AUDIO} ({FULL_AUDIO.stat().st_size} bytes)")
                return url
        except Exception as e:
            last_err = e
            log(f"WARN: {url} failed: {e}")
    raise RuntimeError(f"all audio URLs failed: {last_err}")


def trim_recitation() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    dur_s = (END_MS - START_MS) / 1000.0
    # Put -ss and -t AFTER -i for sample-accurate MP3 seek!
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(FULL_AUDIO),
            "-ss", f"{START_MS / 1000.0:.3f}",
            "-t", f"{dur_s:.3f}",
            "-vn", "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
            str(RAW_RECITATION),
        ],
        check=True,
    )
    log(f"trimmed {RAW_RECITATION} ({RAW_RECITATION.stat().st_size} bytes)")


def download_pin_011() -> None:
    import yt_dlp

    PINTEREST_DIR.mkdir(parents=True, exist_ok=True)
    opts = {
        "quiet": False,
        "no_warnings": False,
        "noprogress": True,
        "format": "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(PIN_CLIP),
        "http_headers": {"User-Agent": UA},
    }
    log(f"downloading Pinterest candidate 011: {PIN_URL}")
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(PIN_URL, download=True)

    if not PIN_CLIP.exists() or PIN_CLIP.stat().st_size < 500_000:
        raise RuntimeError(f"Pinterest clip 011 missing or too small: {PIN_CLIP}")
    log(f"saved {PIN_CLIP} ({PIN_CLIP.stat().st_size} bytes, sha256={sha256(PIN_CLIP)[:12]})")


def main() -> None:
    used_audio_url = download_audio()
    trim_recitation()
    download_pin_011()

    rec_probe = ffprobe_json(RAW_RECITATION)
    pin_probe = ffprobe_json(PIN_CLIP)

    (ASSETS / "selection.txt").write_text(
        "011 — serene alpine emerald lake and mountainside chalets (unused candidate from board K, 32.6 s continuous shot, raw original colors)\n",
        encoding="utf-8",
    )

    SOURCE_MD.write_text(
        "\n".join(
            [
                "# Source assets — slot 002 · Al-Baqarah 2:155–157 · Sheikh Ali Jaber",
                "",
                "Output: `outputs/quran-002_al-baqarah_2-155-157_ali-jaber_en_1080x1920_v1.mp4`",
                "Post package: `metadata/002_al-baqarah_2-155-157_ali-jaber/`",
                "",
                "## Recitation",
                "",
                "- Reciter: Sheikh Ali Abdullah Jaber (1953–2005), Murattal (Hafs 'an 'Asim).",
                f"- Audio source: {used_audio_url}",
                f"- Official ayah timing source: {TIMING_SOURCE_URL}",
                f"- Raw excerpt trim: {START_MS}–{END_MS} ms (Surah Al-Baqarah 2:155–157).",
                f"- Raw trim file: `recitation_raw.m4a` (`{sha256(RAW_RECITATION)}`, {RAW_RECITATION.stat().st_size} bytes).",
                f"- ffprobe: `{json.dumps(rec_probe, ensure_ascii=False)}`",
                "",
                "## Background clip (Pinterest board “K”, candidate 011 — unused)",
                "",
                f"- Pin URL: {PIN_URL}",
                f"- Board: {BOARD_URL} (Jaqqd / jawed1025t)",
                f"- File: `pinterest/{PIN_CLIP.name}` (`{sha256(PIN_CLIP)}`, {PIN_CLIP.stat().st_size} bytes).",
                f"- ffprobe: `{json.dumps(pin_probe, ensure_ascii=False)}`",
                "- Color treatment: raw original colors preserved (no color grade applied per user direction).",
                "- Rights: user-supplied board; user stated no licence issue. Clear rights before commercial release.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    log("all slot 002 source assets fetched and verified")


if __name__ == "__main__":
    main()
