#!/usr/bin/env python3
"""Render a black 9:16 verse-card base with a rounded, animated video popup.

This is the visual half of ``quran-subtitles``. It does not draw Quran text,
translations, credits or any burned-in credit. ``quran_subtitles.py`` adds the
canonical ASS captions and the recitation audio on top.

Example:
  python clip-desk/scripts/quran_visual.py \
    --background assets/quran-19-30-33/background.mp4 \
    --out jobs/quran-19-30-33/visual_base.mp4 \
    --duration 43.4 --intro 0.8 --popup-top 380 --popup-width 1000 \
    --popup-height 860 --radius 90
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
OFF_WHITE_BGR = (232.0, 227.0, 218.0)  # BGR, muted warm white
SHADOW_BGR = (20.0, 21.0, 26.0)        # BGR, blue-black
GLOW_BGR = (210.0, 205.0, 198.0)       # BGR, very soft halo


class VisualError(Exception):
    pass


def find_ffmpeg(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    env_ffmpeg = os.environ.get("CLIP_DESK_FFMPEG")
    if env_ffmpeg:
        return env_ffmpeg
    which = shutil.which("ffmpeg")
    if which:
        return which
    cand = REPO_ROOT / ".venv" / "bin" / "ffmpeg"
    if cand.exists():
        return str(cand)
    raise VisualError("ffmpeg not found; run ./setup.sh or pass --ffmpeg /path/to/ffmpeg")


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def rounded_mask(w: int, h: int, radius: int) -> np.ndarray:
    """Anti-aliased rounded-rectangle alpha mask, float32 in [0, 1]."""
    radius = max(1, min(int(radius), w // 2 - 1, h // 2 - 1))
    scale = 4
    W, H, R = w * scale, h * scale, radius * scale
    m = np.zeros((H, W), dtype=np.float32)
    cv2.rectangle(m, (R, 0), (W - R, H), 1.0, -1)
    cv2.rectangle(m, (0, R), (W, H - R), 1.0, -1)
    cv2.circle(m, (R, R), R, 1.0, -1)
    cv2.circle(m, (W - R, R), R, 1.0, -1)
    cv2.circle(m, (R, H - R), R, 1.0, -1)
    cv2.circle(m, (W - R, H - R), R, 1.0, -1)
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA)


def border_mask(outer: np.ndarray, border: int, radius: int) -> np.ndarray:
    if border <= 0:
        return np.zeros_like(outer)
    h, w = outer.shape
    b = min(int(border), w // 4, h // 4)
    # Keep the inner cut-out's corner radius tied to the requested radius.
    # Deriving it from min(w,h)/2 turned the "border" into a huge circular mask.
    inner = rounded_mask(w - 2 * b, h - 2 * b, max(1, int(radius) - b))
    full_inner = np.zeros_like(outer)
    full_inner[b : h - b, b : w - b] = inner
    return np.clip(outer - full_inner, 0.0, 1.0)


def center_square_crop(frame: np.ndarray, zoom: float) -> np.ndarray:
    h, w = frame.shape[:2]
    side = int(min(w, h) / max(1.0, zoom))
    side = max(2, min(side, min(w, h)))
    x = (w - side) // 2
    y = (h - side) // 2
    return frame[y : y + side, x : x + side]


def blend(
    canvas: np.ndarray,
    x: int,
    y: int,
    overlay: np.ndarray,
    alpha: np.ndarray,
) -> None:
    """Alpha-blend an overlay (image or solid colour array) into canvas in place."""
    oh, ow = alpha.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(canvas.shape[1], x + ow), min(canvas.shape[0], y + oh)
    if x1 <= x0 or y1 <= y0:
        return
    ox0, oy0 = x0 - x, y0 - y
    ox1, oy1 = ox0 + (x1 - x0), oy0 + (y1 - y0)
    a = alpha[oy0:oy1, ox0:ox1].astype(np.float32)
    if a.ndim == 2:
        a = a[:, :, None]
    src = overlay[oy0:oy1, ox0:ox1].astype(np.float32)
    roi = canvas[y0:y1, x0:x1].astype(np.float32)
    canvas[y0:y1, x0:x1] = np.clip(roi * (1.0 - a) + src * a, 0, 255).astype(np.uint8)


def solid(h: int, w: int, color: Tuple[float, float, float]) -> np.ndarray:
    out = np.empty((h, w, 3), dtype=np.float32)
    out[:, :, 0] = color[0]
    out[:, :, 1] = color[1]
    out[:, :, 2] = color[2]
    return out


def render(args: argparse.Namespace) -> None:
    bg_path = Path(args.background).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()
    if not bg_path.exists():
        raise VisualError("background video not found: %s" % bg_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(bg_path))
    if not cap.isOpened():
        raise VisualError("cannot open background video: %s" % bg_path)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or float(args.fps)
    if src_fps <= 0:
        src_fps = float(args.fps)

    ffmpeg = find_ffmpeg(args.ffmpeg)
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        "%dx%d" % (args.width, args.height),
        "-r",
        str(args.fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        args.preset,
        "-crf",
        str(args.crf),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    outer = rounded_mask(args.popup_width, args.popup_height, args.radius)
    border = border_mask(outer, args.border, args.radius)
    shadow = cv2.GaussianBlur(outer, (0, 0), sigmaX=max(1.0, args.shadow_blur))
    glow = cv2.GaussianBlur(outer, (0, 0), sigmaX=max(1.0, args.shadow_blur * 1.8))

    total = int(round(args.duration * args.fps))
    center_y = args.popup_top + args.popup_height // 2
    try:
        for n in range(total):
            t = n / float(args.fps)
            ret, frame = cap.read()
            if not ret:
                # Loop the short Pixabay clip seamlessly enough for a verse card.
                cap.release()
                cap = cv2.VideoCapture(str(bg_path))
                ret, frame = cap.read()
                if not ret:
                    raise VisualError("background video ended and could not be reopened")

            canvas = np.zeros((args.height, args.width, 3), dtype=np.uint8)
            if t >= args.intro:
                p = clamp((t - args.intro) / max(0.01, args.pop_duration))
                ease = 1.0 - (1.0 - p) ** 3
                scale = args.pop_scale + (1.0 - args.pop_scale) * ease
                w2 = max(2, int(round(args.popup_width * scale)))
                h2 = max(2, int(round(args.popup_height * scale)))
                fade = clamp((t - args.intro) / max(0.01, args.fade_in))

                # Slow push-in on the source video itself.
                progress = clamp(t / max(0.01, args.duration))
                zoom = args.zoom_start + (args.zoom_end - args.zoom_start) * progress
                crop = center_square_crop(frame, zoom)
                bg = cv2.resize(crop, (w2, h2), interpolation=cv2.INTER_AREA if w2 < crop.shape[1] else cv2.INTER_LINEAR)
                bg = np.clip(bg.astype(np.float32) * (1.0 - args.dim), 0, 255).astype(np.uint8)

                m2 = cv2.resize(outer, (w2, h2), interpolation=cv2.INTER_LINEAR)
                b2 = cv2.resize(border, (w2, h2), interpolation=cv2.INTER_LINEAR)
                s2 = cv2.resize(shadow, (w2, h2), interpolation=cv2.INTER_LINEAR)
                g2 = cv2.resize(glow, (w2, h2), interpolation=cv2.INTER_LINEAR)

                x = (args.width - w2) // 2
                y = center_y - h2 // 2

                blend(canvas, x, y, solid(h2, w2, GLOW_BGR), g2 * args.glow_strength * fade)
                blend(canvas, x + args.shadow_offset, y + args.shadow_offset, solid(h2, w2, SHADOW_BGR), s2 * args.shadow_strength * fade)
                blend(canvas, x, y, bg, m2 * fade)
                blend(canvas, x, y, solid(h2, w2, OFF_WHITE_BGR), b2 * args.border_strength * fade)

            proc.stdin.write(canvas.tobytes())
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise VisualError("ffmpeg exited with %s" % rc)
    except BrokenPipeError as e:
        raise VisualError("ffmpeg pipe closed early: %s" % e)
    finally:
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except Exception:
            pass
        cap.release()

    print("Visual base: %s (%.3fs, %dx%d, %d fps, source %.2f fps)" % (out_path, args.duration, args.width, args.height, args.fps, src_fps))


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Black 9:16 base with a rounded, animated background-video popup.")
    ap.add_argument("--background", required=True, help="source background video, e.g. Pixabay MP4")
    ap.add_argument("--out", required=True, help="output silent visual-base MP4")
    ap.add_argument("--duration", type=float, required=True, help="duration in seconds")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--intro", type=float, default=0.8, help="seconds of pure black before the popup")
    ap.add_argument("--pop-duration", type=float, default=0.7, help="popup scale-in duration")
    ap.add_argument("--pop-scale", type=float, default=0.90, help="starting scale of the popup")
    ap.add_argument("--fade-in", type=float, default=0.35, help="popup opacity fade-in duration")
    ap.add_argument("--popup-top", type=int, default=380)
    ap.add_argument("--popup-width", type=int, default=1000)
    ap.add_argument("--popup-height", type=int, default=860)
    ap.add_argument("--radius", type=int, default=90)
    ap.add_argument("--border", type=int, default=2)
    ap.add_argument("--border-strength", type=float, default=0.20)
    ap.add_argument("--shadow-blur", type=float, default=26.0)
    ap.add_argument("--shadow-offset", type=int, default=14)
    ap.add_argument("--shadow-strength", type=float, default=0.34)
    ap.add_argument("--glow-strength", type=float, default=0.055)
    ap.add_argument("--zoom-start", type=float, default=1.08)
    ap.add_argument("--zoom-end", type=float, default=1.00)
    ap.add_argument("--dim", type=float, default=0.08, help="darken the popup video, 0..0.5")
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--ffmpeg", help="explicit ffmpeg path")
    args = ap.parse_args(argv)

    try:
        render(args)
        return 0
    except (VisualError, OSError, subprocess.SubprocessError) as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
