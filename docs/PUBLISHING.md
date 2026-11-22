# PUBLISHING.md — captions, titles, credits per platform

Nothing here is posted automatically. This file only defines **what the text should be** so the
package in `metadata/<slot>/` can be pasted into each app without rewriting.

Post package for slot `NNN` lives in `metadata/NNN_<slug>/`:

| File | Purpose |
|---|---|
| `caption.txt` | the description you paste (includes credits, human-readable) |
| `credits.txt` | the plain credit block, for platforms that need it separately |
| `post.json` | machine-readable: title, description, hashtags, credits, rights notes, platform limits |
| `poster.png` | 1080×1920 cover frame (verified, no UI, no burned credits) |
| `qa.png` | 6-frame contact sheet used for the human review |

Deliverable MP4s live **only** in `outputs/`.

---

## Titles (YouTube / Facebook)

Pattern that works for this niche — verse promise, no clickbait, no numerals-as-emotion:

```
<Promise line> | Surah <Name> <ayah-range> | <Reciter short name>
```

Examples that fit the two delivered videos:

- `So remember Me, I will remember you | Surah Al-Baqarah 2:152-153 | Yasser ad-Dussary`
- `Seek help through patience and prayer | Surah Al-Baqarah 2:153 | Yasser ad-Dussary`
- `My Lord has made me blessed | Surah Maryam 19:30-33 | Mishari al-Afasy`

Keep ≤ 70 characters for the first clause if possible; YouTube truncates around 60–70 in search.
One emoji maximum, and only if it fits the tone (🌿, 🤍); never 🙏🏻-style emoji spam.

---

## Descriptions

YouTube / Facebook (long form, credits at the bottom under a divider):

```
<Surah name> <ayah-range> — recited by <reciter>.

<Arabic verse, one line per ayah — optional, omit if the visuals already carry it>

<English translation, verbatim, quoted>

Listen, save, and share if it helped.

—
Quran data provided by Quran Foundation.
Arabic: QPC Hafs / UthmanicHafs1Ver18 — King Fahd Glorious Quran Printing Complex (KFGQPC).
Translation: <edition name> (<edition id> / QuranEnc.com).
Reciter: <reciter>.
Timing: QF <endpoint>.
Fonts: KFGQPC Uthmanic Hafs + Cormorant Garamond (SIL OFL 1.1).
Background: <source, author, license or "user-supplied">.
Source: <quranenc verse link>

Rights: <rights note from credits.txt>
```

Instagram / TikTok: first line must stand alone (only ~2 lines show before "more"). Put credits after
the first 3 lines, and repeat the data credit in the first comment if the caption gets long.

---

## Hashtags

Per-platform, fixed sets so they can be pasted; rotate 3–4 between videos to avoid looking automated.

**Instagram (12–20 tags):**
```
#quran #quranrecitation #albaqarah #surahbaqarah #islamicreels #quranquotes #islam #muslim
#dhikr #sabr #patience #qurantranslation #reels #islamicquotes #yasseraddussary
```
(some platforms cap length; trim to the first 10 if needed)

**TikTok (4–8 tags):**
```
#quran #quranrecitation #islam #sabr #fyp
```

**YouTube (3–6 tags, in the tags field not the description):**
```
quran, surah al-baqarah, yasser ad-dussary, quran recitation with english translation, islamic shorts
```

**Facebook:** 2–4 tags only; hashtags underperform there.

Never invent trending tags, never use tags unrelated to the verse (engagement bait), never use a
reciter's name in a way that implies endorsement.

---

## Credits — the non-negotiable block

Copy verbatim from `credits.txt`. Two rules on top of it:

1. `Quran data provided by Quran Foundation.` appears **in every** caption, always.
2. Credit text is **never** burned into the video pixels.

Commercial rights caveats to keep attached to the package: QF Connected Apps says commercial use or
redistribution of licensed recitations may require a separate written content license; KFGQPC font
commercial release may require written approval. Surface this to the human at review time.

---

## Per-platform field map

| Field | YouTube Shorts | Instagram Reels | Facebook Reels | TikTok |
|---|---|---|---|---|
| Title | title field (≤100 chars) | not separate — first caption line | not separate | not separate |
| Description | full block + credits | caption + hashtags, credits after line 3 | full block | short caption + 4–8 tags |
| Cover | `poster.png` | `poster.png` | `poster.png` | `poster.png` |
| Aspect | 1080×1920 ✔ | 1080×1920 ✔ | 1080×1920 ✔ | 1080×1920 ✔ |
| Audio level | −14.5 LUFS ✔ | −14.5 LUFS ✔ | −14.5 LUFS ✔ | −14.5 LUFS ✔ |
| Length | ≤ 60 s for Shorts | ≤ 90 s recommended | ≤ 90 s | 15–60 s sweet spot |

All four are covered by the same single MP4 — it is already 9:16, ≤30 s, loudness-normalised and has
no burned UI or credits. Nothing needs re-exporting per platform.

---

## Approval gate

1. Show: MP4 path in `outputs/`, `caption.txt`, `credits.txt`, `poster.png`, `qa.png`.
2. State the rights caveats in one line.
3. Wait for an explicit **"yes"**. Then, and only then, does the human post — the agent does not
   upload to any platform from this repo.
4. After posting, fill the tracker row in `CATALOG.md` with the real URL and, later, real numbers.
