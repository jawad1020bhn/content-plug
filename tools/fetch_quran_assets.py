#!/usr/bin/env python3
"""One-shot importer for the first Quran verse-card video.

Sandbox egress is restricted, so GitHub Actions downloads the two public assets:
  * Pixabay background video 204756 (1080x1920, 30 fps), and
  * Quran Foundation Surah Maryam chapter audio for Mishari al-`Afasy.

It saves the background MP4 plus a *trimmed* 19:30-33 recitation excerpt (with
a short silent intro) under assets/. The full surah MP3 stays in ignored .cache/.
No raw QF API JSON is committed.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

UA = "content-plug-quran-assets/1.0 (+https://github.com/jawad1020bhn/content-plug)"
PIXABAY_PAGE = "https://pixabay.com/videos/sunset-sunrise-night-sky-moonlight-204756/"
PIXABAY_MP4 = "https://cdn.pixabay.com/video/2024/03/19/204756-925166550_large.mp4"
QF_AUDIO = "https://download.quranicaudio.com/qdc/mishari_al_afasy/murattal/19.mp3"
QF_TIMING_URL = "https://api.quran.com/api/v4/chapter_recitations/7/19?segments=true"
QF_START_MS = 397790
QF_END_MS = 440010
INTRO_S = 0.8
CLIP_S = (QF_END_MS - QF_START_MS) / 1000.0  # 42.220

ASSETS = Path("assets/quran-19-30-33")
CACHE = Path(".cache")
FULL_AUDIO = CACHE / "quran_surah19_full.mp3"
BACKGROUND = ASSETS / "background.mp4"
RECITATION = ASSETS / "recitation_19_30_33.m4a"
SOURCE_MD = ASSETS / "SOURCE.md"


def log(msg: str) -> None:
    print("[fetch-quran-assets] " + msg, flush=True)


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 10000:
        log("already have %s (%d bytes)" % (dest, dest.stat().st_size))
        return
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    log("downloading %s -> %s" % (url, dest))
    with urllib.request.urlopen(req, timeout=180) as resp, dest.open("wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    if dest.stat().st_size < 10000:
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
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=index,codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        text=True,
    )
    return json.loads(out)


def trim_audio() -> None:
    # 0.8 s silence, then the exact QF 19:30-33 recitation window, with soft fades.
    fade_out_start = INTRO_S + CLIP_S - 0.5
    af = "adelay=800:all=1,afade=t=in:st=0.80:d=0.20,afade=t=out:st=%.3f:d=0.50" % fade_out_start
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        "%.3f" % (QF_START_MS / 1000.0),
        "-t",
        "%.3f" % CLIP_S,
        "-i",
        str(FULL_AUDIO),
        "-vn",
        "-af",
        af,
        "-ar",
        "44100",
        "-ac",
        "2",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(RECITATION),
    ]
    log("trimming %s -> %s" % (FULL_AUDIO, RECITATION))
    subprocess.run(cmd, check=True)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    download(PIXABAY_MP4, BACKGROUND)
    download(QF_AUDIO, FULL_AUDIO)
    trim_audio()

    bg_info = ffprobe_json(BACKGROUND)
    au_info = ffprobe_json(RECITATION)
    if not any(s.get("codec_type") == "video" for s in bg_info.get("streams", [])):
        raise RuntimeError("background has no video stream")
    if not any(s.get("codec_type") == "audio" for s in au_info.get("streams", [])):
        raise RuntimeError("recitation has no audio stream")

    SOURCE_MD.write_text(
        "\n".join(
            [
                "# Source assets — Surah Maryam 19:30–33 verse card",
                "",
                "These are source assets for a local video. Credits belong in the post caption/description,",
                "never burned into the video pixels.",
                "",
                "## Background",
                "",
                "- Pixabay video 204756, “Sunset, Sunrise, Night” by hsahmad472.",
                "- Page: %s" % PIXABAY_PAGE,
                "- Direct MP4: %s" % PIXABAY_MP4,
                "- License: [Pixabay Content License](https://pixabay.com/service/license-summary/) — free use,",
                "  modification and adaptation; no standalone redistribution. Attribution appreciated, not required.",
                "- SHA-256 `%s` (%d bytes)." % (sha256(BACKGROUND), BACKGROUND.stat().st_size),
                "- ffprobe: %s" % json.dumps(bg_info, ensure_ascii=False),
                "",
                "## Recitation",
                "",
                "- Reciter: Mishari Rashid al-`Afasy, Murattal (Hafs), chapter-reciter ID 7.",
                "- QF segment/timing source: %s" % QF_TIMING_URL,
                "- Full chapter audio: %s" % QF_AUDIO,
                "- Trim: %d–%d ms (19:30–33), %.3f s; plus %.1f s leading silence and 0.2 s / 0.5 s fades." % (QF_START_MS, QF_END_MS, CLIP_S, INTRO_S),
                "- Output: `recitation_19_30_33.m4a` (AAC 44.1 kHz stereo, %.3f s total)." % (INTRO_S + CLIP_S),
                "- SHA-256 `%s` (%d bytes)." % (sha256(RECITATION), RECITATION.stat().st_size),
                "- ffprobe: %s" % json.dumps(au_info, ensure_ascii=False),
                "",
                "## Rights / attribution",
                "",
                "- Quran Foundation text/timing/audio: credit “Quran data provided by Quran Foundation.”",
                "  plus the named reciter and translation edition in the post caption/description.",
                "- QF [Connected Apps](https://api-docs.quran.com/docs/connected-apps/) notes that commercial use",
                "  or redistribution of licensed recitations may require a separate written content license.",
                "  Clear rights before any public/commercial post. No upload is done by this importer.",
                "- Full-surah MP3 is kept only in ignored `.cache/`; raw QF API JSON is not committed.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    log("wrote %s" % SOURCE_MD)
    log("done")


if __name__ == "__main__":
    main()
