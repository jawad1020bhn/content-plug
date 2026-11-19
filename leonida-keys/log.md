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

## 2026-11-19 (launch day, session 2 — "real one")
- Stream/launch research via web tools: records + top streamers documented in facts.md / watchlist.md
- Footage hunt on allowed hosts: GitHub repos scanned for real video; found official trailer/postcard
  clips (9s total, 1080p) in tafsirulislamapon/Gta6GASP — downloadable via blobs API
  (tools/fetch_reel2_footage.sh). Leaked-content repos identified and SKIPPED (hard rule).
- Reel 2 (launch news) PRODUCED from REAL footage — media/edits/reel2_launch_news.mp4:
  24.9s, 1080x1920@30, -14 LUFS, plugin blur layout, cinematic slow-mo, crossfades,
  narrator VO (voice-00), synthwave bed, burned captions with verified numbers (7.91M / 99 /
  9.7M / 4.5M hrs). check.py PASS. Automated frame checks: hook box, captions, CTA, seams OK.
- Awaiting human "yes" to post
