#!/usr/bin/env python3
"""Render an Arabic version of a clip whose captions are burned in.

The source edit already draws its captions as full-width coloured bars, so the
English is inside a plate — replacing it needs no inpainting. For each line in
the script we find where the English bar sits at that moment, draw an opaque
Arabic bar in the same place, and put the Arabic text on top (RTL handled by
libass). Captions that were over flat sky look identical to the original edit;
nothing is smudged.

usage:
  arabic_version.py SRC --script script.json --out out.mp4
  arabic_version.py SRC --script script.json --vo vo.wav --out out.mp4

script.json: [{"t0": 0.4, "t1": 4.2, "en": "...", "ar": "...", "cta": false}, ...]
`ar` is what gets burned; `en` is kept only so a reviewer can check the mapping.
"""

import argparse
import json
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import save_json, tool  # noqa: E402
from cut import rtl_font  # noqa: E402
from remove_captions import detect_frame  # noqa: E402

W, H = 1080, 1920
SRC_W = 720          # the clip this was built against; scale is derived from it
BAR_RGB = (16, 14, 26)
CTA_RGB = (196, 120, 12)

_FONT_FILES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def fit_size(text, base, max_px=None):
    """Largest size (<= base) at which `text` fits inside the bar.

    Arabic lines vary a lot in width; a fixed size either overflows the bar or
    looks tiny. Measure with the real font when one is available.
    """
    limit = max_px or (W - 90)
    try:
        from PIL import ImageFont
    except ImportError:
        ImageFont = None
    path = next((f for f in _FONT_FILES if os.path.isfile(f)), None)
    if ImageFont is None or path is None:
        est = len(text) * base * 0.52
        return base if est <= limit else max(30, int(base * limit / est))
    size = base
    while size > 30:
        f = ImageFont.truetype(path, size)
        w = f.getbbox(text)[2]
        if w <= limit:
            return size
        size -= 2
    return size


def grab(src, t):
    p = subprocess.run([tool("ffmpeg"), "-v", "error", "-ss", str(t), "-i", src,
                        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                       capture_output=True)
    return cv2.imdecode(np.frombuffer(p.stdout, np.uint8), cv2.IMREAD_COLOR)


def band_at(src, t):
    """Where the English caption sits at time t, in source pixels.

    Only the dominant text cluster: footage often has text in two places at
    once (caption + end-card), and a union of both would paint a huge bar over
    half the frame.
    """
    fr = grab(src, t)
    if fr is None:
        return None
    ls = detect_frame(fr)
    if not ls:
        return None
    ls = sorted(ls, key=lambda b: b[1] + b[3] / 2)
    clusters = [[ls[0]]]
    for b in ls[1:]:
        if abs((b[1] + b[3] / 2) - (clusters[-1][-1][1] + clusters[-1][-1][3] / 2)) <= 45:
            clusters[-1].append(b)
        else:
            clusters.append([b])
    best = max(clusters, key=len)
    y0 = min(y for x, y, w, h in best)
    y1 = max(y + h for x, y, w, h in best)
    if y1 - y0 > 170:                      # never a bar taller than a caption line
        mid = (y0 + y1) / 2
        y0, y1 = mid - 85, mid + 85
    return int(y0), int(y1)


def ts(sec):
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def ass_colour(rgb, alpha=0):
    r, g, b = rgb
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def build_ass(src, lines, font):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Bar,{font},20,&H00000000,&H00000000,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Ar,{font},62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,5,30,30,0,1
Style: ArCTA,{font},58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,5,30,30,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev, meta = [], []
    for ln in lines:
        mid = (ln["t0"] + ln["t1"]) / 2
        band = tuple(ln["y"]) if ln.get("y") else (band_at(src, mid) or (330, 460))
        pad = 16
        y0s, y1s = max(0, band[0] - pad), min(1280, band[1] + pad)
        y0, y1 = round(y0s * H / 1280), round(y1s * H / 1280)
        hbar = max(96, y1 - y0)
        colour = CTA_RGB if ln.get("cta") else BAR_RGB
        ev.append(f"Dialogue: 0,{ts(ln['t0'])},{ts(ln['t1'])},Bar,,0,0,0,,"
                  f"{{\\an7\\pos(0,{y0})\\p1\\c{ass_colour(colour)}}}"
                  f"m 0 0 l {W} 0 {W} {hbar} 0 {hbar}{{\\p0}}")
        st = "ArCTA" if ln.get("cta") else "Ar"
        size = fit_size(ln["ar"], 58 if ln.get("cta") else 62)
        ev.append(f"Dialogue: 1,{ts(ln['t0'])},{ts(ln['t1'])},{st},,0,0,0,,"
                  f"{{\\pos({W // 2},{y0 + hbar // 2})\\fs{size}}}{ln['ar']}")
        meta.append({"t0": ln["t0"], "t1": ln["t1"], "ar": ln["ar"],
                     "bar_y": [y0, y0 + hbar], "en": ln.get("en", "")})
    return head + "\n".join(ev) + "\n", meta


def main():
    ap = argparse.ArgumentParser(description="Burn an Arabic caption track over a clip.")
    ap.add_argument("src")
    ap.add_argument("--script", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--vo", help="Arabic voiceover wav/mp3 (mixed over the original)")
    ap.add_argument("--bed", type=float, default=0.12,
                    help="original audio level under the VO (default 0.12 = -18 dB)")
    ap.add_argument("--no-duck", action="store_true",
                    help="keep a flat bed instead of ducking it under the voice")
    ap.add_argument("--duck-bed", type=float, default=0.35,
                    help="bed level while the voice is speaking (ducked mode)")
    ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--preset", default="slow")
    ap.add_argument("--font", default=None)
    args = ap.parse_args()

    lines = json.load(open(args.script, encoding="utf-8"))
    font = args.font or rtl_font()
    src = os.path.abspath(args.src)
    out = os.path.abspath(args.out)

    ass, meta = build_ass(src, lines, font)
    work = os.path.join(os.path.dirname(out), "_ar.ass")
    with open(work, "w", encoding="utf-8") as fh:
        fh.write(ass)

    vf = f"scale={W}:{H}:flags=lanczos,setsar=1,ass={work}"

    cmd = [tool("ffmpeg"), "-y", "-v", "warning", "-i", src]
    if args.vo:
        cmd += ["-i", os.path.abspath(args.vo)]
    cmd += ["-vf", vf]
    if args.vo:
        # VO on top, original ducked under it (sidechain), both to -14 LUFS.
        # A flat bed either buries the speech or sounds dead; ducking keeps the
        # music/room alive between lines and drops it out of the way during them.
        if args.no_duck:
            mix = (f"[0:a]volume={args.bed}[bed];[1:a]volume=1.0[vo];"
                   f"[bed][vo]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,")
        else:
            mix = (f"[0:a]highpass=f=60,volume={args.duck_bed}[bed];"
                   f"[1:a]volume=1.0,asplit=2[vo][key];"
                   f"[bed][key]sidechaincompress=threshold=0.03:ratio=8:"
                   f"attack=6:release=280:makeup=1[ducked];"
                   f"[ducked][vo]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,")
        cmd += ["-filter_complex",
                mix + "loudnorm=I=-14:LRA=11:TP=-1.5[aout]",
                "-map", "0:v:0", "-map", "[aout]"]
    else:
        cmd += ["-map", "0:v:0", "-map", "0:a:0?", "-c:a", "copy"]
    cmd += ["-c:v", "libx264", "-crf", str(args.crf), "-preset", args.preset,
            "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if args.vo:
        cmd += ["-c:a", "aac", "-b:a", "192k"]
    cmd += [out]

    print(f"font: {font}  lines: {len(lines)}")
    print(" ".join(cmd)[:200] + " ...")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(f"ffmpeg failed ({r.returncode})")

    side = os.path.splitext(out)[0] + ".json"
    save_json(side, {
        "source": src, "output": out, "task": "arabic captions",
        "font": font, "vo": args.vo, "bed": args.bed if args.vo else None,
        "duck": (not args.no_duck) if args.vo else None,
        "duck_bed": args.duck_bed if args.vo else None,
        "size": [W, H], "crf": args.crf, "lines": meta,
    })
    print(f"done -> {out}\nsidecar -> {side}")


if __name__ == "__main__":
    main()
