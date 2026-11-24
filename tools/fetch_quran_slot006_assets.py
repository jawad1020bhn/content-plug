#!/usr/bin/env python3
"""Importer for Slot 006: Mohamed Siddiq El-Minshawi, Ash-Sharh 94:5-6 (QF id 9).

Calm-voice slot: Minshawi Murattal (Hafs 'an 'Asim), the two "with hardship
comes ease" ayat. Primary audio: QF per-ayah MP3s
(audio.qurancdn.com/Minshawi/Murattal/mp3/094005.mp3 + 094006.mp3) joined
with a 0.5 s waqf-like pause. Fallback per file: QF chapter_recitations/9/94
full-surah MP3 trimmed to the verse segment.

Voice-first assembly (house retention revision): 0.35 s leading + voice track
+ 0.6 s trailing digital silence -> recitation_raw.m4a (~12.5 s, under 25 s cap).
Each ayah file is trimmed to last-word-end + 0.4 s (keeps the natural decay,
kills dead air) so the card fits the 12.1 s background window at ~1.03x.

Background: Pinterest board-K candidate 010 window 63.45-75.55 s (waterfall
cove: dark mossy canyon walls, waterfall breaking into a turquoise pool;
per-frame verified single continuous shot, 0 cuts). The window is NOT
downloaded here - it is cut locally from git blob 33ae4dc4... (commit
422b92c) into jobs/<slot>/ before the render.

Popup: Pinterest board-K candidate 006 used WHOLE (first-person prayer mat on
a rock ledge above an alpine lake, slow left-to-right pan, 7.8 s, 0 cuts);
committed under assets/.../pinterest/ and looped (forward + ping-pong) in the
video build to cover the card duration.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (compatible; content-plug-quran-slot006/1.0)"

QF_AYAH_URLS = {
    5: "https://audio.qurancdn.com/Minshawi/Murattal/mp3/094005.mp3",
    6: "https://audio.qurancdn.com/Minshawi/Murattal/mp3/094006.mp3",
}
QF_TIMING_URLS = {
    5: "https://api.quran.com/api/v4/verses/by_key/94:5?words=true&audio=9&word_fields=text_qpc_hafs",
    6: "https://api.quran.com/api/v4/verses/by_key/94:6?words=true&audio=9&word_fields=text_qpc_hafs",
}
QF_CHAPTER_URL = "https://api.quran.com/api/v4/chapter_recitations/9/94"
SAHEEH_URLS = {
    5: "https://quranenc.com/api/v1/translation/aya/english_saheeh/94/5?without_footnotes_symbols=1",
    6: "https://quranenc.com/api/v1/translation/aya/english_saheeh/94/6?without_footnotes_symbols=1",
}

# House voice-first assembly: onset lands ~0.40 s, mid scroll-settle.
LEAD_PAD_S = 0.35   # leading digital silence
GAP_S = 0.5         # waqf-like pause between the two ayat
TAIL_PAD_S = 0.6    # air for the true-loop match-dissolve + reverb wash
TRIM_TAIL_S = 0.4   # keep last-word-end + 0.4 s of each ayah file (natural decay)

PIN_ID_BG = "e1_AfqPShw8bwXQoW1ZpriWAQUldapMdZi7nE5QXT1Gb78O0tRAksu7kw"
PIN_BLOB_SHA = "33ae4dc41e3a03e01532638aa2140fb2b484e308"
PIN_CLIP_SHA256 = "839f93bd8e665c4ca4536896eefb515b3c52d78b1792c6048801526c1526bff5"
PIN_BLOB_PATH = "assets/al-baqarah-2-152-153/pinterest_candidates/010_" + PIN_ID_BG + ".mp4"
CLIP_LEN_S = 248.27
WINDOW_S = (63.45, 75.55)  # waterfall cove, per-frame verified single shot
BOARD_URL = "https://www.pinterest.com/jawed1025t/k/?invite_code=516f29ecb56e4a40a891ccc8089d146a&sender=1119215082304641687"

PIN_ID_POPUP = "e1_AfqPShwONkAF2MbmnVizxbOIXrhJbRjiVbHEuPuiU4biPcWNE0eyNA"

ROOT = Path(".")
SLOT = "006_ash-sharh_94-5-6_minshawi"
ASSETS = ROOT / "assets" / "quran" / SLOT
CACHE = ROOT / ".cache"
AYAH_MP3 = {v: CACHE / f"minshawi_09400{v}.mp3" for v in (5, 6)}
AYAH_TRIM = {v: CACHE / f"minshawi_09400{v}_trim.m4a" for v in (5, 6)}
CHAPTER_MP3 = CACHE / "minshawi_094.mp3"
CHAPTER_TRIM = {v: CACHE / f"minshawi_094_v{v}_trim.mp3" for v in (5, 6)}
RAW_RECITATION = ASSETS / "recitation_raw.m4a"
SOURCE_MD = ASSETS / "SOURCE.md"


def log(msg: str) -> None:
    print(f"[slot-006] {msg}", flush=True)


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


def download(url: str, dest: Path, timeout: int = 300) -> None:
    log(f"downloading {url} -> {dest}")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as out:
        while True:
            buf = resp.read(1024 * 1024)
            if not buf:
                break
            out.write(buf)


def fetch_json(url: str, dest: Path, timeout: int = 120) -> dict:
    log(f"fetching JSON {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
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


def fetch_fallback_chapter_trim(verse: int) -> tuple[str, str]:
    """Download full surah 94 and trim one verse. Returns (used_url, timing_note)."""
    req = urllib.request.Request(QF_CHAPTER_URL, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    seg = find_chapter_segment(data, verse)
    audio_url = find_audio_url(data)
    if seg is None or not audio_url:
        raise RuntimeError(f"fallback: chapter_recitations/9/94 gave no verse-{verse} segment or audio_url")
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
         "-vn", "-c:a", "copy", str(CHAPTER_TRIM[verse])],
        check=True,
    )
    note = f"fallback chapter trim {start_ms - 400}-{end_ms + 400} ms of surah 94 (verse {verse})"
    return audio_url, note


def fetch_voice(verse: int) -> tuple[Path, str, str]:
    """Returns (voice_file, used_audio_url, timing_note) for one verse."""
    dest = AYAH_MP3[verse]
    try:
        download(QF_AYAH_URLS[verse], dest, timeout=120)
        if dest.stat().st_size < 5000:
            raise RuntimeError(f"ayah mp3 too small ({dest.stat().st_size} bytes)")
        return dest, QF_AYAH_URLS[verse], f"QF per-ayah mp3 09400{verse}"
    except Exception as e:
        log(f"WARN primary per-ayah mp3 94:{verse} failed ({e}); using chapter fallback")
        used_url, note = fetch_fallback_chapter_trim(verse)
        return CHAPTER_TRIM[verse], used_url, note


def trim_to_word_end(src: Path, verse: int, qf: dict) -> Path:
    """Trim one ayah file to last-word-end + TRIM_TAIL_S (kills dead air)."""
    segs = qf["verse"]["audio"]["segments"]
    last_end_ms = segs[-1][3]
    keep = last_end_ms / 1000.0 + TRIM_TAIL_S
    src_dur = float(ffprobe_json(src)["format"]["duration"])
    keep = min(keep, src_dur)
    dest = AYAH_TRIM[verse]
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(src), "-t", f"{keep:.3f}",
         "-vn", "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
         str(dest)],
        check=True,
    )
    log(f"ayah 94:{verse}: file {src_dur:.3f} s, last word ends {last_end_ms} ms -> trimmed {keep:.3f} s")
    return dest


def assemble_raw(f5: Path, f6: Path) -> tuple[float, dict]:
    """Join 94:5 + 0.5 s gap + 94:6, prepend 0.35 s, append 0.6 s silence."""
    d0 = float(ffprobe_json(f5)["format"]["duration"])
    d1 = float(ffprobe_json(f6)["format"]["duration"])
    total = LEAD_PAD_S + d0 + GAP_S + d1 + TAIL_PAD_S
    fc = (
        "[0:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[v0];"
        "[1:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[v1];"
        f"aevalsrc=0:d={GAP_S}:s=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[gap];"
        "[v0][gap][v1]concat=n=3:v=0:a=1,"
        f"adelay={int(LEAD_PAD_S * 1000)}:all=1,apad=whole_dur={total:.3f}[aout]"
    )
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(f5), "-i", str(f6), "-filter_complex", fc,
         "-map", "[aout]", "-vn", "-ar", "44100", "-ac", "2",
         "-c:a", "aac", "-b:a", "192k", str(RAW_RECITATION)],
        check=True,
    )
    concat_map = {
        "lead_s": LEAD_PAD_S,
        "file5_s": round(d0, 3),
        "gap_s": GAP_S,
        "file6_offset_s": round(LEAD_PAD_S + d0 + GAP_S, 3),
        "file6_s": round(d1, 3),
        "tail_s": TAIL_PAD_S,
        "total_s": round(total, 3),
    }
    (ASSETS / "concat_map.json").write_text(
        json.dumps(concat_map, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return float(ffprobe_json(RAW_RECITATION)["format"]["duration"]), concat_map


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

    f5, url5, note5 = fetch_voice(5)
    f6, url6, note6 = fetch_voice(6)

    qf5 = fetch_json(QF_TIMING_URLS[5], ASSETS / "qf_94-5.json")
    qf6 = fetch_json(QF_TIMING_URLS[6], ASSETS / "qf_94-6.json")
    fetch_json(SAHEEH_URLS[5], ASSETS / "saheeh_94-5.json")
    fetch_json(SAHEEH_URLS[6], ASSETS / "saheeh_94-6.json")

    def seg_span(qf: dict) -> str:
        segs = qf["verse"]["audio"]["segments"]
        return f"first word {segs[0][2]} ms, last word ends {segs[-1][3]} ms"

    timing_note = f"94:5 [{seg_span(qf5)}] ({note5}); 94:6 [{seg_span(qf6)}] ({note6})"

    t5 = trim_to_word_end(f5, 5, qf5)
    t6 = trim_to_word_end(f6, 6, qf6)
    raw_dur, concat_map = assemble_raw(t5, t6)
    log(f"raw recitation {RAW_RECITATION} ({RAW_RECITATION.stat().st_size} bytes, {raw_dur:.3f} s)")
    if raw_dur > 25.0:
        raise RuntimeError(f"raw recitation {raw_dur:.3f} s exceeds the 25 s cap")
    win_len = WINDOW_S[1] - WINDOW_S[0]
    speed = raw_dur / win_len

    rec_probe = ffprobe_json(RAW_RECITATION)
    sil = silence_report(RAW_RECITATION)

    (ASSETS / "selection.txt").write_text(
        "010 window 63.45-75.55 s - waterfall breaking through dark mossy canyon walls into "
        "a turquoise pool, slow forward drift; single continuous shot, 0 cuts, no people, "
        "no text; sub-window cut to the card duration at ~1.03x (raw original colors)\n",
        encoding="utf-8",
    )

    SOURCE_MD.write_text(
        "\n".join(
            [
                "# Source assets - slot 006 - Ash-Sharh 94:5-6 - Mohamed Siddiq El-Minshawi",
                "",
                "Output: `outputs/quran-006_ash-sharh_94-5-6_minshawi_en_1080x1920_v1.mp4`",
                "Post package: `metadata/006_ash-sharh_94-5-6_minshawi/`",
                "",
                "## Recitation",
                "",
                "- Reciter: Mohamed Siddiq El-Minshawi, Murattal (Hafs 'an 'Asim), QF reciter ID 9.",
                f"- Audio sources: {url5} + {url6} joined with a {GAP_S} s waqf-like pause.",
                f"- Timing sources: {QF_TIMING_URLS[5]} and {QF_TIMING_URLS[6]}",
                "  (mirrored to `qf_94-5.json` / `qf_94-6.json`).",
                f"- {timing_note}.",
                "- English: Saheeh International translation via QuranEnc",
                f"  ({SAHEEH_URLS[5]}, {SAHEEH_URLS[6]}, mirrored to `saheeh_94-*.json`).",
                f"- Per-ayah trim: each file cut to last-word-end + {TRIM_TAIL_S} s (natural decay kept).",
                f"- Raw assembly (voice-first): {LEAD_PAD_S} s leading + voice track + {TAIL_PAD_S} s trailing",
                f"  digital silence -> `recitation_raw.m4a` ({raw_dur:.3f} s, under the 25 s cap).",
                f"- Concat map: `{json.dumps(concat_map)}` (also `concat_map.json`).",
                f"- Raw trim file: `recitation_raw.m4a` (`{sha256(RAW_RECITATION)}`, "
                f"{RAW_RECITATION.stat().st_size} bytes).",
                f"- ffprobe: `{json.dumps(rec_probe, ensure_ascii=False)}`",
                f"- silencedetect (-45 dB): `{json.dumps(sil)}`",
                "",
                "## Background clip (Pinterest board \"K\", candidate 010 - freed pool, rescouted)",
                "",
                f"- Pin id: {PIN_ID_BG}",
                f"- Board: {BOARD_URL} (Jaqqd / jawed1025t)",
                f"- Full clip re-imported from git blob `{PIN_BLOB_SHA}` (commit 422b92c177ef5bd40a0761db318d1a7626a553f9, "
                f"path `{PIN_BLOB_PATH}`); full-clip sha256 `{PIN_CLIP_SHA256}`.",
                f"- Used window: {WINDOW_S[0]:.2f}-{WINDOW_S[1]:.2f} s of the {CLIP_LEN_S} s montage "
                "(per-frame verified: hard cut at 63.38-63.40 s, freeze+dissolve at 75.60 s; "
                "1 fps strip `jobs/_scout006/strip_pool_62_77.png`); the window is a single continuous "
                f"shot (0 cuts) covering the {raw_dur:.3f} s card at {speed:.4f}x.",
                "- Scene: waterfall breaking through dark mossy canyon walls into a turquoise pool, "
                "slow forward drift - no people, no text.",
                "- Color treatment: raw original colors preserved (no color grade).",
                "- Rights: user-supplied board; user stated no licence issue. Clear rights before commercial release.",
                "",
                "## Popup clip (Pinterest board \"K\", candidate 006 - spent by this slot)",
                "",
                f"- Pin id: {PIN_ID_POPUP}",
                "- File: `pinterest/006_" + PIN_ID_POPUP + ".mp4` (whole clip, 7.8 s, 576x1024, 0 cuts).",
                "- Scene: first-person prayer mat on a rock ledge above an alpine lake, slow "
                "left-to-right pan; looped (forward + ping-pong) in the video build.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    log("all slot 006 source assets fetched and verified")


if __name__ == "__main__":
    main()
