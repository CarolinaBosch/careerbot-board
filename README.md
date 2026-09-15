# CareerBot Job Board

Static dashboard of Carolina Bosch's job-search pipeline, published via GitHub Pages
so it can be opened from an iPhone.

**This page is read-only.** All application decisions happen in Telegram with CareerBot.
CareerBot never applies to a role without explicit per-role approval.

## Contents

| Path | Purpose |
| --- | --- |
| `build.py` | Generates `site/index.html` from the two data inputs |
| `applications.json` | Snapshot of Supabase `public.job_applications` (source of truth) |
| `site/index.html` | The published page |

The numbered shortlist is read from `../current-shortlist.md` in the Obsidian vault
(`Carolina Personal/Career/`) and is not committed to this repo.

## Rebuild

```sh
python3 build.py
git add -A && git commit -m "refresh dashboard" && git push
```

GitHub Pages redeploys within about a minute.

## Data boundaries

Published: company, role, location, salary range, posting link, status.

Never published: resume files, cover letters, contact details, passwords,
verification codes, government IDs, or the free-text application notes stored
in Supabase.
