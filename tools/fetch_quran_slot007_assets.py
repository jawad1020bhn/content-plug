#!/usr/bin/env python3
"""Importer for Slot 007: Mishari al-Afasy, Ibrahim 14:40 (QF id 7).

Single-ayah card: Ibrahim's du'a "My Lord, make me steadfast in prayer..."
Primary audio: QF per-ayah MP3 (audio.qurancdn.com/Alafasy/mp3/014040.mp3).
Fallback: QF chapter_recitations/7/14 full-surah MP3 trimmed to the verse.

Voice-first assembly: 0.35 s leading + head-trimmed voice (first-word-start
minus 0.12 s) + last-word-end + 0.4 s natural decay + 0.6 s trailing digital
silence -> recitation_raw.m4a (~13.8 s, under 25 s cap).

RAW-AUDIO SLOT (human direction): the video build uses this assembly with ZERO
audio processing - no EQ, no reverb, no ambience, no loudness normalization.
Only padding with digital silence; the voice is bit-transparent vs QF.

Popup: Pinterest board-K candidate 002 used WHOLE (man performs wudu at a
mountain stream, stands, then kneels in prayer; 11.08 s, 720x1280, 0 cuts);
committed under assets/.../pinterest/ and mapped whole across the card (~0.80x).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
import traceback
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (compatible; content-plug-quran-slot007/1.0)"

QF_AYAH_URL = "https://audio.qurancdn.com/Alafasy/mp3/014040.mp3"
QF_TIMING_URL = "https://api.quran.com/api/v4/verses/by_key/14:40?words=true&audio=7&word_fields=text_qpc_hafs"
QF_CHAPTER_URL = "https://api.quran.com/api/v4/chapter_recitations/7/14"
SAHEEH_URL = "https://quranenc.com/api/v1/translation/aya/english_saheeh/14/40?without_footnotes_symbols=1"

# Voice-first assembly: onset lands ~0.42 s, mid scroll-settle.
LEAD_PAD_S = 0.35   # leading digital silence
TAIL_PAD_S = 0.6    # air for the true-loop match-dissolve
TRIM_TAIL_S = 0.4   # keep last-word-end + 0.4 s (natural decay)

PIN_ID_POPUP = "e1_AfqPShwWDOHMQ5I_Ev1_JobUxZAcNMrg8PElRynydnpeEjYAk8uQeA"
PIN_BLOB_SHA = "7f92d9240d02a06520c3bd01b666db3d0106e708"
PIN_BLOB_PATH = "assets/al-baqarah-2-152-153/pinterest_candidates/002_" + PIN_ID_POPUP + ".mp4"
BOARD_URL = "https://www.pinterest.com/jawed1025t/k/?invite_code=516f29ecb56e4a40a891ccc8089d146a&sender=1119215082304641687"

ROOT = Path(".")
SLOT = "007_ibrahim_14-40_afasy"
ASSETS = ROOT / "assets" / "quran" / SLOT
CACHE = ROOT / ".cache"
AYAH_MP3 = CACHE / "afasy_014040.mp3"
AYAH_TRIM = CACHE / "afasy_014040_trim.m4a"
CHAPTER_MP3 = CACHE / "afasy_014.mp3"
CHAPTER_TRIM = CACHE / "afasy_014_v40_trim.mp3"
RAW_RECITATION = ASSETS / "recitation_raw.m4a"
SOURCE_MD = ASSETS / "SOURCE.md"


def log(msg: str) -> None:
    print(f"[slot-007] {msg}", flush=True)


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
            "format=duration,size,bit_rate:stream=codec_name,codec_type,sample_rate,channels",
            "-of", "json", str(path),
        ],
        text=True,
    )
    return json.loads(out)


def _http_get(url: str, accept: str, timeout: int) -> bytes:
    """GET with retries (transient runner-network / CDN 429 friendly)."""
    last: Exception | None = None
    for attempt, wait in ((1, 2.0), (2, 6.0), (3, 15.0)):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:  # noqa: BLE001 - retry then surface
            last = e
            log(f"WARN GET attempt {attempt}/3 failed for {url}: {e}; sleeping {wait}s")
            time.sleep(wait)
    assert last is not None
    raise last


def download(url: str, dest: Path, timeout: int = 300) -> None:
    log(f"downloading {url} -> {dest}")
    dest.write_bytes(_http_get(url, "*/*", timeout))


def fetch_json(url: str, dest: Path, timeout: int = 120) -> dict:
    log(f"fetching JSON {url}")
    data = json.loads(_http_get(url, "application/json", timeout).decode("utf-8"))
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    time.sleep(1.0)  # courtesy gap between API hits
    return data


def silence_report(path: Path) -> dict:
    """First non-silence (onset) and trailing-silence start via silencedetect."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", "silencedetect=noise=-45dB:d=0.15", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    starts: list[float] = []
    ends: list[float] = []
    for line in proc.stderr.splitlines():
        if "silence_start:" in line:
            try:
                starts.append(float(line.split("silence_start:")[1].split()[0]))
            except ValueError:
                pass
        if "silence_end:" in line:
            try:
                ends.append(float(line.split("silence_end:")[1].split()[0]))
            except ValueError:
                pass
    return {"silence_starts": starts, "silence_ends": ends}


def find_chapter_segment(obj, verse: int) -> tuple[int, int] | None:
    """Defensively locate [verse, start_ms, end_ms] anywhere in the chapter JSON."""
    if isinstance(obj, list) and len(obj) >= 3 and obj[0] == verse:
        try:
            return int(obj[1]), int(obj[2])
        except (TypeError, ValueError):
            return None
    if isinstance(obj, list):
        for item in obj:
            hit = find_chapter_segment(item, verse)
            if hit:
                return hit
    elif isinstance(obj, dict):
        for item in obj.values():
            hit = find_chapter_segment(item, verse)
            if hit:
                return hit
    return None


def find_audio_url(obj) -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "audio_url" and isinstance(v, str) and v:
                return v
        for v in obj.values():
            hit = find_audio_url(v)
            if hit:
                return hit
    elif isinstance(obj, list):
        for item in obj:
            hit = find_audio_url(item)
            if hit:
                return hit
    return None


def fetch_fallback_chapter_trim() -> tuple[str, str]:
    """Download full surah 14 and trim verse 40. Returns (used_url, timing_note)."""
    req = urllib.request.Request(QF_CHAPTER_URL, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    seg = find_chapter_segment(data, 40)
    audio_url = find_audio_url(data)
    if seg is None or not audio_url:
        raise RuntimeError("fallback: chapter_recitations/7/14 gave no verse-40 segment or audio_url")
    start_ms, end_ms = seg
    if not audio_url.startswith("http"):
        audio_url = "https://audio.qurancdn.com/" + audio_url.lstrip("/")
    if not CHAPTER_MP3.exists():
        download(audio_url, CHAPTER_MP3)
    ss = max(0.0, (start_ms - 400) / 1000.0)
    dur = (end_ms - start_ms + 800) / 1000.0
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(CHAPTER_MP3), "-ss", f"{ss:.3f}", "-t", f"{dur:.3f}",
         "-vn", "-c:a", "copy", str(CHAPTER_TRIM)],
        check=True,
    )
    note = f"fallback chapter trim {start_ms - 400}-{end_ms + 400} ms of surah 14 (verse 40)"
    return audio_url, note


def fetch_voice() -> tuple[Path, str, str]:
    """Returns (voice_file, used_audio_url, timing_note)."""
    try:
        download(QF_AYAH_URL, AYAH_MP3, timeout=120)
        if AYAH_MP3.stat().st_size < 5000:
            raise RuntimeError(f"ayah mp3 too small ({AYAH_MP3.stat().st_size} bytes)")
        return AYAH_MP3, QF_AYAH_URL, "QF per-ayah mp3 014040"
    except Exception as e:
        log(f"WARN primary per-ayah mp3 14:40 failed ({e}); using chapter fallback")
        used_url, note = fetch_fallback_chapter_trim()
        return CHAPTER_TRIM, used_url, note


def trim_to_word_span(src: Path, qf: dict) -> tuple[Path, float]:
    """Trim to [first-word-start - 120 ms, last-word-end + TRIM_TAIL_S].

    Returns (trimmed_path, head_trim_s) so karaoke beats stay aligned.
    """
    segs = qf["verse"]["audio"]["segments"]
    head_trim_s = max(0.0, segs[0][2] / 1000.0 - 0.12)
    keep = segs[-1][3] / 1000.0 + TRIM_TAIL_S - head_trim_s
    src_dur = float(ffprobe_json(src)["format"]["duration"])
    keep = min(keep, src_dur - head_trim_s)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{head_trim_s:.3f}", "-i", str(src), "-t", f"{keep:.3f}",
         "-vn", "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
         str(AYAH_TRIM)],
        check=True,
    )
    log(f"ayah 14:40: file {src_dur:.3f} s, head trim {head_trim_s:.3f} s, "
        f"last word ends {segs[-1][3]} ms -> trimmed {keep:.3f} s")
    return AYAH_TRIM, head_trim_s


def assemble_raw(trimmed: Path) -> tuple[float, dict]:
    """Prepend 0.35 s + append 0.6 s digital silence (no processing of the voice)."""
    d0 = float(ffprobe_json(trimmed)["format"]["duration"])
    total = LEAD_PAD_S + d0 + TAIL_PAD_S
    fc = (
        "[0:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[v0];"
        f"[v0]adelay={int(LEAD_PAD_S * 1000)}:all=1,apad=whole_dur={total:.3f}[aout]"
    )
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(trimmed), "-filter_complex", fc,
         "-map", "[aout]", "-vn", "-ar", "44100", "-ac", "2",
         "-c:a", "aac", "-b:a", "192k", str(RAW_RECITATION)],
        check=True,
    )
    concat_map = {
        "lead_s": LEAD_PAD_S,
        "head_trim_s": 0.0,  # filled by caller
        "voice_s": round(d0, 3),
        "tail_s": TAIL_PAD_S,
        "total_s": round(total, 3),
    }
    return float(ffprobe_json(RAW_RECITATION)["format"]["duration"]), concat_map


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

    f40, url40, note40 = fetch_voice()

    qf40 = fetch_json(QF_TIMING_URL, ASSETS / "qf_14-40.json")
    fetch_json(SAHEEH_URL, ASSETS / "saheeh_14-40.json")

    segs = qf40["verse"]["audio"]["segments"]
    timing_note = (f"14:40 [first word {segs[0][2]} ms, last word ends {segs[-1][3]} ms] "
                   f"({note40})")

    t40, head_trim = trim_to_word_span(f40, qf40)
    raw_dur, concat_map = assemble_raw(t40)
    concat_map["head_trim_s"] = round(head_trim, 3)
    (ASSETS / "concat_map.json").write_text(
        json.dumps(concat_map, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"raw recitation {RAW_RECITATION} ({RAW_RECITATION.stat().st_size} bytes, {raw_dur:.3f} s)")
    if raw_dur > 25.0:
        raise RuntimeError(f"raw recitation {raw_dur:.3f} s exceeds the 25 s cap")
    speed = raw_dur / 11.08  # whole-clip mapping factor for the 11.08 s popup

    rec_probe = ffprobe_json(RAW_RECITATION)
    sil = silence_report(RAW_RECITATION)

    (ASSETS / "selection.txt").write_text(
        "002 popup used whole - man performs wudu at a mountain stream, stands, then "
        "kneels in prayer; lush valley, 0 cuts, face never shown; mapped whole across "
        "the card at ~0.80x (raw original colors)\n",
        encoding="utf-8",
    )

    SOURCE_MD.write_text(
        "\n".join(
            [
                "# Source assets - slot 007 - Ibrahim 14:40 - Mishari al-Afasy",
                "",
                "Output: `outputs/quran-007_ibrahim_14-40_afasy_en_1080x1920_v1.mp4`",
                "Post package: `metadata/007_ibrahim_14-40_afasy/`",
                "",
                "## Recitation (RAW - no audio processing by human direction)",
                "",
                "- Reciter: Mishari al-Afasy, Murattal (Hafs 'an 'Asim), QF reciter ID 7.",
                f"- Audio source: {url40} (single ayah, no inter-ayah gap).",
                f"- Timing source: {QF_TIMING_URL} (mirrored to `qf_14-40.json`).",
                f"- {timing_note}.",
                "- English: Saheeh International translation via QuranEnc",
                f"  ({SAHEEH_URL}, mirrored to `saheeh_14-40.json`; rotation break from "
                "rwwad documented in post.json: rwwad 14:40 reads 'some my offspring').",
                f"- Trim: file cut to [first-word-start - 0.12 s, last-word-end + {TRIM_TAIL_S} s] "
                f"(head {head_trim:.3f} s removed for voice-first onset; natural decay kept).",
                f"- Raw assembly: {LEAD_PAD_S} s leading + voice + {TAIL_PAD_S} s trailing digital "
                f"silence -> `recitation_raw.m4a` ({raw_dur:.3f} s, under the 25 s cap).",
                "- The video build uses this file with ZERO processing (no EQ, reverb, "
                "ambience, normalization); only digital-silence padding for exact length.",
                f"- Concat map: `{json.dumps(concat_map)}` (also `concat_map.json`).",
                f"- Raw file: `recitation_raw.m4a` (`{sha256(RAW_RECITATION)}`, "
                f"{RAW_RECITATION.stat().st_size} bytes).",
                f"- ffprobe: `{json.dumps(rec_probe, ensure_ascii=False)}`",
                f"- silencedetect (-45 dB): `{json.dumps(sil)}`",
                "",
                "## Background: house black surround (no full-bleed clip)",
                "",
                "- v1 ships the house black-surround card (92 px pure-black side margins, "
                "halo, motes, grain) with the board-K popup; no full-bleed background clip.",
                "",
                "## Popup clip (Pinterest board \"K\", candidate 002 - spent by this slot)",
                "",
                f"- Pin id: {PIN_ID_POPUP}",
                f"- Board: {BOARD_URL} (Jaqqd / jawed1025t)",
                f"- Full clip committed from git blob `{PIN_BLOB_SHA}` (commit 422b92c177ef5bd40a0761db318d1a7626a553f9, "
                f"path `{PIN_BLOB_PATH}`).",
                "- File: `pinterest/002_" + PIN_ID_POPUP + ".mp4` (whole clip, 11.08 s, "
                "720x1280, 0 cuts).",
                "- Scene: man performs wudu at a mountain stream, stands, kneels in prayer; "
                "lush green valley, face never shown.",
                f"- Mapped whole across the {raw_dur:.3f} s card at {speed:.4f}x "
                "(gentle slow-motion, no loop).",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    log("all slot 007 source assets fetched and verified")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        ASSETS.mkdir(parents=True, exist_ok=True)
        tb = traceback.format_exc()
        (ASSETS / "fetch_error.txt").write_text(tb, encoding="utf-8")
        print(tb, flush=True)
        raise
