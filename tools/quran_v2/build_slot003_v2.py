#!/usr/bin/env python3
"""Restyle the original Al-Kahf waterfall cut using the Slot 009 v5 layout."""
import json
import subprocess

import numpy as np

import build_video_template as card
from card_atmosphere import atmosphere

SLOT = '003_al-kahf_18-107-108_ali-jaber'
ASSETS = card.ROOT / 'assets' / 'quran' / SLOT
JOB = card.ROOT / 'jobs' / f'{SLOT}_v2'
V1 = card.ROOT / 'outputs' / f'quran-{SLOT}_en_1080x1920_v1.mp4'
V2 = V1.with_name(V1.name.replace('_v1.mp4', '_v2.mp4'))
SHIFT_Y = 103
FRAME_COUNT = 574


def setup():
    beats = json.loads((ASSETS / 'beats003.json').read_text())['beats']
    card.BEATS = beats
    card.BEAT_STARTS = [b['start'] for b in beats]
    card.AYAH_SPANS = [('18:107', beats[0]['start'], beats[1]['end']),
                       ('18:108', beats[2]['start'], beats[2]['end'])]
    card.TOTAL_FRAMES = FRAME_COUNT
    card.DURATION_S = FRAME_COUNT / card.FPS
    card.REC_START_S, card.REC_END_S = beats[0]['start'], beats[-1]['end']
    card.POP_W, card.POP_H, card.POP_X, card.POP_Y, card.POP_R = 860, 1106, 110, 224, 64
    # Unlike the train-window pin, the waterfall is near the middle of the source.
    card.CROP_CENTER_Y = 0.44
    card.HEADER_TEXT = 'Surah Al-Kahf'
    card.HEADER_ANCHOR_Y = 228
    card.ARABIC_SIZE = 80
    card.ARABIC_Y, card.ENGLISH_Y = (1435, 1390), (1610, 1520)
    card.REF_Y, card.FILAMENT_Y = 1740, 1810
    card.KEN_BURNS_GROWTH = 0.020
    card.MOTE_SEED = card.GRAIN_SEED = 2026009
    card.BACKGROUND_EFFECTS = atmosphere()
    (card.PIN_CLIP,) = (ASSETS / 'pinterest').glob('008_*_w89.mp4')
    card.VISUAL_BASE = JOB / 'visual_base.mp4'
    card.ASS_PATH = JOB / 'captions.ass'
    card.HEADER_ASS = JOB / 'header.ass'
    card.HEADER_PNG = JOB / 'header.png'
    card.ENV_NPY = JOB / 'env.npy'


def render():
    setup()
    JOB.mkdir(parents=True, exist_ok=True)
    # Keep the original polished AAC; read the dry trim only to drive the halo.
    pcm = subprocess.check_output([card.FFMPEG, '-v', 'error', '-i', str(ASSETS/'recitation_raw.m4a'),
                                   '-ac', '1', '-ar', '44100', '-f', 'f32le', '-'])
    frame_audio = np.frombuffer(pcm, dtype=np.float32)[:FRAME_COUNT * 1470].reshape(FRAME_COUNT, 1470)
    rms = np.sqrt(np.mean(frame_audio**2, axis=1))
    envelope = np.empty_like(rms)
    value = 0.0
    for i, level in enumerate(rms):
        value += (.38 if level > value else .14) * (level - value)
        envelope[i] = value
    np.save(card.ENV_NPY, np.clip(envelope / (np.percentile(envelope, 95) or 1), 0, 1))
    card.write_captions_ass()
    card.render_visual_base()
    filt = (f'ass=filename={card.ff_escape(card.ASS_PATH)}:fontsdir={card.ff_escape(card.FONT_DIR)}:shaping=1,'
            f'format=yuv444p,pad=1080:{1920+SHIFT_Y}:0:0:color=black,crop=1080:1920:0:{SHIFT_Y}:exact=1')
    subprocess.run([card.FFMPEG, '-v', 'error', '-y', '-i', str(card.VISUAL_BASE), '-i', str(V1),
                    '-map', '0:v:0', '-map', '1:a:0', '-vf', filt, '-c:v', 'libx264', '-crf', '18',
                    '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart',
                    str(V2)], check=True)
    print(V2, flush=True)


if __name__ == '__main__':
    render()
