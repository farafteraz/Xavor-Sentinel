# Xavor Sentinel

Sentinel supplies weekly research for Xavor. The revised brief treats specialist
service experience, buyer questions, research, and external developments as
separate evidence sources. It includes competitive LinkedIn content analysis
covering both messages and execution.

## Research changes

- The audience is the confirmed 50–1,000-employee company segment. Platform and
  specialist services retain their commercial priority; AI supports positioning.
  Data engineering and BI can stand alone.
- No minimum section counts, mandatory calendar ideas, or per-item content titles.
  A quiet week can produce fewer findings. Sentinel does not invent Xavor service
  packages, certifications, prices, clients, or product readiness.
- The previous six digest files supply a bounded title/URL memory. Dates at or
  after the research end date are excluded. Revisited topics need a substantive
  difference, and the output explains it. This is prompt-level novelty assessment,
  not a deterministic guarantee of deduplication or a complete publication history.
- LinkedIn observations record company/author, post link, observed date, access,
  argument, reader, hook, structure, format, proof, CTA, and visible presentation.
  Unseen slides or videos remain unobserved. Patterns must cite examples, and
  performance cannot be inferred from follower or reaction counts.
- `competitive-watchlist.json` records the user-named peers Tkxel, Systems Limited,
  and Devsinc. Service-selling references are separately seeded from Razorleaf,
  Coastal, INRY, and a Systems regional post. The actual post must explain or sell
  a service; company updates do not qualify automatically. Examples and access
  limits live in `competitive-reference-samples.json`. These are an initial
  reference set, not a representative feed audit or proven performance ranking.

Prompts live in `prompts/research-system.md` and `prompts/research-cycle.md`.
Historical digests remain unchanged. The monthly engine reads digest Markdown;
its reference IDs are assigned during ingestion, not by Sentinel.

## Safe preview

```bash
python sentinel.py --prepare-only --output-dir work/prepared
python -m unittest discover -s tests -v
```

These commands need no API key or email credentials and send nothing.

For an explicitly requested live research preview:

```bash
pip install anthropic
python sentinel.py --no-email --as-of 2026-09-30 --output-dir work/preview
```

This needs `ANTHROPIC_API_KEY` and makes paid research calls. It sends no email.
A fresh output directory avoids overwriting a prior digest. `--as-of` sets the
research window, not access to historical web snapshots; retrospectively found
material must preserve its original publication date.

The existing scheduled command still emails using the configured credentials.
Changes on `research-inputs-v2` do not affect the schedule until merged to main.
The validation workflow runs offline tests only. No new live research or email
was sent while implementing this revision.

## Remaining evidence gaps

The new prompt can collect accessible public competitive examples. It cannot
reliably inspect private LinkedIn posts, unseen media, or unavailable performance
analytics. Those require accessible exports or specific source material. A small
public sample must not be reported as a sector-wide benchmark. Practitioner
experience and Xavor's actual cross-account buyer questions remain separate
research inputs; competitor language is not a substitute for them.
