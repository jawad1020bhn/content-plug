<div align="center">

<img src="docs/logo.svg" width="140" alt="clip-desk logo">

<h1 align="center">clip-desk</h1>

<p align="center"><b>Pick a niche.<br>The desk does the rest.</b></p>

<p align="center">A faceless content page is a job of a thousand small decisions. Clip Desk is the tool layer: it finds what is trending in your niche, catches the moment, and cuts a captioned vertical clip ready to post. Campaigns can pay per 1,000 views. You just hit post.</p>

<p align="center"><img src="https://img.shields.io/badge/skills-19-4f7cff" alt="skills: 19"> <img src="https://img.shields.io/badge/clips-1080x1920-4f7cff" alt="clips: 1080x1920"> <img src="https://img.shields.io/badge/languages-12-4f7cff" alt="languages: 12"> <img src="https://img.shields.io/badge/license-MIT-4f7cff" alt="license: MIT"></p>
<p align="center"><sub>Independent project. Not affiliated with any brand, publisher, platform or Anthropic.</sub></p>

</div>

```
/plugin marketplace add <your-org>/clip-desk
/plugin install clip-desk@clip-desk
```

Two lines. In 10 minutes you have: the tools installed, your page folder, today's trending videos in your niche,
the best moments picked and your first vertical clips ready to post.

## Any niche, one desk

Clip Desk was grown out of a single-fandom clipping page and generalized: nothing in it assumes a game, a
franchise or a launch date. Your niche is an input.

- **Games and esports** — gameplay moments, patch news, reaction clips.
- **Cooking and food** — technique tips, recipe tests, reaction clips to viral cooking.
- **Tech and gear** — reviews, comparisons, "the setting nobody changes".
- **Sport and fitness** — highlights, form tips, event-day clips.
- **Music and culture** — live moments, release reactions, throwbacks.
- **Crafts, hobbies, finance, education, fandom** — anything with creators, sources and a search term.

Set three values once, per page:

```
CLIP_DESK_TOPIC="<the niche in the words people search>"
CLIP_DESK_SUBS="<2-4 subreddits where the audience talks>"
CLIP_DESK_HASHTAGS="<4-6 niche tags>"
```

## First run: paste this into Claude Code

```
Use clip-desk. Ask me your questions in one message (page name, niche and topic, platforms, angle, time zone),
then do everything after one "yes": find live clipping campaigns that fit my niche, show today's trending videos
and live streams for my topic, find the best moments in the top one, cut my first 3 clips with hooks, check them
against the campaign rules, and tell me what to post where.
```

## Two ways to make money

**1. Paid clipping campaigns (fastest).** Creators and brands pay clippers per 1,000 views on approved clips.
On Whop Content Rewards around $1 per 1K views is common; every campaign shows its own rate, budget left and
rules. `campaign-finder` reads them live and never guesses a number. You read the rules, clip only that creator,
post, submit the link.

**2. Your own faceless page (bigger, slower).** The built-in playbook runs it: daily content mix, credit rules,
caption templates, the "be first" plan for your niche's next big moment, and a learning loop. Platforms don't pay
for reposted clips, so the page grows on speed, useful tips and credited clips, then earns through campaigns and
partnerships.

No income is promised. Your result depends on speed, picks and hooks, and the scoreboard shows what works.

## The rules that make clips win

- Hook in the first second. Say why to keep watching ("the setting nobody changes").
- 7 to 30 seconds. Cut dead air at the start, end on the payoff.
- Big captions in the safe area. Most people watch muted.
- Make it yours: hook, tip, commentary. Never a plain re-upload. Credit the creator in your post.
- Event day: post to X first, then Reels, TikTok and Shorts, every 1 to 2 hours for 48 hours.
- Every repeated question in your comments becomes a HOW TO post.
- One test per day. No verdict before 24 hours, prefer the 72 h numbers.

## What's inside

| Skill | What you get |
|---|---|
| `setup` | Installs ffmpeg, yt-dlp and faster-whisper, asks 5 questions, builds your page folder |
| `campaign-finder` | Live campaigns in your niche: rate per 1K views, budget left, rules, link |
| `trend-radar` | Videos on your topic from the last 24 h ranked by views per hour |
| `stream-finder` | Who is streaming your topic right now (YouTube, Twitch, Kick), ranked by viewers |
| `moment-finder` | Best 15 to 40 s moments, scored by loudness spikes, hype words, YouTube "most replayed" and chat spikes |
| `live-mode` | Records a live stream and cuts a clip every time chat explodes |
| `reaction-clips` | Reaction clips like the viral ones: the presenter's face on top, the footage below, a big title on the seam. Finds top streams with no account, reads chat, finds the webcam by itself |
| `clip-cutter` | 1080x1920 clip: word-by-word captions, hook box, -14 LUFS. Fill, blurred background, facecam or react |
| `hook-writer` | 3 hook options per clip |
| `rule-check` | Length, format, hashtags and banned content checked before you post |
| `multilang` | One clip in 12 languages: translated word-by-word captions and hook, optional stock-voice hook |
| `dewatermark` | Strips a burned-in watermark from **your own** old footage before reposting (alpha unblend, delogo, crop); `--rights` required |
| `caption-removal` | Removes captions from **your own** clip: subtitle tracks losslessly in seconds, burned-in text with a neural inpainter (VSR/LaMa, external, ~3.6 s/frame on CPU); `--rights` required |
| `quran-subtitles` | Verified Quran recitation captions: canonical QPC Hafs Arabic, one named translation, exact QF/QUL timing, RTL-safe ASS/libass and bundled KFGQPC + Cormorant fonts; human QA required |
| `questions-to-posts` | Pulls repeated questions from your niche's subreddits and your comments, turns the answered ones into HOW TO posts |
| `findings-map` | Builds a database of verified finds (places, products, techniques, resources) from clips, with timestamp and credit. Verified ones become evergreen tip posts |
| `reference-cards` | Turns a sourced reference sheet (codes, shortcuts, ratios, charts) into a 4-slide carousel, with statuses |
| `playbook` | Your full daily routine and event-day plan |
| `learning-loop` | Scoreboard, one test per day, payouts from real numbers only |

Nothing is uploaded automatically. You approve every post.

## Hard rules

No leaks, no "play early" or "free download" posts, no piracy or stolen/paywalled material, no exploits that break
a platform's rules, no fake news, never pretends to be the brand. Every fact needs a primary or named source.
For Quran recitation use `quran-subtitles`, never generic ASR or machine translation; keep raw API data out of the
repo and put QF/translation/reciter/creator credits in the post caption, not in the video pixels.

## Run the scripts yourself

```
pip install -r requirements.txt
python scripts/trends.py --query "your topic" --hours 24
python scripts/streams.py --query "your topic"
python scripts/moments.py "https://www.youtube.com/watch?v=..." --top 8
python scripts/cut.py jobs/<id> --pick 2 --layout facecam --hook "Nobody noticed this"
python scripts/check.py jobs/<id>/edits/clip_2.mp4 --campaign campaigns.md
python scripts/dewatermark.py old.mp4 --out clean.mp4 --rights own --calibrate 2:40,840,352,40
python scripts/remove_captions.py old.mp4 --detect              # where are the captions?
python scripts/remove_captions.py old.mp4 --rights own --vsr-home ~/vsr
python scripts/quran_subtitles.py --selftest             # font/timing smoke test, no network
python scripts/quran_visual.py --background assets/<reel>/bg.mp4 --out jobs/<id>/visual.mp4 --duration 43.4
python scripts/live.py "https://www.youtube.com/watch?v=<live>" --minutes 60
```

Windows, macOS or Linux, Python 3.10+. An NVIDIA GPU makes transcription faster; on the CPU a 12-minute video
takes about 5 minutes.

MIT license. Originally forked from an MIT-licensed fan project; all fandom-specific content replaced with
generic, niche-agnostic tooling.
