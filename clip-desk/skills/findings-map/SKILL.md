---
name: findings-map
description: Build and post a verified map of lesser-known finds in the niche — places, products, techniques, resources, tips, hidden details — taken from creator videos and checked before posting. Use when the user wants a "hidden gems" list, evergreen tip posts, or says scan a video for finds.
---

# Findings map

A database of every good, checkable find in the niche: a hidden spot, a product worth buying, a technique that
works, a resource nobody mentions, a detail everyone missed. Each row is verified before it becomes content.

Entries live in `secrets.csv` (id, category, name, where, how, source_channel, source_url_with_timestamp,
found_on, status, verified_by, notes). Categories: `place`, `money`, `product`, `collectible`, `easter_egg`,
`technique`, `resource`, `other`. Status: `unverified`, `verified`, `wrong`.

## Commands

Run from the project folder with `.venv/bin/python scripts/secrets_map.py ...` (`--csv path` before the
subcommand to use another file).

- `scan jobs/<id>`: reads `transcript.json` and `info.json`, finds find-type mentions (hidden, secret, rare,
  tip, trick, method, recipe, workflow, resource, deal) and adds them as `unverified` with a quote and a `?t=`
  link to the source. Duplicates are skipped. Exploit-type mentions are skipped and printed.
- `add --name N --where W --how H --category place --channel C --url U`: manual entry.
- `verify <id> --by "<who/how>"`: only after the find was checked for real (used, visited, tested) or confirmed
  by a primary source. Needs where, how and source channel filled in.
- `wrong <id>`: the find did not hold up.
- `posts --out findings-posts.md --topic "<niche>"`: HOW TO tip and Spotlight drafts per verified entry, plus a
  "5 finds in [niche]" carousel outline when 3 or more are verified.
- `map --out findings.md`: table grouped by category.

## Flow

1. `scan` a transcribed video. Open each `?t=` link, read the quote, and rewrite the auto name/where/how in
   `secrets.csv` into a real tip.
2. Check it yourself. `verify` or `wrong`.
3. `posts --topic "<niche>"`, then run `rule-check` on the drafts before they go out.

## Rules

1. Post verified entries only. Unverified is a lead, not a fact.
2. Credit the finder on every post (`🎥 channel` plus the timestamp link). Never present a creator's find as ours.
3. No exploits, hacks that break a platform's rules, stolen or paywalled material, leaks or "play early" content.
   The script refuses them; do not work around it.
4. Scan output is a transcript guess. Rewrite the name, where and how by hand; do not post the raw quote.
5. No spoilers for a story, finale or launch reveal. Never imply the page is the brand it covers. Use the niche's
   natural search term. X posts have no hashtags.
