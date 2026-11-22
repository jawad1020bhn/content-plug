#!/usr/bin/env python3
"""Build verified Quran-recitation subtitles from canonical text + known timing.

This is the implementation behind the ``quran-subtitles`` skill. It deliberately
does NOT transcribe audio, OCR a random website, or machine-translate the Quran.
It joins:

  1. canonical Arabic text (prefer QPC Hafs ``text_qpc_hafs`` words),
  2. one published translation (verbatim, with only display markup removed), and
  3. precomputed verse/word timing from Quran Foundation or QUL segment data,

then writes ASS (primary) and optional SRT (review-only) cues. ASS is rendered by
libass with complex shaping so Arabic Uthmani text is not reversed or broken.

Best-fit fonts (verified with libass + FriBidi + HarfBuzz):
  Arabic .... KFGQPC HAFS Uthmanic Script  (UthmanicHafs1Ver18.ttf)
  English ... Cormorant Garamond Light     (CormorantGaramond-wght.ttf, OFL 1.1)

Raw Quran Foundation API JSON, generated ASS containing Quran text, and font
binaries are NOT committed to the public repo. Use local ignored job files and
credit the sources in the post caption/description, never burned into the video.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLED_FONT_DIR = REPO_ROOT / "clip-desk" / "skills" / "quran-subtitles" / "fonts"
DEFAULT_FONT_DIR = os.environ.get("CLIP_DESK_QURAN_FONT_DIR", str(BUNDLED_FONT_DIR))
DEFAULT_ARABIC_FONT = "KFGQPC HAFS Uthmanic Script"
DEFAULT_ENGLISH_FONT = "Cormorant Garamond Light"
FONT_EXTS = {".ttf", ".otf", ".woff", ".woff2"}
WAQF_MARKS = "ۚۗۖۙۛۜ۝۞"


class QuranSubtitleError(Exception):
    pass


def warn(msg: str, strict: bool = False) -> None:
    print("WARN: " + msg, file=sys.stderr)
    if strict:
        raise QuranSubtitleError(msg)


def hard_error(msg: str) -> None:
    raise QuranSubtitleError(msg)


def clean_text(value: Any) -> str:
    """Strip only display markup; do not paraphrase or 'fix' the wording."""
    if value is None:
        return ""
    if isinstance(value, dict):
        value = value.get("text") or value.get("translation") or ""
    if isinstance(value, list):
        value = " ".join(clean_text(v) for v in value)
    s = str(value)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def ass_escape(s: str) -> str:
    s = s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    return s.replace("\n", "\\N")


def wrap_english(s: str, cpl: int) -> str:
    lines = textwrap.wrap(
        s,
        width=cpl,
        break_long_words=False,
        break_on_hyphens=False,
        replace_whitespace=False,
        drop_whitespace=True,
    )
    return "\n".join(lines) if lines else s


def arabic_visual_len(s: str) -> int:
    """Approximate display width: count base characters, not harakat/whitespace."""
    return sum(1 for ch in s if not unicodedata.combining(ch) and not ch.isspace())


def wrap_arabic(s: str, cpl: int, max_lines: int = 2) -> str:
    """Wrap QPC Arabic at word boundaries for a narrow phone card."""
    if cpl <= 0 or not s:
        return s
    lines: List[str] = []
    cur: List[str] = []
    for word in s.split():
        candidate = " ".join(cur + [word])
        if cur and arabic_visual_len(candidate) > cpl:
            lines.append(" ".join(cur))
            cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(" ".join(cur))
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [" ".join(lines[max_lines - 1 :])]
    return "\n".join(lines)


def parse_verse_key(key: str) -> Tuple[int, int]:
    m = re.fullmatch(r"(\d+):(\d+)", str(key).strip())
    if not m:
        raise QuranSubtitleError("bad verse_key %r; expected surah:ayah" % key)
    return int(m.group(1)), int(m.group(2))


def verse_key_sort(k: str) -> Tuple[int, int]:
    return parse_verse_key(k)


def parse_range(spec: str) -> Tuple[int, List[str]]:
    """Accept 19:30, 19:30-33, or 19:30-19:33."""
    m = re.fullmatch(r"(\d+):(\d+)(?:-(?:(\d+):)?(\d+))?", spec.strip())
    if not m:
        raise QuranSubtitleError("bad --range %r; use 19:30-33" % spec)
    chapter, first = int(m.group(1)), int(m.group(2))
    end_chapter = int(m.group(3)) if m.group(3) else chapter
    last = int(m.group(4)) if m.group(4) else first
    if end_chapter != chapter:
        raise QuranSubtitleError("--range cannot cross surahs in this skill")
    if last < first:
        raise QuranSubtitleError("--range end ayah is before start ayah")
    return chapter, ["%d:%d" % (chapter, a) for a in range(first, last + 1)]


def first_number(obj: Dict[str, Any], *names: str) -> Optional[float]:
    for name in names:
        if name in obj and obj[name] is not None:
            try:
                return float(obj[name])
            except (TypeError, ValueError):
                return None
    return None


def join_qpc_words(words: Any) -> str:
    if not isinstance(words, list):
        return ""
    out = []
    for w in words:
        if isinstance(w, str):
            out.append(w)
            continue
        if not isinstance(w, dict):
            continue
        if w.get("char_type_name") == "end":
            continue
        t = w.get("text_qpc_hafs") or w.get("text_uthmani") or w.get("text") or ""
        if t:
            out.append(str(t))
    return " ".join(out)


def normalize_verse(raw: Any, chapter: Optional[int]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise QuranSubtitleError("verse entry is not an object")
    # unwrap a list of by_key API responses
    if "verse" in raw and isinstance(raw["verse"], dict):
        raw = raw["verse"]

    ch = raw.get("chapter_id") or raw.get("chapter_number") or raw.get("sura") or chapter
    ayah = raw.get("verse_number") or raw.get("aya") or raw.get("id") or raw.get("ayah")
    key = raw.get("verse_key") or raw.get("verseKey")
    if not key:
        if ch is None or ayah is None:
            raise QuranSubtitleError("cannot determine verse_key; pass --chapter")
        key = "%s:%s" % (int(ch), int(ayah))
    key = str(key).strip()

    arabic = raw.get("text_qpc_hafs") or join_qpc_words(raw.get("words"))
    arabic = arabic or raw.get("text_uthmani") or raw.get("arabic_text") or raw.get("uthmani") or raw.get("text") or ""
    arabic_source = "text_qpc_hafs" if raw.get("text_qpc_hafs") or join_qpc_words(raw.get("words")) else "text_uthmani_or_other"

    trans = raw.get("translation")
    if not trans and isinstance(raw.get("translations"), list) and raw["translations"]:
        first = raw["translations"][0]
        trans = first.get("text") if isinstance(first, dict) else first
    trans = clean_text(trans)

    tname = ""
    if isinstance(raw.get("translations"), list) and raw["translations"]:
        first = raw["translations"][0]
        if isinstance(first, dict):
            tname = first.get("resource_name") or first.get("name") or ""
    tname = tname or clean_text(raw.get("translation_name") or raw.get("translation_source") or "")

    return {
        "verse_key": key,
        "arabic": str(arabic).strip(),
        "arabic_source": arabic_source,
        "translation": trans,
        "translation_name": tname,
        "source_url": clean_text(raw.get("source_url") or raw.get("source") or ""),
    }


def load_verses(path: str, chapter: Optional[int], overrides: Optional[str]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    meta: Dict[str, Any] = {}
    raw: Any = None
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        meta = {
            "translation_name": clean_text(data.get("translation_name") or data.get("translation") or ""),
            "source_url": clean_text(data.get("source_url") or data.get("source") or ""),
            "reciter": clean_text(data.get("reciter") or ""),
        }
        if "verses" in data:
            raw = data["verses"]
        elif "verse" in data:
            raw = [data["verse"]]
        elif "result" in data:
            raw = data["result"]
        elif "ayahs" in data:
            raw = data["ayahs"]
        else:
            raw = data.get("data") or []
    if raw is None:
        raw = []
    if isinstance(raw, dict):
        raw = list(raw.values())

    verses = []
    for item in raw:
        if isinstance(item, dict) and "verse" in item and isinstance(item["verse"], dict):
            item = item["verse"]
        verses.append(normalize_verse(item, chapter))
    if not verses:
        raise QuranSubtitleError("no verses found in %s" % path)

    if overrides:
        ov = json.loads(Path(overrides).read_text(encoding="utf-8"))
        if not isinstance(ov, dict):
            raise QuranSubtitleError("--translation-overrides must be a JSON object")
        ometa = ov.pop("_meta", {}) if isinstance(ov, dict) else {}
        for v in verses:
            if v["verse_key"] in ov:
                v["translation"] = clean_text(ov[v["verse_key"]])
        if isinstance(ometa, dict):
            meta["translation_name"] = clean_text(ometa.get("translation_name") or meta.get("translation_name") or "")
            meta["source_url"] = clean_text(ometa.get("source_url") or meta.get("source_url") or "")
    return verses, meta


def load_timings(path: str) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    meta: Dict[str, Any] = {}
    rows: Any = None
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        meta = {
            "reciter": clean_text(data.get("reciter") or data.get("reciter_name") or ""),
            "source_url": clean_text(data.get("source_url") or data.get("source") or ""),
            "audio_url": clean_text(data.get("audio_url") or ""),
        }
        if isinstance(data.get("audio_file"), dict):
            af = data["audio_file"]
            meta["audio_url"] = clean_text(af.get("audio_url") or meta.get("audio_url") or "")
            rows = af.get("timestamps") or af.get("segments") or []
        elif "timestamps" in data:
            rows = data["timestamps"]
        elif "verses" in data:
            rows = data["verses"]
        elif "result" in data:
            rows = data["result"]
        else:
            # QUL-style dict keyed by verse_key
            rows = [dict(v, verse_key=k) for k, v in data.items() if isinstance(v, dict) and ":" in k]
    if rows is None:
        rows = []
    if isinstance(rows, dict):
        rows = [dict(v, verse_key=k) for k, v in rows.items() if isinstance(v, dict)]

    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("verse_key") or row.get("key") or "").strip()
        if not key:
            continue
        start = first_number(row, "start_ms", "timestamp_from", "from", "start")
        end = first_number(row, "end_ms", "timestamp_to", "to", "end")
        duration = first_number(row, "duration_ms", "duration")
        if start is None and end is not None and duration is not None:
            start = end - abs(duration)
        if end is None and start is not None and duration is not None:
            end = start + abs(duration)
        if start is None or end is None:
            raise QuranSubtitleError("timing for %s has no start/end" % key)
        if end < start:
            # legacy Quran Foundation rows sometimes carry a negative duration
            start, end = min(start, end), max(start, end)
        segs = row.get("segments") or []
        out[key] = {"start_ms": float(start), "end_ms": float(end), "segments": segs}
    if not out:
        raise QuranSubtitleError("no timings found in %s" % path)
    return out, meta


def ass_time(ms: float) -> str:
    cs = int(round(max(0.0, ms) / 10.0))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return "%d:%02d:%02d.%02d" % (h, m, s, cs)


def srt_time(ms: float) -> str:
    ms = int(round(max(0.0, ms)))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def style_line(name: str, font: str, size: int, color: str, alignment: int = 8) -> str:
    # ASS colours are &HAABBGGRR; 00 alpha = opaque.
    return (
        "Style: %s,%s,%d,%s,&H000000FF,&H00000000,&H00000000,"
        "0,0,0,0,100,100,0,0,1,0,0,%d,80,80,0,1"
        % (name, font, size, color, alignment)
    )


def dialogue(style: str, start: str, end: str, text: str, x: int, y: int, fade: int) -> str:
    prefix = "{\\pos(" + str(x) + "," + str(y) + ")\\fad(" + str(fade) + "," + str(fade) + ")}"
    return "Dialogue: 0,%s,%s,%s,,0,0,0,,%s%s" % (start, end, style, prefix, ass_escape(text))


def build_ass(
    cues: List[Dict[str, Any]],
    width: int,
    height: int,
    arabic_font: str,
    english_font: str,
    surah_name: str,
    fade_ms: int,
    sizes: Dict[str, int],
    layers: set,
    positions: Dict[str, int],
) -> str:
    header_y = positions["header"]
    arabic_y = positions["arabic"]
    english_y = positions["english"]
    ref_y = positions["ref"]
    center_x = width // 2
    fade = max(0, int(fade_ms / 10))  # ASS \fad is centiseconds

    head = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: %d" % width,
        "PlayResY: %d" % height,
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: None",
        "Title: %s verified subtitles" % surah_name,
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        style_line("Header", english_font, sizes["header"], "&H00CFC7B8"),
        style_line("QuranArabic", arabic_font, sizes["arabic"], "&H00F5EFE6"),
        style_line("QuranEnglish", english_font, sizes["english"], "&H00F5EFE6"),
        style_line("QuranRef", english_font, sizes["ref"], "&H00C9BFAF"),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    first_start = ass_time(cues[0]["start_ms"])
    last_end = ass_time(cues[-1]["end_ms"])
    if "header" in layers:
        head.append(dialogue("Header", first_start, last_end, surah_name, center_x, header_y, fade))

    for c in cues:
        st, en = ass_time(c["start_ms"]), ass_time(c["end_ms"])
        if "arabic" in layers:
            head.append(dialogue("QuranArabic", st, en, c["arabic_display"], center_x, arabic_y, fade))
        if "english" in layers:
            head.append(dialogue("QuranEnglish", st, en, c["english_display"], center_x, english_y, fade))
        if "ref" in layers:
            head.append(dialogue("QuranRef", st, en, "[%s]" % c["verse_key"], center_x, ref_y, fade))
    return "\n".join(head) + "\n"


def build_srt(cues: List[Dict[str, Any]]) -> str:
    out = []
    for i, c in enumerate(cues, 1):
        body = "[%s]\n%s\n%s" % (
            c["verse_key"],
            c["arabic"],
            c["translation"].replace("\n", " "),
        )
        out.append("%d\n%s --> %s\n%s\n" % (i, srt_time(c["start_ms"]), srt_time(c["end_ms"]), body))
    return "\n".join(out)


def check_font_dir(font_dir: Path, strict: bool) -> None:
    if not font_dir.is_dir():
        hard_error("font dir does not exist: %s" % font_dir)
    fonts = [f for f in font_dir.iterdir() if f.is_file() and f.suffix.lower() in FONT_EXTS]
    others = [f for f in font_dir.iterdir() if f.is_file() and f not in fonts]
    if not fonts:
        warn("font dir has no .ttf/.otf/.woff files: %s" % font_dir, strict)
    if others:
        warn("font dir contains non-font files; libass may try to load them: %s" % ", ".join(f.name for f in others), strict)
    has_arabic = any(("UthmanicHafs" in f.name or "KFGQPC" in f.name or "Hafs" in f.name) for f in fonts)
    has_english = any("Cormorant" in f.name for f in fonts)
    if not has_arabic:
        warn("font dir has no KFGQPC/UthmanicHafs file; QPC Hafs text may fall back to a wrong font", strict)
    if not has_english:
        warn("font dir has no Cormorant Garamond file; English will fall back to a generic serif", strict)


def find_ffmpeg(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    env = os.environ.get("CLIP_DESK_FFMPEG")
    if env:
        return env
    which = shutil.which("ffmpeg")
    if which:
        return which
    cand = REPO_ROOT / ".venv" / "bin" / "ffmpeg"
    if cand.exists():
        return str(cand)
    hard_error("ffmpeg not found; run ./setup.sh or pass --ffmpeg /path/to/ffmpeg")


def ff_filter_path(p: Path) -> str:
    # Enough for absolute Linux paths used by this skill.
    return str(p.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,")


def make_preview(
    ass_path: Path,
    preview_path: Path,
    font_dir: Path,
    width: int,
    height: int,
    duration_s: float,
    preview_time: float,
    background: Optional[str],
    dim: float,
    ffmpeg: str,
) -> None:
    ass_path = ass_path.resolve()
    font_dir = font_dir.resolve()
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    t = max(0.03, min(preview_time, max(0.05, duration_s - 0.05)))
    duration_s = max(duration_s, t + 0.2)
    ass_filter = "ass=filename=%s:fontsdir=%s:shaping=1" % (ff_filter_path(ass_path), ff_filter_path(font_dir))
    vf = []
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-y"]
    if background:
        bg = Path(background)
        if not bg.exists():
            hard_error("background not found: %s" % bg)
        if bg.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            cmd += ["-loop", "1", "-framerate", "30", "-i", str(bg.resolve())]
        else:
            cmd += ["-stream_loop", "-1", "-i", str(bg.resolve())]
        cmd += ["-t", "%.3f" % duration_s]
        vf += [
            "fps=30",
            "scale=%d:%d:force_original_aspect_ratio=increase" % (width, height),
            "crop=%d:%d" % (width, height),
        ]
        if dim > 0:
            vf += ["eq=brightness=-%.3f:saturation=0.92" % dim]
    else:
        cmd += ["-f", "lavfi", "-i", "color=c=black:s=%dx%d:d=%.3f:r=30" % (width, height, duration_s)]
        vf += ["fps=30"]
    vf += [ass_filter, "select='gte(t,%.3f)'" % t]
    cmd += ["-vf", ",".join(vf), "-an", "-frames:v", "1", "-update", "1", str(preview_path.resolve())]
    subprocess.run(cmd, check=True)


def parse_layers(spec: str, strict: bool) -> set:
    allowed = {"header", "arabic", "english", "ref"}
    layers = {item.strip().lower() for item in spec.split(",") if item.strip()}
    unknown = sorted(layers - allowed)
    if unknown:
        hard_error("unknown --layers value(s): %s" % ", ".join(unknown))
    if not layers:
        hard_error("--layers needs at least one of: header,arabic,english,ref")
    if "arabic" not in layers:
        warn("Arabic layer is disabled; canonical text must be checked elsewhere before posting", strict)
    return layers


def make_video(
    args: argparse.Namespace,
    ass_path: Path,
    font_dir: Path,
    duration_s: float,
    original_first_start_ms: float,
    ffmpeg: str,
) -> None:
    """Render the final MP4 with libass; never upload or post it."""
    video_out = Path(args.video_out).expanduser().resolve()
    video_out.parent.mkdir(parents=True, exist_ok=True)
    if "outputs/" not in (str(video_out) + "/"):
        warn("final MP4 should normally be written under outputs/: %s" % video_out, args.strict)

    if args.source_video and args.background:
        warn("both --source-video and --background were given; using --source-video", args.strict)
    visual = args.source_video or args.background
    if not visual:
        hard_error("--video-out needs --source-video or --background")
    visual_path = Path(visual).expanduser().resolve()
    if not visual_path.exists():
        hard_error("visual source not found: %s" % visual_path)
    still = visual_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    is_background = bool(args.background and not args.source_video)

    # With --auto-offset the ASS cues start at zero; trim the corresponding full-surah source.
    source_start_ms = args.source_start_ms if args.source_start_ms is not None else (original_first_start_ms if args.auto_offset else 0.0)
    audio_start_ms = args.audio_start_ms if args.audio_start_ms is not None else (original_first_start_ms if args.auto_offset else 0.0)
    ass_filter = "ass=filename=%s:fontsdir=%s:shaping=1" % (
        ff_filter_path(ass_path.resolve()),
        ff_filter_path(font_dir.resolve()),
    )
    vf = [
        "fps=%d" % args.fps,
        "scale=%d:%d:force_original_aspect_ratio=increase" % (args.width, args.height),
        "crop=%d:%d" % (args.width, args.height),
    ]
    if args.dim > 0:
        vf += ["eq=brightness=-%.3f:saturation=0.92" % args.dim]
    vf += [ass_filter]

    cmd = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-y"]
    if still:
        cmd += ["-loop", "1", "-framerate", str(args.fps), "-i", str(visual_path)]
    elif is_background:
        # A looping background clip; do not seek it to recitation timestamps.
        cmd += ["-stream_loop", "-1", "-i", str(visual_path)]
    elif source_start_ms > 0:
        cmd += ["-ss", "%.3f" % (source_start_ms / 1000.0), "-i", str(visual_path)]
    else:
        cmd += ["-i", str(visual_path)]

    has_external_audio = bool(args.audio)
    if has_external_audio:
        audio_path = Path(args.audio).expanduser().resolve()
        if not audio_path.exists():
            hard_error("audio not found: %s" % audio_path)
        cmd += ["-ss", "%.3f" % (audio_start_ms / 1000.0), "-i", str(audio_path)]

    cmd += ["-t", "%.3f" % duration_s, "-vf", ",".join(vf)]
    cmd += ["-map", "0:v:0"]
    if has_external_audio:
        cmd += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"]
    else:
        # Optional map keeps still-image/background-only renders valid; no explicit
        # bitrate here, because ffmpeg warns when a bitrate option has no audio stream.
        cmd += ["-map", "0:a:0?", "-c:a", "aac"]
    cmd += [
        "-r", str(args.fps),
        "-c:v", "libx264",
        "-preset", args.preset,
        "-crf", str(args.crf),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(video_out),
    ]
    subprocess.run(cmd, check=True)


def write_credits(path: Path, args: argparse.Namespace, verse_meta: Dict[str, Any], timing_meta: Dict[str, Any]) -> None:
    qsource = clean_text(args.quran_source) or "Quran Foundation"
    if qsource.lower().startswith("quran foundation"):
        text = [
            "Post caption / description credit — DO NOT burn this into the video.",
            "",
            "Quran data provided by Quran Foundation.",
        ]
    else:
        text = [
            "Post caption / description credit — DO NOT burn this into the video.",
            "",
            "Quran text: %s." % qsource,
        ]
    text += [
        "Arabic: QPC Hafs / UthmanicHafs1Ver18 — King Fahd Glorious Quran Printing Complex (KFGQPC).",
    ]
    tname = args.translation_credit or clean_text(verse_meta.get("translation_name")) or "Named published translation"
    edition = clean_text(args.translation_edition)
    if edition:
        tname = "%s (%s)" % (tname, edition)
    text.append("Translation: %s." % tname)
    reciter = args.reciter or clean_text(timing_meta.get("reciter")) or "Named reciter"
    text.append("Reciter: %s." % reciter)
    tsource = clean_text(args.timing_source) or clean_text(timing_meta.get("source_url")) or "QF/QUL segment data"
    text.append("Timing: %s." % tsource)
    text.append("Fonts: KFGQPC Uthmanic Hafs + Cormorant Garamond (SIL OFL 1.1).")
    if args.background_credit:
        text.append("Background: %s." % args.background_credit)
    src = args.source_url or clean_text(timing_meta.get("source_url")) or clean_text(verse_meta.get("source_url"))
    if src:
        text.append("Source: %s" % src)
    text += [
        "",
        "Human review required before posting. Nothing is uploaded automatically.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(text) + "\n", encoding="utf-8")


def make_cues(
    verses: List[Dict[str, Any]],
    timings: Dict[str, Dict[str, Any]],
    wanted: List[str],
    offset_ms: float,
    auto_offset: bool,
    english_cpl: int,
    arabic_cpl: int,
    arabic_lines: int,
    strict: bool,
) -> List[Dict[str, Any]]:
    by_key = {v["verse_key"]: v for v in verses}
    missing_verses = [k for k in wanted if k not in by_key]
    if missing_verses:
        hard_error("missing verse text for: %s" % ", ".join(missing_verses))
    missing_timings = [k for k in wanted if k not in timings]
    if missing_timings:
        hard_error("missing timing for: %s" % ", ".join(missing_timings))

    first_start = timings[wanted[0]]["start_ms"]
    if auto_offset:
        # Shift the source timings to zero, then keep any user-requested lead-in.
        offset_ms += -first_start
    cues = []
    for key in wanted:
        v = by_key[key]
        t = timings[key]
        start = t["start_ms"] + offset_ms
        end = t["end_ms"] + offset_ms
        if start < 0:
            warn("cue %s starts before 0 after offset; clamped" % key, strict)
            start = 0.0
        if end <= start:
            hard_error("cue %s has non-positive duration" % key)
        if not v["arabic"]:
            hard_error("verse %s has no Arabic text" % key)
        if not v["translation"]:
            warn("verse %s has no translation; pass --translation-overrides" % key, strict)
        if v["arabic_source"] not in {"text_qpc_hafs", "synthetic"}:
            warn("verse %s is not text_qpc_hafs; with UthmanicHafs1Ver18 prefer QF word_fields=text_qpc_hafs" % key, strict)
        arabic_display = wrap_arabic(v["arabic"], arabic_cpl, arabic_lines)
        if len(arabic_display.split("\n")) > arabic_lines:
            warn("verse %s Arabic exceeds %d lines; increase --arabic-cpl or reduce --arabic-size" % (key, arabic_lines), False)
        english = clean_text(v["translation"])
        english_display = wrap_english(english, english_cpl)
        if any(len(line) > english_cpl + 8 for line in english_display.split("\n")):
            # Style warning, not a data-integrity error: human QA decides the split.
            warn("verse %s has a long English line; split at punctuation, do not trim Quran text" % key, False)
        dur = (end - start) / 1000.0
        cps = len(english.replace("\n", "")) / dur if dur else 999
        cues.append(
            {
                "verse_key": key,
                "arabic": v["arabic"],
                "arabic_display": arabic_display,
                "translation": english,
                "english_display": english_display,
                "start_ms": start,
                "end_ms": end,
                "dur_s": dur,
                "cps": cps,
                "arabic_source": v["arabic_source"],
            }
        )
    return cues


def validate_cues(cues: List[Dict[str, Any]], args: argparse.Namespace) -> None:
    for c in cues:
        # Reading-rate and duration checks are advisory: exact Quran timings can be
        # longer than generic subtitle limits and must be reviewed by eye/ear.
        if c["dur_s"] < args.min_duration:
            warn("%s is shorter than %.3fs" % (c["verse_key"], args.min_duration), False)
        if c["dur_s"] > args.max_duration:
            warn("%s is longer than %.1fs; split at a waqf/breath, do not shorten the verse" % (c["verse_key"], args.max_duration), False)
        if c["cps"] > args.max_cps:
            warn("%s reads at %.1f CPS (> %.1f); give it more time or split the translation at punctuation" % (c["verse_key"], c["cps"], args.max_cps), False)
        parse_verse_key(c["verse_key"])
    for a, b in zip(cues, cues[1:]):
        gap = b["start_ms"] - a["end_ms"]
        if gap < 0:
            warn("overlapping cues %s / %s" % (a["verse_key"], b["verse_key"]), args.strict)
        # QF/QUL verse timings are often exactly contiguous. A two-frame gap is a
        # presentation preference, not a reason to reject authoritative timing.


def selftest_data() -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Dict[str, Any]], Dict[str, Any], int, List[str]]:
    verses = [
        {
            "verse_key": "0:1",
            "arabic": "هذا اختبار للخط العربي",
            "translation": "This is a synthetic font and timing test.",
            "translation_name": "Synthetic test text",
            "arabic_source": "synthetic",
            "source_url": "",
        },
        {
            "verse_key": "0:2",
            "arabic": "سطر ثانٍ للاختبار",
            "translation": "Second synthetic test line.",
            "translation_name": "Synthetic test text",
            "arabic_source": "synthetic",
            "source_url": "",
        },
    ]
    timings = {
        "0:1": {"start_ms": 0.0, "end_ms": 2500.0, "segments": []},
        "0:2": {"start_ms": 2500.0, "end_ms": 5000.0, "segments": []},
    }
    return verses, {"translation_name": "Synthetic test text"}, timings, {"reciter": "Synthetic"}, 0, ["0:1", "0:2"]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Build verified Quran-recitation ASS/SRT subtitles.")
    ap.add_argument("--verses", help="JSON: QF by_chapter/by_key, QuranEnc result, quran-json, or normalized verses list")
    ap.add_argument("--timings", help="JSON: QF audio_file.timestamps, QUL segments, or normalized timing list")
    ap.add_argument("--range", dest="range_spec", help="verse range, e.g. 19:30-33")
    ap.add_argument("--chapter", type=int, help="default surah number for datasets without verse_key")
    ap.add_argument("--translation-overrides", help="JSON object mapping verse_key -> verbatim translation text; optional _meta")
    ap.add_argument("--out", help="output .ass path (required unless --selftest)")
    ap.add_argument("--srt", help="optional review-only .srt path")
    ap.add_argument("--credits-out", help="optional post-caption credit file")
    ap.add_argument("--preview", help="optional PNG preview path; requires --font-dir")
    ap.add_argument("--video-out", help="optional final MP4 path; normally outputs/<video-name>.mp4 (see docs/CATALOG.md)")
    ap.add_argument("--source-video", help="source recitation video for final MP4")
    ap.add_argument("--audio", help="external recitation audio for final MP4")
    ap.add_argument("--video-duration", type=float, default=None, help="override final MP4 duration in seconds")
    ap.add_argument("--source-start-ms", type=float, default=None, help="seek full source video to this timestamp")
    ap.add_argument("--audio-start-ms", type=float, default=None, help="seek external audio to this timestamp")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--font-dir", default=DEFAULT_FONT_DIR, help="directory holding the two best-fit font files")
    ap.add_argument("--ffmpeg", help="explicit ffmpeg path")
    ap.add_argument("--arabic-font", default=DEFAULT_ARABIC_FONT)
    ap.add_argument("--english-font", default=DEFAULT_ENGLISH_FONT)
    ap.add_argument("--layers", default="header,arabic,english,ref", help="comma-separated ASS layers: header,arabic,english,ref")
    ap.add_argument("--surah-name", default="Surah")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--background", help="optional scenic image/video for preview or final MP4")
    ap.add_argument("--dim", type=float, default=0.22, help="background dim for preview/MP4, 0..0.5")
    ap.add_argument("--fade-ms", type=int, default=400)
    ap.add_argument("--english-cpl", type=int, default=42)
    ap.add_argument("--arabic-cpl", type=int, default=0, help="wrap Arabic after this many base characters; 0 disables wrapping")
    ap.add_argument("--arabic-lines", type=int, default=2, help="maximum Arabic lines when --arabic-cpl is set")
    ap.add_argument("--header-y", type=int, default=None, help="bottom-centre ASS y for the surah header")
    ap.add_argument("--arabic-y", type=int, default=None, help="bottom-centre ASS y for the Arabic layer")
    ap.add_argument("--english-y", type=int, default=None, help="bottom-centre ASS y for the English layer")
    ap.add_argument("--ref-y", type=int, default=None, help="bottom-centre ASS y for the verse reference")
    ap.add_argument("--arabic-size", type=int, default=62)
    ap.add_argument("--english-size", type=int, default=46)
    ap.add_argument("--header-size", type=int, default=36)
    ap.add_argument("--ref-size", type=int, default=28)
    ap.add_argument("--offset-ms", type=float, default=0.0)
    ap.add_argument("--auto-offset", action="store_true", help="shift first selected cue to 0 ms")
    ap.add_argument("--preview-time", type=float, default=None, help="preview timestamp in seconds")
    ap.add_argument("--min-duration", type=float, default=0.833)
    ap.add_argument("--max-duration", type=float, default=7.0)
    ap.add_argument("--max-cps", type=float, default=17.0)
    ap.add_argument("--reciter", default="")
    ap.add_argument("--quran-source", default="Quran Foundation", help="canonical text source for credits")
    ap.add_argument("--timing-source", default="", help="QF/QUL/alignment source for credits")
    ap.add_argument("--translation-edition", default="", help="translation resource ID or edition for credits")
    ap.add_argument("--translation-credit", default="")
    ap.add_argument("--background-credit", default="")
    ap.add_argument("--source-url", default="")
    ap.add_argument("--dry-run", action="store_true", help="validate and print report only; do not write outputs")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--selftest", action="store_true", help="run a synthetic non-Quran font/timing test")
    args = ap.parse_args(argv)

    try:
        if args.selftest:
            verses, verse_meta, timings, timing_meta, chapter, wanted = selftest_data()
            args.surah_name = args.surah_name if args.surah_name != "Surah" else "Font test"
            args.translation_credit = args.translation_credit or "Synthetic test text"
            args.reciter = args.reciter or "Synthetic"
            args.out = args.out or str(REPO_ROOT / ".cache" / "quran_subtitles_selftest.ass")
            args.preview = args.preview or str(REPO_ROOT / ".cache" / "quran_subtitles_selftest.png")
        else:
            if not args.verses or not args.timings or not args.range_spec or not args.out:
                hard_error("--verses, --timings, --range and --out are required (or use --selftest)")
            chapter, wanted = parse_range(args.range_spec)
            if args.chapter:
                chapter = args.chapter
            verses, verse_meta = load_verses(args.verses, chapter, args.translation_overrides)
            timings, timing_meta = load_timings(args.timings)

        original_first_start_ms = timings[wanted[0]]["start_ms"]
        cues = make_cues(
            verses,
            timings,
            wanted,
            args.offset_ms,
            args.auto_offset,
            args.english_cpl,
            args.arabic_cpl,
            args.arabic_lines,
            args.strict,
        )
        validate_cues(cues, args)
        layers = parse_layers(args.layers, args.strict)
        render_duration_s = args.video_duration if args.video_duration is not None else cues[-1]["end_ms"] / 1000.0 + 0.4
        if render_duration_s < cues[-1]["end_ms"] / 1000.0:
            hard_error("--video-duration is shorter than the last cue")

        if not args.font_dir:
            if args.preview:
                hard_error("--preview needs --font-dir or CLIP_DESK_QURAN_FONT_DIR")
            warn("no font dir set; ASS will rely on system fonts", False)
            font_dir = None
        else:
            font_dir = Path(args.font_dir).expanduser().resolve()
            check_font_dir(font_dir, args.strict)

        sizes = {
            "arabic": args.arabic_size,
            "english": args.english_size,
            "header": args.header_size,
            "ref": args.ref_size,
        }
        positions = {
            "header": args.header_y if args.header_y is not None else int(args.height * 0.44),
            "arabic": args.arabic_y if args.arabic_y is not None else int(args.height * 0.515),
            "english": args.english_y if args.english_y is not None else int(args.height * 0.578),
            "ref": args.ref_y if args.ref_y is not None else int(args.height * 0.645),
        }
        ass_text = build_ass(
            cues,
            args.width,
            args.height,
            args.arabic_font,
            args.english_font,
            args.surah_name,
            args.fade_ms,
            sizes,
            layers,
            positions,
        )

        print("Quran subtitles: %d cues, %s -> %s" % (len(cues), wanted[0], wanted[-1]))
        for c in cues:
            print(
                "  %-6s %7.2fs -> %7.2fs  %5.1f CPS  %s"
                % (c["verse_key"], c["start_ms"] / 1000.0, c["end_ms"] / 1000.0, c["cps"], c["arabic_source"])
            )
        if args.dry_run:
            print("DRY RUN: no files written")
            return 0

        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(ass_text, encoding="utf-8")
        print("ASS: %s" % out_path)

        if args.srt:
            srt_path = Path(args.srt).expanduser().resolve()
            srt_path.parent.mkdir(parents=True, exist_ok=True)
            srt_path.write_text(build_srt(cues), encoding="utf-8")
            print("SRT (review only): %s" % srt_path)
        if args.credits_out:
            cp = Path(args.credits_out).expanduser().resolve()
            write_credits(cp, args, verse_meta, timing_meta)
            print("Credits: %s" % cp)
        if args.preview or args.video_out:
            if not font_dir:
                hard_error("preview/MP4 rendering requires a font dir")
            ffmpeg = find_ffmpeg(args.ffmpeg)
        if args.preview:
            pt = args.preview_time if args.preview_time is not None else (cues[0]["start_ms"] + cues[0]["end_ms"]) / 2000.0
            make_preview(
                out_path,
                Path(args.preview).expanduser().resolve(),
                font_dir,
                args.width,
                args.height,
                render_duration_s,
                pt,
                args.background,
                args.dim,
                ffmpeg,
            )
            print("Preview: %s" % Path(args.preview).expanduser().resolve())
        if args.video_out:
            make_video(
                args,
                out_path,
                font_dir,
                render_duration_s,
                original_first_start_ms,
                ffmpeg,
            )
            print("MP4: %s" % Path(args.video_out).expanduser().resolve())
        if args.selftest:
            print("SELFTEST OK")
        return 0
    except QuranSubtitleError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        print("ERROR: ffmpeg failed with exit %s" % e.returncode, file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError) as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
