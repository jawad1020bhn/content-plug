#!/usr/bin/env python3
"""Render a black 9:16 verse-card base with a rounded, animated video popup.

This is the visual half of ``quran-subtitles``. It does not draw Quran text,
translations, credits or any burned-in credit. ``quran_subtitles.py`` adds the
canonical ASS captions and the recitation audio on top.

Example:
  python clip-desk/scripts/quran_visual.py \
    --background assets/quran/001_al-baqarah_2-152-153_yasser-ad-dussary/background.mp4 \
    --out jobs/001_al-baqarah_2-152-153_yasser-ad-dussary/visual_base.mp4 \
    --duration 27.0 --intro 0.0 --open-blur 5.8 --loop-tail 0.45 \
    --aspect-crop --emerald-grade --top-lit-border --motes --progress-bar \
    --audio-envelope jobs/001_al-baqarah_2-152-153_yasser-ad-dussary/recitation_polished.m4a \
    --popup-top 340 --popup-width 1000 --popup-height 780 --radius 90
"""

from __future__ import annotations

import argparse
import math
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


def center_aspect_crop(frame: np.ndarray, zoom: float, target_w: int, target_h: int) -> np.ndarray:
    """True-aspect center crop matching target_w:target_h without vertical squash."""
    fh, fw = frame.shape[:2]
    z = max(1.0, zoom)
    cw = int(fw / z)
    ch = int(cw * target_h / max(1, target_w))
    if ch > fh:
        ch = int(fh / z)
        cw = int(ch * target_w / max(1, target_h))
    cw = max(2, min(cw, fw))
    ch = max(2, min(ch, fh))
    x0 = (fw - cw) // 2
    y0 = (fh - ch) // 2
    return frame[y0 : y0 + ch, x0 : x0 + cw]


def extract_audio_envelope(ffmpeg: str, audio_path: Path, duration_s: float, fps: int) -> np.ndarray:
    """Extract a smoothed [0..1] vocal loudness envelope at video frame rate."""
    raw = subprocess.check_output(
        [ffmpeg, "-v", "error", "-i", str(audio_path), "-f", "f32le", "-ac", "1", "-ar", "44100", "-"]
    )
    samples = np.frombuffer(raw, dtype=np.float32)
    sr = 44100
    total_frames = max(1, int(round(duration_s * fps)))
    hop = max(1, sr // max(1, fps))
    frame_rms = np.zeros(total_frames, dtype=np.float64)
    for idx in range(total_frames):
        s0 = idx * hop
        s1 = min(len(samples), s0 + hop)
        if s1 > s0:
            frame_rms[idx] = float(np.sqrt(np.mean(samples[s0:s1] ** 2)))
    kx = np.arange(-5, 6, dtype=np.float64)
    kernel = np.exp(-0.5 * (kx / 2.2) ** 2)
    kernel /= kernel.sum()
    smooth = np.convolve(frame_rms, kernel, mode="same")
    p95 = float(np.percentile(smooth[smooth > 1e-4], 95)) if np.any(smooth > 1e-4) else 0.1
    return np.clip(smooth / max(p95, 1e-4), 0.0, 1.0)


def apply_emerald_grade(bgr: np.ndarray, inner_vignette_3c: np.ndarray) -> np.ndarray:
    """Mute glaring neon reds/yellows into earthy cedar and shift greens toward moody pine."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h_idx = hsv[:, :, 0]
    s_f = hsv[:, :, 1].astype(np.float32)
    v_f = hsv[:, :, 2].astype(np.float32)

    h_vals = np.arange(256, dtype=np.float32)
    red_w = np.clip(1.0 - np.minimum(h_vals, np.abs(180.0 - h_vals)) / 16.0, 0.0, 1.0)
    yel_w = np.clip(1.0 - np.abs(h_vals - 24.0) / 12.0, 0.0, 1.0)
    grn_w = np.clip(1.0 - np.abs(h_vals - 62.0) / 28.0, 0.0, 1.0)

    s_scale = (1.0 - 0.58 * red_w - 0.55 * yel_w - 0.08 * grn_w)[h_idx]
    v_scale = (1.0 - 0.18 * red_w - 0.12 * yel_w)[h_idx]
    h_new = np.clip(np.round((h_vals + 3.5 * grn_w) % 180.0), 0, 179).astype(np.uint8)[h_idx]

    hsv[:, :, 0] = h_new
    hsv[:, :, 1] = np.clip(s_f * s_scale, 0, 255).astype(np.uint8)
    hsv[:, :, 2] = np.clip(v_f * v_scale, 0, 255).astype(np.uint8)
    graded = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR).astype(np.float32)
    graded = (127.5 + (graded - 127.5) * 1.06) * inner_vignette_3c
    return np.clip(graded, 0.0, 255.0).astype(np.uint8)


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
    env_30fps: Optional[np.ndarray] = None
    if args.audio_envelope:
        audio_p = Path(args.audio_envelope).expanduser().resolve()
        if not audio_p.exists():
            raise VisualError("audio envelope source not found: %s" % audio_p)
        env_30fps = extract_audio_envelope(ffmpeg, audio_p, args.duration, args.fps)

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
    if args.top_lit_border:
        y_grad = np.linspace(1.0, 0.0, args.popup_height, dtype=np.float32)[:, None]
        x_grad = 1.0 - 0.25 * np.abs(np.linspace(-1.0, 1.0, args.popup_width, dtype=np.float32))[None, :]
        border = border * (0.35 + 1.40 * (y_grad ** 1.5) * x_grad)

    pad = 110
    padded_outer = np.zeros((args.popup_height + 2 * pad, args.popup_width + 2 * pad), dtype=np.float32)
    padded_outer[pad : pad + args.popup_height, pad : pad + args.popup_width] = outer
    shadow = cv2.GaussianBlur(padded_outer, (0, 0), sigmaX=max(1.0, args.shadow_blur))
    glow = cv2.GaussianBlur(padded_outer, (0, 0), sigmaX=max(1.0, args.shadow_blur * 1.7))

    yy = np.linspace(-1.0, 1.0, args.popup_height, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, args.popup_width, dtype=np.float32)[None, :]
    inner_vig = np.clip(1.0 - 0.14 * (xx * xx + yy * yy), 0.78, 1.0)
    inner_vig_3c = np.stack([inner_vig * 1.02, inner_vig * 1.00, inner_vig * 0.97], axis=-1).astype(np.float32)

    sp_r = 8
    sy, sx = np.mgrid[-sp_r : sp_r + 1, -sp_r : sp_r + 1].astype(np.float32)
    mote_sprite = np.exp(-0.5 * (sx * sx + sy * sy) / (2.6 ** 2))[:, :, None] * np.array([205.0, 218.0, 232.0], dtype=np.float32)
    motes = []
    if args.motes:
        rng = np.random.default_rng(786)
        for _ in range(14):
            mx = float(rng.uniform(90, args.width - 90))
            my = float(rng.choice([rng.uniform(110, max(120, args.popup_top - 20)), rng.uniform(args.popup_top + args.popup_height + 30, args.height - 160)]))
            vy = float(rng.uniform(-9.0, -4.5))
            vx = float(rng.uniform(-3.0, 3.0))
            op = float(rng.uniform(0.032, 0.062))
            ph = float(rng.uniform(0, 2 * math.pi))
            motes.append((mx, my, vx, vy, op, ph))

    total = int(round(args.duration * args.fps))
    center_y = args.popup_top + args.popup_height // 2
    try:
        for n in range(total):
            t = n / float(args.fps)
            ret, frame = cap.read()
            if not ret:
                cap.release()
                cap = cv2.VideoCapture(str(bg_path))
                ret, frame = cap.read()
                if not ret:
                    raise VisualError("background video ended and could not be reopened")

            canvas = np.zeros((args.height, args.width, 3), dtype=np.uint8)
            voice_e = float(env_30fps[min(n, len(env_30fps) - 1)]) if env_30fps is not None else 0.0

            if motes:
                canvas_f = canvas.astype(np.float32)
                for mx, my, vx, vy, op, ph in motes:
                    px = int((mx + vx * t + 8.0 * math.sin(0.5 * t + ph)) % (args.width - 2 * sp_r - 2)) + sp_r
                    py = int((my + vy * t) % (args.height - 2 * sp_r - 2)) + sp_r
                    if args.popup_top - 14 <= py <= args.popup_top + args.popup_height + 14:
                        continue
                    twinkle = op * (0.65 + 0.35 * math.sin(1.4 * t + ph))
                    canvas_f[py - sp_r : py + sp_r + 1, px - sp_r : px + sp_r + 1] += mote_sprite * twinkle
                canvas = np.clip(canvas_f, 0, 255).astype(np.uint8)

            if t >= args.intro:
                p = clamp((t - args.intro) / max(0.01, args.pop_duration))
                ease = 1.0 - (1.0 - p) ** 3
                tail_ease = 0.0
                if args.loop_tail > 0.0:
                    tp = clamp((t - (args.duration - args.loop_tail)) / args.loop_tail)
                    tail_ease = tp * tp
                scale = (args.pop_scale + (1.0 - args.pop_scale) * ease) * (1.0 - 0.032 * tail_ease)
                w2 = max(2, int(round(args.popup_width * scale)))
                h2 = max(2, int(round(args.popup_height * scale)))
                pad2 = max(2, int(round(pad * scale)))
                pw2, ph2 = w2 + 2 * pad2, h2 + 2 * pad2
                fade = clamp((t - args.intro) / max(0.01, args.fade_in)) * (1.0 - 0.16 * tail_ease)

                progress = clamp(t / max(0.01, args.duration))
                zoom = args.zoom_start + (args.zoom_end - args.zoom_start) * progress
                if args.aspect_crop:
                    crop = center_aspect_crop(frame, zoom, args.popup_width, args.popup_height)
                else:
                    crop = center_square_crop(frame, zoom)
                bg = cv2.resize(crop, (w2, h2), interpolation=cv2.INTER_AREA if w2 < crop.shape[1] else cv2.INTER_LINEAR)

                if args.emerald_grade:
                    iv = inner_vig_3c if (w2 == args.popup_width and h2 == args.popup_height) else cv2.resize(inner_vig_3c, (w2, h2))
                    bg = apply_emerald_grade(bg, iv)

                blur_sigma = 0.0
                if args.open_blur > 0.0:
                    blur_sigma += args.open_blur * ((1.0 - clamp((t - args.intro) / 0.55)) ** 2)
                if tail_ease > 0.0:
                    blur_sigma += 4.8 * tail_ease
                if blur_sigma > 0.25:
                    bg = cv2.GaussianBlur(bg, (0, 0), sigmaX=blur_sigma)

                bg = np.clip(bg.astype(np.float32) * (1.0 - args.dim), 0, 255).astype(np.uint8)

                m2 = outer if (w2 == args.popup_width and h2 == args.popup_height) else cv2.resize(outer, (w2, h2), interpolation=cv2.INTER_LINEAR)
                b2 = border if (w2 == args.popup_width and h2 == args.popup_height) else cv2.resize(border, (w2, h2), interpolation=cv2.INTER_LINEAR)
                s2 = shadow if (pw2 == shadow.shape[1] and ph2 == shadow.shape[0]) else cv2.resize(shadow, (pw2, ph2), interpolation=cv2.INTER_LINEAR)
                g2 = glow if (pw2 == glow.shape[1] and ph2 == glow.shape[0]) else cv2.resize(glow, (pw2, ph2), interpolation=cv2.INTER_LINEAR)

                x = (args.width - w2) // 2
                y = center_y - h2 // 2

                dyn_glow = args.glow_strength + (0.042 * voice_e if env_30fps is not None else 0.0)
                blend(canvas, x - pad2, y - pad2, solid(ph2, pw2, GLOW_BGR), g2 * dyn_glow * fade)
                blend(canvas, x - pad2 + args.shadow_offset, y - pad2 + args.shadow_offset, solid(ph2, pw2, SHADOW_BGR), s2 * args.shadow_strength * fade)
                blend(canvas, x, y, bg, m2 * fade)
                blend(canvas, x, y, solid(h2, w2, OFF_WHITE_BGR), b2 * args.border_strength * fade)

            if args.progress_bar and t >= max(0.0, args.intro):
                bar_w = 210
                bar_x0 = (args.width - bar_w) // 2
                bar_y = args.progress_y
                fil_fade = clamp((t - args.intro) / 0.35) * clamp((args.duration - t) / 0.35)
                if 0 <= bar_y < args.height - 2 and fil_fade > 0.01:
                    roi = canvas[bar_y : bar_y + 2, bar_x0 : bar_x0 + bar_w].astype(np.float32)
                    roi += np.array([195.0, 202.0, 210.0], dtype=np.float32) * (0.12 * fil_fade)
                    fill_w = int(round(bar_w * clamp((t - args.intro) / max(0.1, args.duration - args.intro))))
                    if fill_w > 0:
                        roi[:, :fill_w] = roi[:, :fill_w] * (1.0 - 0.44 * fil_fade) + np.array([205.0, 220.0, 235.0], dtype=np.float32) * (0.44 * fil_fade)
                    canvas[bar_y : bar_y + 2, bar_x0 : bar_x0 + bar_w] = np.clip(roi, 0, 255).astype(np.uint8)

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
    ap.add_argument("--aspect-crop", action="store_true", help="preserve true popup aspect ratio instead of 1:1 square crop")
    ap.add_argument("--emerald-grade", action="store_true", help="mute neon reds/yellows and shift foliage toward moody emerald")
    ap.add_argument("--audio-envelope", help="optional audio path to modulate halo glow with vocal loudness")
    ap.add_argument("--top-lit-border", action="store_true", help="directional top-lit frosted glass border")
    ap.add_argument("--motes", action="store_true", help="subtle warm atmospheric motes in dark canvas space")
    ap.add_argument("--progress-bar", action="store_true", help="hair-thin recitation progress filament below reference")
    ap.add_argument("--progress-y", type=int, default=1662, help="y position of progress filament")
    ap.add_argument("--open-blur", type=float, default=0.0, help="initial optical defocus sigma on popup open (e.g. 5.8)")
    ap.add_argument("--loop-tail", type=float, default=0.0, help="seconds at end to ease scale/blur for seamless loop (e.g. 0.45)")
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
