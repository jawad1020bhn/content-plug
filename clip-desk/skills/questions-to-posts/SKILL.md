---
name: questions-to-posts
description: Turn repeated audience questions (subreddit threads and comments on our own posts) into HOW TO post drafts. Use when the user asks what people are asking, wants HOW TO ideas, or says to turn comment questions into posts.
---

# Questions to posts

Finds the questions the audience keeps asking, checks whether `facts.md` answers them, and drafts HOW TO posts from verified facts only. Works in any niche: the subreddits and the topic name are inputs.

## Command

Run from the page folder (where `facts.md` lives):

```
python scripts/questions.py --subs <subreddit,subreddit> --topic "<niche>" --days 3 \
  [--comments comments.txt] --out questions.md
```

- `--subs`: the subreddits where the audience actually talks about this niche (or set `CLIP_DESK_SUBS`).
  Ask the human if you do not know them; do not guess a community.
- `--topic`: the niche name used in draft titles, e.g. `"Sourdough"` -> `HOW TO FIX A SOGGY LOAF IN SOURDOUGH`
  (or set `CLIP_DESK_TOPIC`). Without it the draft has a `[TOPIC]` placeholder to fill by hand.
- `--comments comments.txt`: comments pasted from our own posts, one per line.
- `--facts facts.md` (default), `--ideas idea-bank.md` (default), `--top 25`, `--min-count 1`.
- Uses public Reddit JSON, 1 request per second, waits and retries on 429. If Reddit blocks it, paste comments into `comments.txt` and run again.

## What you get

- `questions.md`: clusters ranked by count then upvotes. Each has the canonical question, count, example links, and either `answer found in facts.md: <line>` or `UNANSWERED: needs an authoritative source`.
- Below the clusters: a HOW TO draft per answered cluster, in the playbook template (`HOW TO [DO THE THING] IN [TOPIC]`, numbered steps).
- `idea-bank.md`: every unanswered cluster is appended as a research task.

## After the run

1. Read each draft. The script copies steps from `facts.md` lines; it cannot judge order or whether a line is really a step. Fix order, trim to 3 to 5 steps, keep the wording true to the fact.
2. For each unanswered cluster, find an authoritative source (the primary/official one where it exists) and add
   it to `facts.md` with the link, then rerun.
3. Run `rule-check` on the final text, then post. Same-day turnaround for repeated questions beats polish.

## Rules

1. Facts only from authoritative sources — the official/primary source for the niche (the brand, publisher,
   standards body, documentation) or a named publication — logged in `facts.md` with the link. Recheck anything
   older than 48 hours.
2. Never invent steps, numbers, dates, prices or menu names. No source, no step. An unanswered question stays a
   research task.
3. No leaked, stolen, paywalled or pirated material, and no exploits that break a platform's rules, even if the
   audience asks for them. Skip those clusters. Rumors stay out unless the human approves one, clearly labeled.
4. Credit: if a post builds on someone's clip or find, credit with `🎥 @creator`. Do not quote or name Reddit
   users; the questions are only a signal of what to cover.
5. Never imply the page is the brand, publisher or platform it covers. Use the niche's natural search term.
6. Keep all-caps to the hook line only.
