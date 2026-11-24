# TEMPLATE — proven on slots 001-v2 and 002. Copy to jobs/<slot>/ and edit the
# SLOT constants listed in tools/quran_v2/README.md before running. Do not run in place.
# 005 revision: 876px popup, English 50, voice-first onset, first-frame punch, true-loop match-dissolve.
# 005 v2 (proven): English 58 / Ref 36 / Header 46, beat heartbeat, focus-pull entrances, inner vignette.
# 005 v3 (proven): Ref 66 / Header 70, ref_y 1548 (clearance above filament).

#!/usr/bin/env python3
"""Render Video 002: Surah Al-Baqarah 2:155-157 · Sheikh Ali Jaber (@quietly.cards).

Specifications implemented per user direction:
  * Surah Al-Baqarah 2:155-157 (~41.0 s total; 39.63 s unedited studio recitation by Sheikh Ali Jaber)
  * Unused Pinterest clip Candidate 011 (011_e1_AfqPShzEtwAnD7ThMX5sHbgIPsLcRUnHp5Gze2TSoZqKuuDXknyc-g.mp4)
  * ZERO color grading on background clip (100% raw natural clip colors preserved)
  * Widened popup card: 876x748 px (x=102..978 on 1080x1920, radius=76) so ~40 px of pure black
    margin + halo + rounded glass border remain visible on BOTH sides even after Instagram Reels
    crops ~62 px per side on tall 20:9 smartphones (verified with the 20:9 crop sim)
  * NO text hook line — pro iOS-physics "fake scroll" feed flick + directional motion blur +
    critically-damped spring settle (0.00 s -> 0.84 s); voice-first recitation enters ~0.40 s
    mid-settle with first-frame punch (zoom-breath, halo pulse, border flash, light sweep)
  * All middle micro-animations from 001 v2 preserved:
      - Voice-reactive warm ambient halo (driven by 30fps voice RMS envelope)
      - Top-lit glass rounded border with subtle voice shimmer
      - 28 floating warm-ivory atmospheric dust motes (fast pre-blurred 17x17 sprite)
      - Staggered lyric glide (Arabic QPC Hafs glides up, English Saheeh glides 100 ms later)
      - Dynamic ayah reference [2:155] / [2:156] / [2:157] + ultra-thin glowing progress filament
      - True seamless loop: final 0.55 s match-dissolves into frame 0 (no fade-to-black break)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FFMPEG = shutil.which("ffmpeg") or str(ROOT / ".venv" / "bin" / "ffmpeg")
FFPROBE = shutil.which("ffprobe") or str(ROOT / ".venv" / "bin" / "ffprobe")

SLOT = "002_al-baqarah_2-155-157_ali-jaber"
ASSETS_DIR = ROOT / "assets" / "quran" / SLOT
PIN_CLIP = ASSETS_DIR / "pinterest" / "011_e1_AfqPShzEtwAnD7ThMX5sHbgIPsLcRUnHp5Gze2TSoZqKuuDXknyc-g.mp4"
JOB_DIR = ROOT / "jobs" / SLOT
AUDIO_MASTER = JOB_DIR / "recitation_master.m4a"
ENV_NPY = JOB_DIR / "voice_env_30fps.npy"
FONT_DIR = ROOT / "clip-desk" / "skills" / "quran-subtitles" / "fonts"

VISUAL_BASE = JOB_DIR / "visual_base.mp4"
ASS_PATH = JOB_DIR / "captions.ass"
HEADER_ASS = JOB_DIR / "header_only.ass"
HEADER_PNG = JOB_DIR / "header_strip.png"

OUT_MP4 = ROOT / "outputs" / "quran-002_al-baqarah_2-155-157_ali-jaber_en_1080x1920_v1.mp4"
META_DIR = ROOT / "metadata" / SLOT

W, H = 1080, 1920
FPS = 30
DURATION_S = 41.00
TOTAL_FRAMES = int(round(DURATION_S * FPS))  # 1230

# Widened popup geometry (005): tall-phone 20:9 Reels crops ~62 px per side,
# leaving ~40 px black + full halo + full glass border visible post-crop.
# 1080 - 876 = 204 -> 102 px black margin on LEFT and 102 px on RIGHT!
POP_W = 876
POP_H = 748
POP_X = (W - POP_W) // 2  # 102
POP_Y = 342
POP_R = 76

SCROLL_END_S = 0.84
REC_START_S = 0.85
REC_END_S = 40.48
LOOP_MATCH_S = 0.55  # final 0.55 s match-dissolves into frame 0 (true Reel loop)

# Canonical QPC Hafs (api.quran.com text_qpc_hafs, words only, omitting ayah-end circle glyph)
# + Verbatim Saheeh International v1.1.2 (QuranEnc.com)
# Acoustically aligned to Sheikh Ali Jaber's breath & phonetic landmarks in recitation_raw.m4a:
BEATS = [
    {
        "id": 1,
        "ref": "2:155",
        "start": 0.84,
        "end": 6.08,
        "arabic": "وَلَنَبۡلُوَنَّكُم بِشَيۡءٖ مِّنَ ٱلۡخَوۡفِ وَٱلۡجُوعِ",
        "english": "And We will surely test you\\Nwith something of fear and hunger",
    },
    {
        "id": 2,
        "ref": "2:155",
        "start": 6.08,
        "end": 12.95,
        "arabic": "وَنَقۡصٖ مِّنَ ٱلۡأَمۡوَٰلِ\\Nوَٱلۡأَنفُسِ وَٱلثَّمَرَٰتِۗ",
        "english": "and a loss of wealth\\Nand lives and fruits,",
    },
    {
        "id": 3,
        "ref": "2:155",
        "start": 13.36,
        "end": 15.66,
        "arabic": "وَبَشِّرِ ٱلصَّٰبِرِينَ",
        "english": "but give good tidings to the patient,",
    },
    {
        "id": 4,
        "ref": "2:156",
        "start": 15.66,
        "end": 20.85,
        "arabic": "ٱلَّذِينَ إِذَآ أَصَٰبَتۡهُم مُّصِيبَةٞ قَالُوٓاْ",
        "english": "Who, when disaster strikes them, say,",
    },
    {
        "id": 5,
        "ref": "2:156",
        "start": 20.85,
        "end": 27.82,
        "arabic": "إِنَّا لِلَّهِ وَإِنَّآ إِلَيۡهِ رَٰجِعُونَ",
        "english": '"Indeed we belong to Allāh,\\Nand indeed to Him we will return."',
    },
    {
        "id": 6,
        "ref": "2:157",
        "start": 28.02,
        "end": 35.48,
        "arabic": "أُوْلَٰٓئِكَ عَلَيۡهِمۡ صَلَوَٰتٞ\\Nمِّن رَّبِّهِمۡ وَرَحۡمَةٞۖ",
        "english": "Those are the ones upon whom are\\Nblessings from their Lord and mercy.",
    },
    {
        "id": 7,
        "ref": "2:157",
        "start": 35.48,
        "end": 40.72,
        "arabic": "وَأُوْلَٰٓئِكَ هُمُ ٱلۡمُهۡتَدُونَ",
        "english": "And it is those who are\\Nthe [rightly] guided.",
    },
]

BEAT_STARTS = [b["start"] for b in BEATS]  # v2 heartbeat pulses


def ff_escape(p: Path) -> str:
    return str(p.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,")


def ass_time(sec: float) -> str:
    cs = max(0, int(round(sec * 100.0)))
    h = cs // 360000
    cs %= 360000
    m = cs // 6000
    cs %= 6000
    s = cs // 100
    c = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def rounded_mask(w: int, h: int, radius: int) -> np.ndarray:
    radius = max(1, min(int(radius), w // 2 - 1, h // 2 - 1))
    sc = 4
    W4, H4, R4 = w * sc, h * sc, radius * sc
    m = np.zeros((H4, W4), dtype=np.float32)
    cv2.rectangle(m, (R4, 0), (W4 - R4, H4), 1.0, -1)
    cv2.rectangle(m, (0, R4), (W4, H4 - R4), 1.0, -1)
    cv2.circle(m, (R4, R4), R4, 1.0, -1)
    cv2.circle(m, (W4 - R4, R4), R4, 1.0, -1)
    cv2.circle(m, (R4, H4 - R4), R4, 1.0, -1)
    cv2.circle(m, (W4 - R4, H4 - R4), R4, 1.0, -1)
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA)


def top_lit_border_mask(outer: np.ndarray, border_px: int, radius: int) -> np.ndarray:
    h, w = outer.shape
    b = max(1, int(border_px))
    inner = rounded_mask(w - 2 * b, h - 2 * b, max(1, radius - b))
    full_inner = np.zeros_like(outer)
    full_inner[b : h - b, b : w - b] = inner
    rim = np.clip(outer - full_inner, 0.0, 1.0)
    # Top-lit specular falloff: bright warm ivory along top curve, subtle along bottom
    y_grad = np.linspace(1.0, 0.30, h, dtype=np.float32)[:, None]
    return rim * y_grad


def scroll_offset_px(t: float) -> float:
    """Pro iOS UIScrollView inertial flick + critically-damped spring lock (0.00 -> 0.84 s).

    At t=0.00s: offset = +1340 px (previous card sits in upper-mid viewport, active card peeks in below).
    Accelerates rapidly upward through 0.05..0.42s, crosses 0 around 0.56s, gently overshoots
    to -15 px at t=0.65s, and settles smoothly to 0.0 px at t=0.84s.
    """
    if t >= SCROLL_END_S:
        return 0.0
    u = max(0.0, min(1.0, t / SCROLL_END_S))
    # Smooth C2 spring curve: starts at +1340, fast flick, micro-overshoot -15 px, settles to 0
    decay = (1.0 - u) ** 2.35
    osc = math.cos(u * math.pi * 1.42)
    raw = 1340.0 * decay * osc
    # Ease the very first 2 frames slightly so velocity ramps like a real thumb release
    return raw


def render_header_sprite() -> np.ndarray:
    """Render 'Surah Al-Baqarah' header via libass onto black so it scrolls & blurs with the card."""
    HEADER_ASS.write_text(
        "\n".join(
            [
                "[Script Info]",
                "ScriptType: v4.00+",
                f"PlayResX: {W}",
                f"PlayResY: 120",
                "WrapStyle: 2",
                "ScaledBorderAndShadow: yes",
                "",
                "[V4+ Styles]",
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
                "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                "Alignment, MarginL, MarginR, MarginV, Encoding",
                "Style: Header,Cormorant Garamond Light,70,&H28D2DCE4,&H000000FF,&H00000000,&H00000000,"
                "0,0,0,0,100,100,0.6,0,1,0,0,5,40,40,10,1",
                "",
                "[Events]",
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
                "Dialogue: 0,0:00:00.00,0:00:02.00,Header,,0,0,0,,Surah Al-Baqarah",
                "",
            ]
        ),
        encoding="utf-8",
    )
    ass_f = f"ass=filename={ff_escape(HEADER_ASS)}:fontsdir={ff_escape(FONT_DIR)}:shaping=1"
    subprocess.run(
        [
            FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s={W}x120:d=0.2:r=30",
            "-vf", ass_f,
            "-frames:v", "1", "-update", "1", str(HEADER_PNG),
        ],
        check=True,
    )
    img = cv2.imread(str(HEADER_PNG), cv2.IMREAD_COLOR)
    return img  # (120, 1080, 3) on pure black -> additive/screen blend!


def write_captions_ass() -> None:
    """Write libass subtitle file with staggered upward glide + fade for all 7 beats."""
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {W}",
        f"PlayResY: {H}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        # PrimaryColour in ASS is &HAABBGGRR:
        # Arabic: warm luminous cream #F2EDE2 -> &H00E2EDF2
        "Style: Arabic,KFGQPC HAFS Uthmanic Script,60,&H00E2EDF2,&H000000FF,&H88080808,&H90000000,"
        "0,0,0,0,100,100,0,0,1,1.2,2.0,5,155,155,20,1",
        # English: warm muted parchment #DDD7CB -> &H00CBD7DD
        "Style: English,Cormorant Garamond Light,58,&H00D8D2C6,&H000000FF,&H88080808,&H80000000,"
        "0,0,0,0,100,100,0.2,0,1,0.9,1.5,5,165,165,20,1",
        # Ref: subtle warm stone #9E988E -> &H328E989E
        "Style: Ref,Cormorant Garamond Light,66,&H20A79E94,&H000000FF,&H00000000,&H00000000,"
        "0,0,0,0,100,100,1.0,0,1,0,0,5,180,180,20,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for b in BEATS:
        t0 = b["start"]
        t1 = b["end"]
        # Adjust vertical centers gently if Arabic has 2 lines vs 1 line
        has_2_ar = "\\N" in b["arabic"]
        ar_y = 1236 if has_2_ar else 1248
        en_y = 1422 if has_2_ar else 1408
        ref_y = 1548  # v3: Ref 66 needs clearance above the 1612 filament

        # Arabic enters at t0, glides up 15 px over 340 ms
        ar_tag = f"{{\\an5\\move(540,{ar_y + 15},540,{ar_y},0,340)\\fad(250,220)\\blur6\\t(0,300,\\blur0)\\fscx96\\fscy96\\t(0,340,\\fscx100\\fscy100)}}"
        lines.append(
            f"Dialogue: 2,{ass_time(t0)},{ass_time(t1)},Arabic,,0,0,0,,{ar_tag}{b['arabic']}"
        )

        # English enters +100 ms staggered, glides up 14 px over 360 ms
        en_t0 = min(t1 - 0.3, t0 + 0.10)
        en_tag = f"{{\\an5\\move(540,{en_y + 14},540,{en_y},0,360)\\fad(270,220)\\blur6\\t(0,360,\\blur0)\\fscx96\\fscy96\\t(0,360,\\fscx100\\fscy100)}}"
        lines.append(
            f"Dialogue: 2,{ass_time(en_t0)},{ass_time(t1)},English,,0,0,0,,{en_tag}{b['english']}"
        )

    # Continuous ayah reference pills grouped per ayah so [2:155] doesn't flicker between sub-beats!
    ayah_spans = [
        ("2:155", 0.84, 15.66),
        ("2:156", 15.66, 27.92),
        ("2:157", 28.02, 40.72),
    ]
    for ref, rs, re_t in ayah_spans:
        r_tag = "{\\an5\\pos(540,1548)\\fad(260,220)}"
        lines.append(
            f"Dialogue: 1,{ass_time(rs)},{ass_time(re_t)},Ref,,0,0,0,,{r_tag}[{ref}]"
        )

    ASS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_source_frames(path: Path) -> np.ndarray:
    """Decode all frames of Pinterest Candidate 011 (720x1280, ~978 frames) into RAM for fast interpolation."""
    cap = cv2.VideoCapture(str(path))
    frames = []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(fr)
    cap.release()
    if not frames:
        raise RuntimeError(f"No frames decoded from {path}")
    return np.stack(frames, axis=0)  # (N, 1280, 720, 3) uint8 — ~2.6 GB, fits easily in RAM? Wait: check RAM!


def get_cropped_ungraded_frame(cap_frames: list[np.ndarray], src_idx_float: float, zoom: float) -> np.ndarray:
    """Sample raw ungraded BGR frame at sub-frame index with gentle Ken Burns drift into POP_W x POP_H."""
    n = len(cap_frames)
    i0 = max(0, min(n - 1, int(math.floor(src_idx_float))))
    i1 = max(0, min(n - 1, i0 + 1))
    frac = src_idx_float - i0

    if frac < 1e-3 or i0 == i1:
        fr = cap_frames[i0]
    else:
        fr = cv2.addWeighted(cap_frames[i0], 1.0 - frac, cap_frames[i1], frac, 0.0)

    sh, sw = fr.shape[:2]  # 1280, 720
    # Aspect-fill crop box inside 720x1280 for POP_W:POP_H (816:748), zoomed by `zoom`
    target_aspect = POP_W / float(POP_H)  # 1.0909
    crop_w = sw / zoom
    crop_h = crop_w / target_aspect
    if crop_h > sh:
        crop_h = sh / zoom
        crop_w = crop_h * target_aspect

    # Center horizontally, frame golden-ratio alpine chalets + emerald water vertically (center_y ~ 51% of height)
    cx = sw * 0.50
    cy = sh * 0.515
    x0 = max(0.0, min(sw - crop_w, cx - crop_w * 0.5))
    y0 = max(0.0, min(sh - crop_h, cy - crop_h * 0.5))

    ix0, iy0 = int(round(x0)), int(round(y0))
    ix1, iy1 = min(sw, int(round(x0 + crop_w))), min(sh, int(round(y0 + crop_h)))
    sub = fr[iy0:iy1, ix0:ix1]
    # Pure Lanczos resize — ZERO color grading!
    return cv2.resize(sub, (POP_W, POP_H), interpolation=cv2.INTER_LANCZOS4)


def make_mote_sprite(size: int = 17) -> np.ndarray:
    """Pre-blurred 17x17 radial warm-ivory dust mote sprite (float32 [0..1])."""
    c = size // 2
    y, x = np.ogrid[:size, :size]
    r2 = ((x - c) ** 2 + (y - c) ** 2) / float(max(1, c * c))
    sp = np.exp(-r2 * 3.4).astype(np.float32)
    sp[r2 > 1.0] = 0.0
    return sp


def build_outgoing_ghost_card(sample_popup_bgr: np.ndarray, card_mask_u8: np.ndarray, border_f: np.ndarray, header_bgr: np.ndarray) -> np.ndarray:
    """Build a realistic dark-feed 'previous reel' canvas (1080x1920) that scrolls off the top at t=0..0.42s.

    Uses a softly blurred frame from the scenic clip + softly blurred abstract editorial lines
    (never unread Quranic text) so the vertical flick looks 100% like scrolling past a previous card!
    """
    ghost = np.zeros((H, W, 3), dtype=np.uint8)
    blurred_scene = cv2.GaussianBlur(sample_popup_bgr, (25, 25), 7.0)
    # Slightly dim outgoing card so incoming card commands focus
    blurred_scene = (blurred_scene.astype(np.float32) * 0.78).astype(np.uint8)

    roi = ghost[POP_Y : POP_Y + POP_H, POP_X : POP_X + POP_W]
    m_f = (card_mask_u8.astype(np.float32) / 255.0)[:, :, None]
    b_col = np.array([212.0, 224.0, 232.0], dtype=np.float32)[None, None, :]
    comp = blurred_scene.astype(np.float32) * m_f + b_col * (border_f[:, :, None] * 0.24)
    ghost[POP_Y : POP_Y + POP_H, POP_X : POP_X + POP_W] = np.clip(comp, 0, 255).astype(np.uint8)

    # Header above outgoing card (softly blurred)
    hy = POP_Y - 96
    ghost[hy : hy + 120, :] = np.maximum(ghost[hy : hy + 120, :], cv2.GaussianBlur(header_bgr, (9, 9), 2.5))

    # Soft out-of-focus editorial shimmer bars where previous card's caption sat (zero text)
    bars = np.zeros((H, W, 3), dtype=np.uint8)
    cv2.line(bars, (390, 1245), (690, 1245), (175, 184, 192), 10, cv2.LINE_AA)
    cv2.line(bars, (340, 1410), (740, 1410), (130, 138, 146), 7, cv2.LINE_AA)
    cv2.line(bars, (415, 1462), (665, 1462), (120, 128, 136), 7, cv2.LINE_AA)
    bars = cv2.GaussianBlur(bars, (35, 35), 11.0)
    ghost = np.clip(ghost.astype(np.int16) + (bars.astype(np.int16) * 4 // 10), 0, 255).astype(np.uint8)
    return ghost


def blit_vertical_shift(dst: np.ndarray, src: np.ndarray, dy: int) -> None:
    """Blit full-width src (H, W, 3) onto dst shifted vertically by `dy` pixels."""
    if dy <= -H or dy >= H:
        return
    if dy >= 0:
        h_copy = H - dy
        dst[dy:H, :] = np.maximum(dst[dy:H, :], src[0:h_copy, :])
    else:
        h_copy = H + dy
        dst[0:h_copy, :] = np.maximum(dst[0:h_copy, :], src[-dy:H, :])


def render_visual_base(only_frames: list[int] | None = None) -> dict[int, np.ndarray]:
    """Render visual_base.mp4 (or return sampled frames when `only_frames` is given for fast QA)."""
    t_start = time.time()
    voice_env = np.load(ENV_NPY)
    header_bgr = render_header_sprite()
    # Frame-0 reference for the true-loop match-dissolve (full renders only; ~1 s pre-pass)
    loop_target = render_visual_base(only_frames=[0])[0] if only_frames is None else None

    # Decode source frames into list of compact 720x1280 BGR arrays (~978 frames * 2.7MB = ~2.6GB,
    # or resize to 880x1564? Even smaller: 720x1280 is ONLY 720*1280*3 = 2.76 MB * 978 = 2.7 GB.
    # Let's check RAM or stream sequentially!Wait: src_idx_float is strictly monotonic except ghost card!
    # Streaming sequentially with a 2-frame ring buffer uses ONLY 6 MB of RAM AND is even faster!!)
    cap = cv2.VideoCapture(str(PIN_CLIP))
    src_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 978

    # Grab one frame near 75% for the outgoing ghost card in the 0.00..0.42s fake scroll
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(src_count * 0.75))
    ok_g, ghost_raw = cap.read()
    if not ok_g:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        _, ghost_raw = cap.read()
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    # Precompute rounded mask, top-lit border, and voice-breathing halo once!
    card_mask = rounded_mask(POP_W, POP_H, POP_R)  # float32 [0..1]
    card_mask_u8 = np.clip(card_mask * 255.0, 0, 255).astype(np.uint8)
    inv_mask_3 = (1.0 - card_mask)[:, :, None]
    mask_3 = card_mask[:, :, None]
    # v2: subtle inner vignette for premium card depth (1.00 center -> 0.90 corners)
    _vy, _vx = np.mgrid[0:POP_H, 0:POP_W].astype(np.float32)
    _vr = np.sqrt(((_vx / POP_W - 0.5) * 2.0) ** 2 + ((_vy / POP_H - 0.5) * 2.0) ** 2) / np.sqrt(2.0)
    vignette_3 = (1.0 - 0.10 * np.clip(_vr, 0.0, 1.0) ** 1.6)[:, :, None].astype(np.float32)

    border_f = top_lit_border_mask(card_mask, border_px=2, radius=POP_R)  # float32
    border_col = np.array([214.0, 226.0, 236.0], dtype=np.float32)[None, None, :]  # warm champagne ivory BGR

    # Precompute soft halo in a padded ROI around the popup card (pad = 96 px on each side)
    PAD = 96
    halo_h, halo_w = POP_H + 2 * PAD, POP_W + 2 * PAD
    halo_seed = np.zeros((halo_h, halo_w), dtype=np.float32)
    halo_seed[PAD : PAD + POP_H, PAD : PAD + POP_W] = card_mask
    halo_blur = cv2.GaussianBlur(halo_seed, (0, 0), sigmaX=34.0, sigmaY=34.0)
    # Zero out inside the opaque card interior so we only blend the exterior glow ring!
    halo_ring = halo_blur.copy()
    halo_ring[PAD : PAD + POP_H, PAD : PAD + POP_W] *= (1.0 - card_mask)
    # Pre-multiply halo BGR unit sprite so per-frame halo is just `(halo_unit * strength).astype(uint8)`!
    halo_bgr_unit = halo_ring[:, :, None] * np.array([192.0, 208.0, 224.0], dtype=np.float32)[None, None, :]
    hx0, hy0 = POP_X - PAD, POP_Y - PAD
    hx1, hy1 = hx0 + halo_w, hy0 + halo_h

    # Outgoing ghost card for fake-scroll opener
    ghost_sample_crop = get_cropped_ungraded_frame([ghost_raw], 0.0, 1.02)
    ghost_sample_crop = (ghost_sample_crop.astype(np.float32) * vignette_3).astype(np.uint8)
    ghost_canvas = build_outgoing_ghost_card(ghost_sample_crop, card_mask_u8, border_f, header_bgr)

    # Deterministic floating motes (28 warm-ivory micro-particles)
    rng = np.random.default_rng(2026002)
    n_motes = 28
    mote_x0 = rng.uniform(48, W - 48, n_motes)
    mote_y0 = rng.uniform(80, H - 120, n_motes)
    mote_vy = rng.uniform(14.0, 31.0, n_motes)
    mote_amp = rng.uniform(8.0, 24.0, n_motes)
    mote_freq = rng.uniform(0.18, 0.45, n_motes)
    mote_phase = rng.uniform(0.0, 2.0 * math.pi, n_motes)
    mote_alpha = rng.uniform(0.10, 0.26, n_motes)
    mote_sp = make_mote_sprite(17)
    mote_col = np.array([200.0, 214.0, 226.0], dtype=np.float32)
    # 12 tiny far-layer motes for depth (9 px sprite, dimmer, slower)
    n_far = 12
    far_x0 = rng.uniform(48, W - 48, n_far)
    far_y0 = rng.uniform(80, H - 120, n_far)
    far_vy = rng.uniform(6.0, 14.0, n_far)
    far_amp = rng.uniform(4.0, 12.0, n_far)
    far_freq = rng.uniform(0.10, 0.25, n_far)
    far_phase = rng.uniform(0.0, 2.0 * math.pi, n_far)
    far_alpha = rng.uniform(0.05, 0.12, n_far)
    far_sp = make_mote_sprite(9)
    # Animated OLED grain: 4 cycling full-frame +-1 LSB tiles kill banding in the black surround
    grain_rng = np.random.default_rng(2026005)
    grain_tiles = [grain_rng.integers(-1, 2, size=(H, W, 1)).astype(np.int16) for _ in range(4)]

    sampled_out: dict[int, np.ndarray] = {}
    proc = None
    if only_frames is None:
        VISUAL_BASE.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen(
            [
                FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                "-i", "pipe:0",
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                str(VISUAL_BASE),
            ],
            stdin=subprocess.PIPE,
        )

    # Ring buffer for sequential decoding
    cur_src_i = -1
    buf_f0 = ghost_raw
    buf_f1 = ghost_raw

    def read_up_to(target_i: int) -> tuple[np.ndarray, np.ndarray]:
        nonlocal cur_src_i, buf_f0, buf_f1
        if only_frames is not None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, target_i))
            ok0, f0 = cap.read()
            ok1, f1 = cap.read()
            return (f0 if ok0 else buf_f0), (f1 if ok1 else (f0 if ok0 else buf_f0))
        while cur_src_i < target_i:
            ok, nxt = cap.read()
            if not ok:
                nxt = buf_f1
            buf_f0 = buf_f1
            buf_f1 = nxt
            cur_src_i += 1
        # Need target_i and target_i + 1: ensure one step ahead
        return buf_f0, buf_f1

    # Pre-prime frame 0 and 1 for streaming mode
    if only_frames is None:
        ok0, buf_f0 = cap.read()
        ok1, buf_f1 = cap.read()
        if not ok1:
            buf_f1 = buf_f0
        cur_src_i = 0

    frame_indices = sorted(only_frames) if only_frames is not None else range(TOTAL_FRAMES)

    for f_idx in frame_indices:
        t = f_idx / float(FPS)
        u_full = f_idx / float(max(1, TOTAL_FRAMES - 1))

        # Map [0 .. TOTAL_FRAMES-1] smoothly across [0 .. src_count - 2]
        src_pos = u_full * max(1, src_count - 2)
        i0 = int(math.floor(src_pos))
        frac = src_pos - i0

        if only_frames is not None:
            fr0, fr1 = read_up_to(i0)
        else:
            while cur_src_i < i0:
                ok_n, nxt = cap.read()
                if not ok_n:
                    nxt = buf_f1
                buf_f0 = buf_f1
                buf_f1 = nxt
                cur_src_i += 1
            fr0, fr1 = buf_f0, buf_f1

        # v2: beat-switch heartbeat — micro zoom/border/halo pulse at each caption start
        beat_pulse = 0.0
        for _bs in BEAT_STARTS:
            _dt = t - _bs
            if 0.0 <= _dt < 2.0:
                beat_pulse += math.exp(-_dt / 0.28)
        # Gentle continuous Ken Burns scale 1.000 -> 1.045 (no color grade!) + first-frame zoom-breath
        zoom = 1.000 + 0.045 * u_full + 0.065 * math.exp(-t / 0.30) + 0.012 * beat_pulse
        popup_bgr = get_cropped_ungraded_frame([fr0, fr1], frac, zoom)

        # Voice envelope at this frame
        v_env = float(voice_env[min(f_idx, len(voice_env) - 1)])

        # Build active card canvas
        canvas = np.zeros((H, W, 3), dtype=np.uint8)

        # 1. Atmospheric dust motes (drawn behind halo/card so they float in the black surround)
        for m in range(n_motes):
            mx = int(round(mote_x0[m] + mote_amp[m] * math.sin(2.0 * math.pi * mote_freq[m] * t + mote_phase[m])))
            my = int(round((mote_y0[m] - mote_vy[m] * t) % (H - 80) + 40))
            if 9 <= mx < W - 9 and 9 <= my < H - 9:
                # Pulse subtly with recitation
                ma = mote_alpha[m] * (0.75 + 0.45 * v_env)
                patch = (mote_sp[:, :, None] * (mote_col[None, None, :] * ma)).astype(np.uint8)
                roi_m = canvas[my - 8 : my + 9, mx - 8 : mx + 9]
                canvas[my - 8 : my + 9, mx - 8 : mx + 9] = np.maximum(roi_m, patch)
        for m in range(n_far):
            fx = int(round(far_x0[m] + far_amp[m] * math.sin(2.0 * math.pi * far_freq[m] * t + far_phase[m])))
            fy = int(round((far_y0[m] - far_vy[m] * t) % (H - 80) + 40))
            if 5 <= fx < W - 5 and 5 <= fy < H - 5:
                fa = far_alpha[m] * (0.75 + 0.45 * v_env)
                fpatch = (far_sp[:, :, None] * (mote_col[None, None, :] * fa)).astype(np.uint8)
                roi_f = canvas[fy - 4 : fy + 5, fx - 4 : fx + 5]
                canvas[fy - 4 : fy + 5, fx - 4 : fx + 5] = np.maximum(roi_f, fpatch)

        # 2. Voice-reactive warm ambient halo around narrowed popup card
        halo_strength = 0.055 + 0.068 * v_env + 0.10 * math.exp(-t / 0.25) + 0.03 * beat_pulse
        halo_patch = np.clip(halo_bgr_unit * halo_strength, 0, 255).astype(np.uint8)
        canvas[hy0:hy1, hx0:hx1] = np.clip(
            canvas[hy0:hy1, hx0:hx1].astype(np.uint16) + halo_patch.astype(np.uint16), 0, 255
        ).astype(np.uint8)

        # 3. Rounded ungraded video popup + top-lit glass border
        roi_c = canvas[POP_Y : POP_Y + POP_H, POP_X : POP_X + POP_W].astype(np.float32)
        rim_gain = 0.31 + 0.07 * v_env + 0.32 * math.exp(-t / 0.20) + 0.15 * beat_pulse
        comp_card = (
            roi_c * inv_mask_3
            + popup_bgr.astype(np.float32) * mask_3 * vignette_3
            + border_col * (border_f[:, :, None] * rim_gain)
        )
        canvas[POP_Y : POP_Y + POP_H, POP_X : POP_X + POP_W] = np.clip(comp_card, 0, 255).astype(np.uint8)

        # 3b. First-frame light sweep: specular band glides L->R across the card (0..0.7 s)
        if t < 0.70:
            sweep_u = t / 0.70
            sweep_xc = -220.0 + (POP_W + 440.0) * sweep_u
            sweep_xx = np.arange(POP_W, dtype=np.float32)[None, :]
            sweep_band = np.exp(-((sweep_xx - sweep_xc) ** 2) / (2.0 * 120.0 ** 2))
            sweep_fade = math.sin(min(1.0, sweep_u) * math.pi)
            sweep_add = (sweep_band * mask_3[:, :, 0] * (60.0 * sweep_fade)).astype(np.float32)
            roi_s = canvas[POP_Y : POP_Y + POP_H, POP_X : POP_X + POP_W].astype(np.float32)
            roi_s += sweep_add[:, :, None] * np.array([0.92, 0.97, 1.0], dtype=np.float32)[None, None, :]
            canvas[POP_Y : POP_Y + POP_H, POP_X : POP_X + POP_W] = np.clip(roi_s, 0, 255).astype(np.uint8)

        # 4. Header ('Surah Al-Baqarah') locked above popup card (y_center ~ 286 -> top = 226)
        hy_hdr = POP_Y - 116
        canvas[hy_hdr : hy_hdr + 120, :] = np.maximum(canvas[hy_hdr : hy_hdr + 120, :], header_bgr)

        # 5. Ultra-thin recitation progress filament (follows the voice-first recitation start)
        if t >= REC_START_S:
            prog = max(0.0, min(1.0, (t - REC_START_S) / (REC_END_S - REC_START_S)))
            fade_in_p = min(1.0, (t - REC_START_S) / 0.35)
            bar_w = 168
            bx0 = (W - bar_w) // 2
            by0 = 1612
            # Subtle base track
            track_c = int(round(44 * fade_in_p))
            cv2.line(canvas, (bx0, by0), (bx0 + bar_w, by0), (track_c, track_c + 3, track_c + 6), 2, cv2.LINE_AA)
            fill_px = int(round(bar_w * prog))
            if fill_px > 0:
                fc_b = int(round(188 * fade_in_p))
                fc_g = int(round(202 * fade_in_p))
                fc_r = int(round(214 * fade_in_p))
                cv2.line(canvas, (bx0, by0), (bx0 + fill_px, by0), (fc_b // 3, fc_g // 3, fc_r // 3), 6, cv2.LINE_AA)
                cv2.line(canvas, (bx0, by0), (bx0 + fill_px, by0), (fc_b, fc_g, fc_r), 2, cv2.LINE_AA)
                # Soft luminous tip
                tx = bx0 + fill_px
                if 8 <= tx < W - 8:
                    tip = (mote_sp[:, :, None] * (mote_col[None, None, :] * (0.50 * fade_in_p))).astype(np.uint8)
                    canvas[by0 - 8 : by0 + 9, tx - 8 : tx + 9] = np.maximum(
                        canvas[by0 - 8 : by0 + 9, tx - 8 : tx + 9], tip
                    )

        # 6. PRO FAKE-SCROLL FEED OPENER (0.00 s -> 0.84 s)
        if t < SCROLL_END_S:
            dy = int(round(scroll_offset_px(t)))
            dy_prev = scroll_offset_px(max(0.0, t - 1.0 / FPS))
            dy_next = scroll_offset_px(min(SCROLL_END_S, t + 1.0 / FPS))
            vel_px = abs(dy_next - dy_prev) * 0.5

            feed_frame = np.zeros((H, W, 3), dtype=np.uint8)
            # Outgoing previous card sits 1560 px above active card
            dy_ghost = dy - 1560
            blit_vertical_shift(feed_frame, ghost_canvas, dy_ghost)
            blit_vertical_shift(feed_frame, canvas, dy)

            # Directional vertical shutter motion blur proportional to scroll velocity
            kh = max(1, min(45, int(round(vel_px * 0.34))))
            if kh % 2 == 0:
                kh += 1
            if kh >= 3:
                feed_frame = cv2.blur(feed_frame, (1, kh))
            canvas = feed_frame

        # 7. True seamless loop: match-dissolve into frame 0 over the final LOOP_MATCH_S
        if loop_target is not None and t > DURATION_S - LOOP_MATCH_S:
            lk = (t - (DURATION_S - LOOP_MATCH_S)) / LOOP_MATCH_S
            lk = lk * lk * (3.0 - 2.0 * lk)
            canvas = (canvas.astype(np.float32) * (1.0 - lk) + loop_target.astype(np.float32) * lk).astype(np.uint8)

        canvas = np.clip(canvas.astype(np.int16) + grain_tiles[f_idx % 4], 0, 255).astype(np.uint8)

        if only_frames is not None:
            sampled_out[f_idx] = canvas
        else:
            assert proc is not None and proc.stdin is not None
            proc.stdin.write(canvas.tobytes())
            if f_idx % 300 == 0:
                print(f"[slot-002] rendered frame {f_idx}/{TOTAL_FRAMES} ({time.time() - t_start:.1f}s)", flush=True)

    cap.release()
    if proc is not None:
        assert proc.stdin is not None
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"ffmpeg visual_base failed with exit code {rc}")
        print(f"[slot-002] visual_base complete in {time.time() - t_start:.1f}s -> {VISUAL_BASE}", flush=True)
    return sampled_out


def mux_final_video() -> None:
    """Burn libass QPC Hafs + English captions onto visual_base.mp4 and mux Haram master audio."""
    OUT_MP4.parent.mkdir(parents=True, exist_ok=True)
    ass_f = f"ass=filename={ff_escape(ASS_PATH)}:fontsdir={ff_escape(FONT_DIR)}:shaping=1"
    # No output fade: visual_base already match-dissolves into frame 0 (true seamless loop)
    vf = ass_f
    subprocess.run(
        [
            FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(VISUAL_BASE),
            "-i", str(AUDIO_MASTER),
            "-vf", vf,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            "-movflags", "+faststart",
            "-shortest",
            str(OUT_MP4),
        ],
        check=True,
    )
    print(f"[slot-002] final MP4 written: {OUT_MP4} ({OUT_MP4.stat().st_size} bytes)", flush=True)


def run_test_preview() -> None:
    """Fast (<4s) pre-flight visual QA of fake-scroll frames + all 7 caption beats + Reels 20:9 crop!"""
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    write_captions_ass()

    # Sample fake-scroll frames (t=0.07s, 0.23s, 0.43s, 0.65s overshoot, 0.84s lock) + midpoints of all 7 beats
    scroll_frames = [2, 7, 13, 19, 25]
    beat_frames = [int(round(((b["start"] + b["end"]) * 0.5) * FPS)) for b in BEATS]
    samples = render_visual_base(only_frames=scroll_frames + beat_frames)

    # Save 5-panel fake-scroll motion strip
    strip_tiles = [cv2.resize(samples[f], (270, 480), interpolation=cv2.INTER_AREA) for f in scroll_frames]
    cv2.imwrite(str(JOB_DIR / "preview_scroll_strip.png"), np.hstack(strip_tiles))

    # Burn exact ASS onto each beat midpoint frame to verify Arabic QPC Hafs + English + Reels 20:9 margins!
    beat_panels = []
    ass_f = f"ass=filename={ff_escape(ASS_PATH)}:fontsdir={ff_escape(FONT_DIR)}:shaping=1"
    for b, f_idx in zip(BEATS, beat_frames):
        t_mid = f_idx / float(FPS)
        raw_png = JOB_DIR / f"tmp_beat_{b['id']}_raw.png"
        sub_png = JOB_DIR / f"tmp_beat_{b['id']}_sub.png"
        cv2.imwrite(str(raw_png), samples[f_idx])
        subprocess.run(
            [
                FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
                "-loop", "1", "-framerate", "30", "-i", str(raw_png),
                "-ss", f"{t_mid:.3f}", "-t", "0.1",
                "-vf", f"setpts=PTS+{t_mid:.3f}/TB,{ass_f}",
                "-frames:v", "1", "-update", "1", str(sub_png),
            ],
            check=True,
        )
        rendered = cv2.imread(str(sub_png))
        # Also draw subtle guide ticks on a Reels-crop check panel for the final beat!
        if b["id"] == BEATS[-1]["id"]:
            # Simulate tall 20:9 phone horizontal crop (~62 px cropped off left and right -> 956x1920)
            reels_sim = rendered[:, 62 : W - 62].copy()
            cv2.imwrite(str(JOB_DIR / "preview_reels_20x9_crop.png"), reels_sim)
        beat_panels.append(cv2.resize(rendered, (360, 640), interpolation=cv2.INTER_AREA))

    # Assemble 4x2 grid of the 7 beats (+ Reels 20:9 tall-phone crop simulation in slot 8!)
    reels_panel = cv2.imread(str(JOB_DIR / "preview_reels_20x9_crop.png"))
    reels_panel_resized = cv2.resize(reels_panel, (320, 640), interpolation=cv2.INTER_AREA)
    pad_slot8 = np.zeros((640, 360, 3), dtype=np.uint8)
    pad_slot8[:, 20:340] = reels_panel_resized
    cv2.putText(pad_slot8, "20:9 REELS CROP SIM", (58, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 220, 180), 2, cv2.LINE_AA)
    beat_panels.append(pad_slot8)

    while len(beat_panels) % 4:
        beat_panels.append(np.zeros((640, 360, 3), dtype=np.uint8))
    rows = [np.hstack(beat_panels[i : i + 4]) for i in range(0, len(beat_panels), 4)]
    cv2.imwrite(str(JOB_DIR / "preview_beats_grid.png"), np.vstack(rows))
    print("[slot-002] wrote preview_scroll_strip.png and preview_beats_grid.png", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-preview", action="store_true")
    args = ap.parse_args()

    JOB_DIR.mkdir(parents=True, exist_ok=True)
    write_captions_ass()
    if args.test_preview:
        run_test_preview()
        return

    render_visual_base(only_frames=None)
    mux_final_video()


if __name__ == "__main__":
    main()
