# Font notice and provenance

Two font binaries are bundled in `../fonts/`. They are **unmodified bytes**; the Cormorant file was renamed from
`CormorantGaramond[wght].ttf` to `CormorantGaramond-wght.ttf` only to avoid shell/URL bracket escaping. No font was
subsetted, converted, merged or edited. License texts live in this directory, separate from `../fonts/`, because
libass tries to load every file in a `fontsdir` and warns on non-font files.

## Arabic: KFGQPC HAFS Uthmanic Script

- File: `UthmanicHafs1Ver18.ttf`
- SHA-256: `a0636e68e375af9552470d67773936f54d536e6586ce2608311b2fe7f9cbec3a`
- Internal ASS family name: `KFGQPC HAFS Uthmanic Script`
- Official QF CDN path documented by [QF font rendering](https://api-docs.quran.com/docs/tutorials/fonts/font-rendering/):
  `https://verses.quran.foundation/fonts/quran/hafs/uthmanic_hafs/UthmanicHafs1Ver18.ttf`
- Raw bytes in this checkout came from a public GitHub mirror of that QF-documented file:
  [mashaleye/SurahSpot](https://github.com/mashaleye/SurahSpot/blob/main/public/fonts/UthmanicHafs1Ver18.ttf).
  The internal family name, RTL shaping and harakat were verified with `fontTools`, libass, FriBidi and HarfBuzz in
  this workspace. The QF CDN path is recorded as the canonical upstream source.
- EULA: [`LICENSE-KFGQPC.txt`](LICENSE-KFGQPC.txt), a copy of the KFGQPC electronic end-user license agreement from
  [this public mirror](https://github.com/abofahad506/-quran-uthmani-text/blob/main/fonts/LICENSE-KFGQPC.txt).
  Official publisher: [fonts.qurancomplex.gov.sa](http://fonts.qurancomplex.gov.sa/).
- Summary: © 2010 King Fahd Glorious Quran Printing Complex. The EULA grants free use/copy/distribution subject
  to conditions, forbids sale, modification, alteration, translation, reverse engineering, decompilation and
  disassembly, and provides the font "AS IS". Its opening paragraph also says reproduction needs written approval;
  for a public or commercial production release, re-download from the official QF/KFGQPC source and obtain written
  clarification if needed. Credit KFGQPC / Quran Foundation in the post caption. Do not rely on npm/CDN mirror
  `ISC` package metadata as authoritative; the font EULA governs.

## English: Cormorant Garamond

- File: `CormorantGaramond-wght.ttf` (original name `CormorantGaramond[wght].ttf`)
- SHA-256: `b20b7d9626dd956b2c5e558692ad328b1f19e3275e2782db4fa07670d83f35e0`
- Internal ASS family / named instance: `Cormorant Garamond Light`
- Source: [Google Fonts `ofl/cormorantgaramond`](https://github.com/google/fonts/tree/main/ofl/cormorantgaramond),
  variable TTF from the [Git blob API](https://api.github.com/repos/google/fonts/git/blobs/d992a83ce525c330fad3a19087746bcb2dc038ee).
- License: [`OFL-CormorantGaramond.txt`](OFL-CormorantGaramond.txt), SIL Open Font License 1.1,
  © 2015 the Cormorant Project Authors. OFL permits bundling and use with the license text included; respect the
  reserved font name rules if the font itself is modified (we did not modify it).

## Quran data / credit

Bundling the fonts is not a redistribution of QF/QUL API data. Raw API JSON, generated ASS/SRT containing Quran
text, and fetched timing payloads must remain in ignored job folders. For social videos using QF data, credit
"Quran data provided by Quran Foundation." plus the named translation, reciter, KFGQPC, and creator/background in
the post caption/description. See [QF Developer Terms](https://api-docs.quran.com/legal/developer-terms/) and
[Connected Apps](https://api-docs.quran.com/docs/connected-apps/). Never burn credit text into the video.
