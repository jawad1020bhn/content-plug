#!/usr/bin/env python3
"""Importer for Slot 002: Surah Al-Baqarah 2:155-157 · Sheikh Ali Jaber + Pinterest Candidate 011."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

UA = "content-plug-quran-slot002/1.0 (+https://github.com/jawad1020bhn/content-plug)"

AUDIO_URLS = [
    "https://cdn.mp3quran.net/audio/ali-jaber/r1/002.mp3",
    "https://server11.mp3quran.net/a_jbr/002.mp3",
]
EVERYAYAH_URLS = [
    "https://everyayah.com/data/Ali_Jaber_64kbps/002155.mp3",
    "https://everyayah.com/data/Ali_Jaber_64kbps/002156.mp3",
    "https://everyayah.com/data/Ali_Jaber_64kbps/002157.mp3",
]
TIMING_SOURCE_URL = "https://www.mp3quran.net/api/v3/ayat_timing?surah=2&read=76"

# Official mp3quran read=76 timestamps for 2:155-157:
#   2:155: 2822600 -> 2837860 ms
#   2:156: 2837860 -> 2849780 ms
#   2:157: 2849780 -> 2862800 ms
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


def fetch_and_trim_audio() -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
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
                dur_s = (END_MS - START_MS) / 1000.0
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
                return url
        except Exception as e:
            last_err = e
            log(f"WARN: {url} failed: {e}")

    # Fallback: concatenate EveryAyah 002155..002157
    log("falling back to EveryAyah per-ayah MP3s")
    parts = []
    for idx, url in enumerate(EVERYAYAH_URLS, 155):
        dest = CACHE / f"ali_jaber_{idx}.mp3"
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as out:
            out.write(resp.read())
        parts.append(dest)
    concat_txt = CACHE / "concat.txt"
    concat_txt.write_text("\n".join(f"file '{p.resolve()}'" for p in parts) + "\n", encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-vn", "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
            str(RAW_RECITATION),
        ],
        check=True,
    )
    return "https://everyayah.com/data/Ali_Jaber_64kbps/ (002155-002157)"


def download_pin_011() -> None:
    import yt_dlp

    PINTEREST_DIR.mkdir(parents=True, exist_ok=True)
    if PIN_CLIP.exists() and PIN_CLIP.stat().st_size > 500_000:
        return

    # Attempt 1: direct pin URL
    direct_opts = {
        "quiet": False,
        "no_warnings": False,
        "noprogress": True,
        "ignoreerrors": True,
        "format": "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(PIN_CLIP),
        "http_headers": {"User-Agent": UA},
    }
    log(f"attempt 1: direct pin {PIN_URL}")
    with yt_dlp.YoutubeDL(direct_opts) as ydl:
        ydl.extract_info(PIN_URL, download=True)

    if PIN_CLIP.exists() and PIN_CLIP.stat().st_size > 500_000:
        log(f"saved {PIN_CLIP} via direct pin URL ({PIN_CLIP.stat().st_size} bytes)")
        return

    # Attempt 2: board URL with match_filter matching PIN_ID (for invite-scoped e1_ IDs)
    tmp_dir = CACHE / "pin_board_tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    def only_pin_011(info: dict, *args, **kwargs) -> str | None:
        if info.get("vcodec") == "none":
            return "not a video pin"
        if str(info.get("id")) != PIN_ID:
            return "not target pin 011"
        return None

    board_opts = {
        "quiet": False,
        "no_warnings": False,
        "noprogress": True,
        "ignoreerrors": True,
        "extract_flat": False,
        "lazy_playlist": False,
        "noplaylist": False,
        "playlistend": 20,
        "match_filter": only_pin_011,
        "format": "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(tmp_dir / "%(id)s.%(ext)s"),
        "http_headers": {"User-Agent": UA},
    }
    log(f"attempt 2: extracting {PIN_ID} from board {BOARD_URL}")
    with yt_dlp.YoutubeDL(board_opts) as ydl:
        ydl.extract_info(BOARD_URL, download=True)

    matches = sorted(tmp_dir.glob("*.mp4"))
    if not matches:
        raise RuntimeError(f"failed to download {PIN_ID} from both pin URL and board URL")
    shutil.move(str(matches[0]), str(PIN_CLIP))
    log(f"saved {PIN_CLIP} via board URL ({PIN_CLIP.stat().st_size} bytes)")


def main() -> None:
    used_audio_url = fetch_and_trim_audio()
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
