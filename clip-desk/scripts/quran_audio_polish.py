#!/usr/bin/env python3
"""Polish a Quran recitation for a short verse card, without touching the words.

What this does — and deliberately does not do:
  * builds a synthetic *hall* impulse response (exponentially decaying noise, darker
    over time) and convolves it in as a low-level send, so the voice gains a sense of
    a large room without any pitched/metallic tone,
  * adds a short pre-delay (default 45 ms) so the reverb sits behind the voice instead
    of smearing the consonants; the pre-delay is far below echo perception, so no word
    ever repeats or doubles,
  * light clarity EQ: rumble high-pass, small mud cut, small presence lift,
  * gentle compression, then a peak limiter and a loudness match to a target LUFS.

It never time-stretches, pitch-shifts, denoises-to-taste or re-orders the recitation,
so verse/word timings from Quran Foundation still line up exactly. The dry voice is
never delayed: only the reverb send carries the pre-delay.

Example:
  python clip-desk/scripts/quran_audio_polish.py \
    --in assets/quran/001_al-baqarah_2-152-153_yasser-ad-dussary/recitation.m4a \
    --out jobs/001_al-baqarah_2-152-153_yasser-ad-dussary/recitation_polished.m4a \
    --tail 0.4 --target-lufs -14.5
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]


class AudioPolishError(Exception):
    pass


def find_bin(name: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    env = os.environ.get("CLIP_DESK_%s" % name.upper())
    if env:
        return env
    which = shutil.which(name)
    if which:
        return which
    cand = REPO_ROOT / ".venv" / "bin" / name
    if cand.exists():
        return str(cand)
    raise AudioPolishError("%s not found; run ./setup.sh" % name)


def build_hall_ir(
    path: Path,
    rate: int = 44100,
    decay_s: float = 0.52,
    length_s: float = 1.6,
    predelay_ms: float = 45.0,
    damping_hz: float = 3600.0,
    low_cut_hz: float = 140.0,
    seed: int = 20261121,
) -> None:
    """Write a stereo, smooth, noise-based hall IR with an exact pre-delay."""
    n = int(rate * length_s)
    t = np.arange(n, dtype=np.float64) / rate
    rng = np.random.default_rng(seed)

    # Frequency-dependent decay: bright energy dies faster than low-mid energy.
    ir = np.zeros((n, 2), dtype=np.float64)
    for ch in range(2):
        noise = rng.standard_normal(n)
        spec = np.fft.rfft(noise)
        freqs = np.fft.rfftfreq(n, 1.0 / rate)
        # Dark tilt + gentle low cut: no boom, no metallic resonance (no peaks).
        tilt = 1.0 / (1.0 + (freqs / damping_hz) ** 1.6)
        lowcut = freqs / (freqs + low_cut_hz)
        shaped = np.fft.irfft(spec * tilt * lowcut, n)
        env = np.exp(-t / decay_s) * (1.0 - np.exp(-t / 0.012))
        ir[:, ch] = shaped * env

    # Smooth diffused build, then normalise to unit energy so wet level is predictable.
    for ch in range(2):
        ir[:, ch] = np.convolve(ir[:, ch], np.ones(9) / 9.0, mode="same")
    ir -= ir.mean(axis=0)
    ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True))

    pre = int(round(rate * predelay_ms / 1000.0))
    padded = np.zeros((n + pre, 2), dtype=np.float64)
    padded[pre:] = ir

    pcm = np.clip(padded * 32767.0 * 0.25, -32768, 32767).astype("<i2")
    import wave

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())


def measure(ffmpeg: str, path: Path) -> dict:
    out = subprocess.run(
        [ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stderr
    start = out.rfind("{")
    end = out.rfind("}")
    if start < 0 or end < start:
        raise AudioPolishError("could not parse loudnorm output")
    data = json.loads(out[start : end + 1])
    return {
        "lufs": float(data["input_i"]),
        "peak_dbtp": float(data["input_tp"]),
        "lra": float(data["input_lra"]),
    }


def build_filter(
    ir_path: Path,
    wet: float,
    highpass: float,
    mud_hz: float,
    mud_db: float,
    presence_hz: float,
    presence_db: float,
    comp_ratio: float,
    comp_threshold: float,
    tail_s: float,
    fade_out_s: float,
    gain_db: float,
    ceiling_db: float,
    duration_s: Optional[float],
) -> str:
    pre = [
        "aformat=sample_fmts=fltp:channel_layouts=stereo:sample_rates=44100",
        "highpass=f=%.1f:poles=2" % highpass,
        "equalizer=f=%.0f:width_type=q:w=1.0:g=%.2f" % (mud_hz, mud_db),
        "equalizer=f=%.0f:width_type=q:w=1.05:g=%.2f" % (presence_hz, presence_db),
        "acompressor=threshold=%.3f:ratio=%.2f:attack=14:release=240:makeup=1.0"
        % (comp_threshold, comp_ratio),
    ]
    post = [
        "volume=%.3f" % (10 ** (gain_db / 20.0)),
        "alimiter=limit=%.4f:attack=5:release=60:level=0" % (10 ** (ceiling_db / 20.0)),
    ]
    if duration_s:
        post.append("apad=whole_dur=%.3f" % duration_s)
        post.append("atrim=0:%.3f" % duration_s)
    else:
        post.append("apad=pad_dur=%.3f" % max(0.0, tail_s))
    if fade_out_s > 0:
        post.append("afade=t=out:st=%.3f:d=%.3f" % (max(0.0, (duration_s or 0) - fade_out_s), fade_out_s))

    graph = [
        "[0:a]" + ",".join(pre) + ",asplit=2[dry][send]",
        # The IR is the second ffmpeg input; it carries the pre-delay, never the dry voice.
        "[send][1:a]afir=gtype=none[wetraw]",
        "[wetraw]volume=%.4f[wet]" % wet,
        "[dry]volume=1.0[d]",
        "[d][wet]amix=inputs=2:normalize=0," + ",".join(post) + "[aout]",
    ]
    return ";".join(graph)


def run(args: argparse.Namespace) -> None:
    ffmpeg = find_bin("ffmpeg", args.ffmpeg)
    src = Path(args.input).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    if not src.exists():
        raise AudioPolishError("input audio not found: %s" % src)
    out.parent.mkdir(parents=True, exist_ok=True)

    probe = subprocess.run(
        [
            find_bin("ffprobe", args.ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(src),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    src_duration = float(probe)

    with tempfile.TemporaryDirectory() as td:
        ir_path = Path(td) / "hall_ir.wav"
        build_hall_ir(
            ir_path,
            decay_s=args.decay,
            length_s=args.ir_length,
            predelay_ms=args.predelay,
            damping_hz=args.damping,
        )

        duration_s = src_duration + max(0.0, args.tail)
        # First pass: measure at unity gain, then bake the loudness match in.
        gain_db = 0.0
        for _ in range(2):
            graph = build_filter(
                ir_path,
                wet=args.wet,
                highpass=args.highpass,
                mud_hz=args.mud_hz,
                mud_db=args.mud_db,
                presence_hz=args.presence_hz,
                presence_db=args.presence_db,
                comp_ratio=args.comp_ratio,
                comp_threshold=args.comp_threshold,
                tail_s=0.0,
                fade_out_s=args.fade_out,
                gain_db=gain_db,
                ceiling_db=args.ceiling,
                duration_s=duration_s,
            )
            cmd = [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(src),
                "-i", str(ir_path),
                "-filter_complex", graph,
                "-map", "[aout]",
                "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
                str(out),
            ]
            subprocess.run(cmd, check=True)
            info = measure(ffmpeg, out)
            delta = args.target_lufs - info["lufs"]
            if abs(delta) <= args.tolerance and info["peak_dbtp"] <= args.ceiling - 0.05:
                break
            gain_db += delta

        if info["peak_dbtp"] > args.ceiling + 0.05:
            raise AudioPolishError(
                "true peak %.2f dBTP exceeds the %.2f dBTP ceiling" % (info["peak_dbtp"], args.ceiling)
            )

        print(
            "Audio polish: %s -> %s (%.3fs, %.1f LUFS, %.1f dBTP, wet %.2f, predelay %.0f ms, gain %+.1f dB)"
            % (
                src,
                out,
                duration_s,
                info["lufs"],
                info["peak_dbtp"],
                args.wet,
                args.predelay,
                gain_db,
            ),
            file=sys.stderr,
        )


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Add a subtle hall space and clarity to a recitation without altering words or timing."
    )
    ap.add_argument("--in", dest="input", required=True, help="source recitation audio")
    ap.add_argument("--out", dest="output", required=True, help="polished audio (AAC/M4A)")
    ap.add_argument("--wet", type=float, default=0.15, help="reverb send level, 0..1 (default 0.15 = -16 dB)")
    ap.add_argument("--predelay", type=float, default=45.0, help="reverb pre-delay in ms (default 45)")
    ap.add_argument("--decay", type=float, default=0.52, help="IR decay time constant in seconds")
    ap.add_argument("--ir-length", type=float, default=1.6, help="IR length in seconds")
    ap.add_argument("--damping", type=float, default=3600.0, help="IR high-frequency damping start (Hz)")
    ap.add_argument("--highpass", type=float, default=72.0, help="rumble high-pass (Hz)")
    ap.add_argument("--mud-hz", type=float, default=330.0)
    ap.add_argument("--mud-db", type=float, default=-1.6, help="small cut around --mud-hz")
    ap.add_argument("--presence-hz", type=float, default=2900.0)
    ap.add_argument("--presence-db", type=float, default=2.0, help="gentle vocal presence lift")
    ap.add_argument("--comp-ratio", type=float, default=1.7)
    ap.add_argument("--comp-threshold", type=float, default=0.13, help="linear compressor threshold (~-17.7 dBFS)")
    ap.add_argument("--tail", type=float, default=0.4, help="extra seconds kept so the reverb tail rings out")
    ap.add_argument("--fade-out", type=float, default=0.35, help="final fade-out seconds")
    ap.add_argument("--target-lufs", type=float, default=-14.5)
    ap.add_argument("--tolerance", type=float, default=0.3)
    ap.add_argument("--ceiling", type=float, default=-1.5, help="true-peak ceiling in dBTP")
    ap.add_argument("--ffmpeg")
    ap.add_argument("--ffprobe")
    args = ap.parse_args(argv)
    try:
        run(args)
        return 0
    except (AudioPolishError, OSError, subprocess.SubprocessError, KeyError) as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
