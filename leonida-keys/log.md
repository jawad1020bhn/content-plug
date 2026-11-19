# Log

## 2026-11-19 (launch day)
- Environment rebuilt on branch arena/ed5419c1-stream-plug (setup.sh: venv + ffmpeg OK)
  - ffmpeg upgraded to v9.0.2 via imageio-ffmpeg wheel (old 2018 static lacked xfade); setup.sh updated accordingly
- Page folder scaffolded: Leonida Keys / @LeonidaKeysHQ
- LESSON (critical): the platform snapshot respects .gitignore — the first render of Reel 1
  (in gitignored media/) was lost between turns. .gitignore fixed: media/edits is now tracked;
  only jobs/, media/raw/, media/official/ stay ignored. Reel rebuilt from regenerated assets.
- Reel 1 (launch welcome) PRODUCED & rule-check PASS:
  media/edits/reel1_leonida_keys.mp4 — 19.9s, 1080x1920@30, -14 LUFS
  4 AI concept images (Ken Burns + crossfades) + narrator VO (voice-00) + synthwave bed + burned captions
  Facts used: launch day, story starts in Leonida Keys (Jason Duval), Florida Keys basis, Key Lento stilt houses
- Awaiting human "yes" to post
