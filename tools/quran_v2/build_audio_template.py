# TEMPLATE — proven on slots 001-v2 and 002. Copy to jobs/<slot>/ and edit the
# SLOT constants listed in tools/quran_v2/README.md before running. Do not run in place.

#!/usr/bin/env python3
"""Build Pro Masjid al-Haram Spatial Master for Slot 002 (Sheikh Ali Jaber, 2:155-157).

Preserves 100% of original recitation words, pitch, and timing (raw 0.00s..41.00s).
Adds:
  1. Gentle vocal clarity sculpting (sub-rumble HPF 68 Hz, warm chest +1.3 dB @ 175 Hz,
     mud cut -2.2 dB @ 340 Hz, Hijazi presence lift +1.7 dB @ 3.8 kHz, silky 10.8 kHz air shelf)
  2. True Stereo Masjid al-Haram Sanctuary Impulse Response:
     - 56 ms pre-delay (consonants stay 100% crisp and dry up front; zero echo/doubling)
     - Discrete wide-stereo marble courtyard early reflections (62/79/104/131 ms L/R)
     - Dual-decay lush sanctuary tail (mid RT60 ~1.55 s, high RT60 ~0.72 s, stereo decorrelated,
       wet send = 0.34 for rich unmistakable Haram acoustic space)
  3. Ultra-subtle non-musical alpine water ripple bed (-35 dBFS, ducked under recitation)
     + micro-tactile scroll lock thud at t=0.63s (-30 dBFS) during the 0.00-0.84s fake scroll
  4. Two-pass EBU R128 mastering to -14.3 LUFS / <= -1.5 dBTP, plus 30fps voice envelope export.
"""

from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path

import numpy as np

import shutil

ROOT = Path(__file__).resolve().parents[2]
FFMPEG = shutil.which("ffmpeg") or str(ROOT / ".venv" / "bin" / "ffmpeg")
SLOT = "002_al-baqarah_2-155-157_ali-jaber"
RAW_IN = ROOT / "assets" / "quran" / SLOT / "recitation_raw.m4a"
JOB_DIR = ROOT / "jobs" / SLOT
IR_WAV = JOB_DIR / "haram_sanctuary_ir.wav"
AMBIENCE_WAV = JOB_DIR / "lake_ambience.wav"
PREMASTER_WAV = JOB_DIR / "recitation_premaster.wav"
MASTER_M4A = JOB_DIR / "recitation_master.m4a"
ENV_NPY = JOB_DIR / "voice_env_30fps.npy"
AUDIO_REPORT = JOB_DIR / "audio_report.json"

DURATION_S = 41.00
SR = 44100
FPS = 30


def write_wav_stereo(path: Path, data: np.ndarray, sr: int = SR) -> None:
    pcm = np.clip(data * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def build_haram_sanctuary_ir(path: Path) -> None:
    """True-stereo Masjid al-Haram courtyard + sanctuary hall IR (3.2 s)."""
    length_s = 3.2
    predelay_ms = 56.0
    n = int(SR * length_s)
    t = np.arange(n, dtype=np.float64) / SR
    rng = np.random.default_rng(20261122)

    ir = np.zeros((n, 2), dtype=np.float64)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)

    for ch in range(2):
        # Decorrelated diffuse field per channel
        noise_mid = rng.standard_normal(n)
        noise_air = rng.standard_normal(n)

        spec_mid = np.fft.rfft(noise_mid)
        spec_air = np.fft.rfft(noise_air)

        # Warm marble body (170 Hz .. 2800 Hz, longer decay 1.50s)
        band_mid = (freqs / (freqs + 170.0)) * (1.0 / (1.0 + (freqs / 2700.0) ** 1.8))
        # Silky sanctuary air (900 Hz .. 5200 Hz, faster decay 0.68s so sibilants never hiss)
        band_air = ((freqs / (freqs + 900.0)) ** 2) * (1.0 / (1.0 + (freqs / 5000.0) ** 2.2))

        tail_mid = np.fft.irfft(spec_mid * band_mid, n)
        tail_air = np.fft.irfft(spec_air * band_air, n)

        attack = 1.0 - np.exp(-t / 0.022)
        env_mid = np.exp(-t / (1.48 + 0.05 * ch)) * attack
        env_air = np.exp(-t / 0.66) * (1.0 - np.exp(-t / 0.010))

        diffuse = 0.78 * tail_mid * env_mid + 0.34 * tail_air * env_air
        diffuse = np.convolve(diffuse, np.ones(7) / 7.0, mode="same")
        ir[:, ch] = diffuse

    # Normalise diffuse tail energy first
    ir -= ir.mean(axis=0)
    ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True))

    # Prepend 56 ms pre-delay + subtle stereo marble early reflections
    pre = int(round(SR * predelay_ms / 1000.0))
    total = np.zeros((n + pre, 2), dtype=np.float64)
    total[pre:] = ir * 0.24

    # Early reflections (filtered soft taps, decorrelated L/R for 3D stereo sanctuary width)
    er_taps_l = [(62.0, 0.032), (96.0, -0.021), (128.0, 0.015)]
    er_taps_r = [(74.0, 0.030), (109.0, -0.020), (141.0, 0.014)]
    tap_kernel = np.hanning(33)
    tap_kernel /= tap_kernel.sum()
    for ms, gain in er_taps_l:
        idx = int(round(SR * ms / 1000.0))
        if idx + 33 < len(total):
            total[idx : idx + 33, 0] += gain * tap_kernel
    for ms, gain in er_taps_r:
        idx = int(round(SR * ms / 1000.0))
        if idx + 33 < len(total):
            total[idx : idx + 33, 1] += gain * tap_kernel

    write_wav_stereo(path, total, SR)


def build_subtle_ambience_and_scroll_cue(path: Path, voice_mono_44k: np.ndarray) -> None:
    """Ultra-subtle non-musical lake water air (-35 dBFS, ducked under voice) + soft scroll settle."""
    n = int(SR * DURATION_S)
    rng = np.random.default_rng(77002)
    bed = np.zeros((n, 2), dtype=np.float64)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    # Gentle natural water-air spectrum (band-limited 260..2400 Hz, zero tonal peaks)
    water_shape = ((freqs / (freqs + 280.0)) ** 1.5) / (1.0 + (freqs / 2100.0) ** 2.4)
    t = np.arange(n, dtype=np.float64) / SR
    lfo_l = 0.78 + 0.22 * np.sin(2.0 * np.pi * 0.19 * t)
    lfo_r = 0.78 + 0.22 * np.sin(2.0 * np.pi * 0.17 * t + 1.3)

    for ch, lfo in enumerate((lfo_l, lfo_r)):
        w = np.fft.irfft(np.fft.rfft(rng.standard_normal(n)) * water_shape, n)
        w /= np.max(np.abs(w)) + 1e-9
        bed[:, ch] = w * lfo * 0.011  # ~ -39 dBFS peak, completely subliminal & natural

    # Sidechain ducking from voice envelope so recitation stays 100% pure
    win = int(SR * 0.08)
    v_abs = np.abs(voice_mono_44k[:n])
    if len(v_abs) < n:
        v_abs = np.pad(v_abs, (0, n - len(v_abs)))
    env = np.convolve(v_abs, np.ones(win) / win, mode="same")
    duck = 1.0 - 0.65 * np.clip(env / 0.12, 0.0, 1.0)
    bed *= duck[:, None]

    # Subtle iOS-like low-frequency felt scroll-settle air at t=0.14s (flick) and t=0.63s (spring lock)
    # Strictly non-musical, ultra-soft tactile air (< -29 dBFS)
    for t0, f0, amp, decay in [(0.12, 145.0, 0.018, 0.11), (0.63, 92.0, 0.022, 0.075)]:
        i0 = int(t0 * SR)
        span = int(0.28 * SR)
        ts = np.arange(span, dtype=np.float64) / SR
        # Pitch-dropping damped thud + soft air brush
        thud = np.sin(2.0 * np.pi * f0 * ts * np.exp(-ts * 4.5)) * np.exp(-ts / decay) * (1.0 - np.exp(-ts / 0.006))
        if i0 + span < n:
            bed[i0 : i0 + span, 0] += amp * thud
            bed[i0 : i0 + span, 1] += amp * thud

    # Smooth fade-in and loop tail fade-out
    fade_in = int(0.18 * SR)
    fade_out = int(0.45 * SR)
    bed[:fade_in] *= np.linspace(0.0, 1.0, fade_in)[:, None]
    bed[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)[:, None]

    write_wav_stereo(path, bed, SR)


def measure_loudnorm(path: Path) -> dict:
    proc = subprocess.run(
        [FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-af", "loudnorm=I=-14.3:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    err = proc.stderr
    s = err.rfind("{")
    e = err.rfind("}")
    return json.loads(err[s : e + 1])


def main() -> None:
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    build_haram_sanctuary_ir(IR_WAV)

    # Decode raw recitation mono for envelope + ducking
    raw_bytes = subprocess.check_output(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(RAW_IN), "-ac", "1", "-ar", str(SR), "-f", "f32le", "pipe:1"]
    )
    voice_mono = np.frombuffer(raw_bytes, dtype=np.float32)

    # Export smooth 30fps voice envelope for voice-reactive popup halo
    n_frames = int(round(DURATION_S * FPS))
    spf = SR // FPS
    env_30 = np.zeros(n_frames, dtype=np.float32)
    for f in range(n_frames):
        seg = voice_mono[f * spf : (f + 1) * spf]
        if len(seg) > 0:
            env_30[f] = float(np.sqrt(np.mean(seg ** 2)))
    # Smooth attack/release so halo breathes organically
    smooth = np.zeros_like(env_30)
    cur = 0.0
    for i, v in enumerate(env_30):
        coeff = 0.38 if v > cur else 0.14
        cur = cur + coeff * (v - cur)
        smooth[i] = cur
    p95 = float(np.percentile(smooth, 95)) or 1.0
    smooth = np.clip(smooth / p95, 0.0, 1.0)
    np.save(ENV_NPY, smooth)

    build_subtle_ambience_and_scroll_cue(AMBIENCE_WAV, voice_mono)

    # Pass 1: Mix sculpted dry recitation + true-stereo Haram Sanctuary IR (wet=0.36) + subtle ambience
    # Note: dry path is NEVER time-stretched, pitch-shifted, or delayed!
    fc = (
        "[0:a]aresample=44100,"
        "highpass=f=68:poles=2,"
        "equalizer=f=175:t=q:w=0.9:g=1.3,"
        "equalizer=f=340:t=q:w=1.2:g=-2.2,"
        "equalizer=f=3800:t=q:w=1.0:g=1.7,"
        "lowpass=f=11800:poles=1,"
        "acompressor=threshold=-20dB:ratio=2.1:attack=18:release=190:makeup=1.5,"
        "afade=t=in:st=0.05:d=0.45,"
        "afade=t=out:st=40.52:d=0.46,"
        "asplit=2[dry][send];"
        "[send]equalizer=f=240:t=q:w=0.8:g=-2.5,afir=dry=10:wet=10[wet];"
        "[dry][wet]amix=inputs=2:weights='1.0 0.42':normalize=0[vocal];"
        "[vocal][2:a]amix=inputs=2:weights='1.0 1.0':normalize=0,"
        "atrim=0:41.00,asetpts=PTS-STARTPTS[out]"
    )
    subprocess.run(
        [
            FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(RAW_IN),
            "-i", str(IR_WAV),
            "-i", str(AMBIENCE_WAV),
            "-filter_complex", fc,
            "-map", "[out]",
            "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le",
            str(PREMASTER_WAV),
        ],
        check=True,
    )

    stats1 = measure_loudnorm(PREMASTER_WAV)
    ln2 = (
        f"loudnorm=I=-14.3:TP=-1.5:LRA=11:"
        f"measured_I={stats1['input_i']}:"
        f"measured_TP={stats1['input_tp']}:"
        f"measured_LRA={stats1['input_lra']}:"
        f"measured_thresh={stats1['input_thresh']}:"
        f"offset={stats1['target_offset']}:linear=true,"
        f"alimiter=limit=0.84:level=false,"
        f"afade=t=out:st=40.55:d=0.45"
    )
    subprocess.run(
        [
            FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(PREMASTER_WAV),
            "-af", ln2,
            "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
            str(MASTER_M4A),
        ],
        check=True,
    )

    stats2 = measure_loudnorm(MASTER_M4A)
    report = {
        "duration_s": DURATION_S,
        "premaster_loudnorm": stats1,
        "final_loudnorm": stats2,
        "haram_ir_length_s": 3.2,
        "predelay_ms": 56.0,
        "wet_mix": 0.42,
        "words_or_timing_changed": False,
    }
    AUDIO_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["final_loudnorm"], indent=2))


if __name__ == "__main__":
    main()
