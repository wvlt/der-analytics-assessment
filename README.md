# Analytics Engineer Technical Assessment — DER Fleet Analytics

Welcome, and thanks for making time for this exercise.

You've been asked to imagine you're the new Analytics Engineer at **WestGen Energy**, a Western Australian generator and retailer with a growing Distributed Energy Resources (DER) portfolio: grid-scale batteries (BESS), solar farms, wind farms, and a Virtual Power Plant (VPP).

WestGen's Future Energy team currently receives raw telemetry from these assets but has no structured analytics layer. Your job is to build the first version of one — end to end — on **Databricks Free Edition**, and then present your work to the team.

---

## Time expectation

This task is designed to be completed in **about 4 hours**. You may spend longer if you wish, but we don't recommend it and it won't earn extra credit — part of what we're assessing is your ability to prioritise and make sensible trade-offs under a time constraint. **It is completely fine (and expected) to leave things unfinished or simplified — just be ready to explain what you'd do with more time.**

Suggested split (indicative only):

| Phase | Time |
|---|---|
| Setup + data generation + exploration | ~30 min |
| Data pipeline & modelling | ~90 min |
| KPIs & dashboard | ~60 min |
| Presentation prep | ~40 min |

---

## Setup

1. Sign up for [Databricks Free Edition](https://www.databricks.com/learn/free-edition) (free, no credit card). Free Edition comes with Unity Catalog enabled and a default catalog called `workspace`.
2. Set up your Unity Catalog structure first. Create a catalog `westgen` (or use the `workspace` catalog if you prefer — state your choice) containing schemas for your medallion layers and a **Volume** for landing the raw files, e.g.:
   ```sql
   CREATE CATALOG IF NOT EXISTS westgen;
   CREATE SCHEMA IF NOT EXISTS westgen.raw;
   CREATE VOLUME IF NOT EXISTS westgen.raw.landing;
   ```
3. Create a new notebook and run the provided script `data/generate_data.py` (copy its contents into a notebook cell, or upload it). It writes three CSV files into your landing Volume (edit `OUT_DIR` at the top if you named yours differently):
   - `asset_metadata.csv` — the DER asset register (~12 rows)
   - `telemetry.csv` — 5-minute interval telemetry for all assets over 14 days (~48,000 rows)
   - `market_prices.csv` — 30-minute wholesale energy prices for the same period
4. **Important:** the data is intentionally imperfect, in ways that are realistic for operational OT/SCADA and vendor data. Part of the task is finding and handling these issues. Document what you find.

---

## The task

### Part 1 — Pipeline & data model
Build a pipeline in Databricks that takes the three raw datasets through to clean, analysis-ready tables.

- Use a medallion architecture (bronze-silver-gold, or a justified variant) **implemented as governed Delta tables in Unity Catalog**, using the full three-level namespace (e.g. `westgen.bronze.telemetry` → `westgen.silver.telemetry` → `westgen.gold.fct_asset_performance`). DataFrames, temp views, and files on disk don't count as your layers — every layer must be a registered UC table another user could query by name. Structure it the way you would if this were the foundation of a real platform, but keep it proportionate to the time available.
- Add table/column comments or descriptions where they'd genuinely help a future user — treat the catalog as something a teammate inherits, not scratch space.
- Identify and handle the data quality issues you find. Keep a short log of what you found and what you decided to do about each (a markdown cell is fine).
- Produce a modelled analytical layer (e.g. fact/dimension tables or well-designed gold tables) that could support asset performance reporting across the fleet.

### Part 2 — KPIs
From your modelled layer, compute at least the following:

1. **Solar/wind capacity factor** per asset, daily and for the full period.
2. **BESS round-trip efficiency** per battery over the period.
3. **Asset availability** (% of expected intervals where the asset reported valid data) per asset.
4. **Estimated gross revenue** per asset: energy generated/discharged × the prevailing market price (state your assumptions — the granularity mismatch between telemetry and prices is deliberate).

Plus **one insight of your own choosing** — anything interesting you noticed in the data that you think the Future Energy team should know about.

### Part 3 — Dashboard
Build a dashboard (Databricks dashboards preferred; a well-organised notebook with visuals is acceptable) that surfaces fleet-level and asset-level performance. Think about your audience: an asset engineer and an executive will both look at this. You choose what goes on it — that choice is part of the assessment.

### Part 4 — Presentation (10 minutes)
Prepare a short presentation (max ~7 slides, any format — slides, or a well-structured notebook you talk through) covering:

1. **Your solution architecture** — a simple diagram of what you built, and a second view of how you'd evolve it into a production system at real scale (streaming SCADA feeds, AEMO data, ML models in the mix). Basic is fine; we're interested in your reasoning, not your diagramming.
2. Data quality issues found and decisions made.
3. Your data model and why you shaped it that way.
4. Key findings — the KPIs and your chosen insight.
5. How you used AI tools, if you did (see below).
6. What you'd do next with more time.

---

## The interview — nothing to submit

**There is no submission.** You'll receive this task roughly 24 hours before your interview. At the interview, you'll **share your screen** and:

1. Present your findings (~10 minutes, uninterrupted).
2. Walk us through your live Databricks workspace — your catalog, tables, notebooks, and dashboard — followed by a Q&A where we'll dig into your choices. Have your workspace open and ready; we may ask you to open specific queries, explain specific cells, or make small changes live.

## AI tools

You're free to use AI tools (Claude, ChatGPT, Copilot, Databricks Assistant, etc.) — we use them too. Two conditions:

- **Tell us how you used them** — which tools, for what parts, and what you changed or rejected from their output. This is part of your presentation, and honest, skilled AI use is a positive signal, not a negative one.
- **You must fully understand everything in your workspace.** The Q&A will test this, and "the AI wrote that part" is not an acceptable answer to a question about your own pipeline.

## What we're looking for

- **Technical depth** — sound pipeline design, correct SQL/Python, sensible modelling.
- **Critical thinking** — did you notice what's wrong with the data, and make defensible decisions?
- **Judgment & prioritisation** — a smaller thing done well beats a big thing done badly.
- **Communication** — can you explain your work to both engineers and executives?

You may use any resources you like, including AI tools — but you must fully understand and be able to defend every line of what you submit. The Q&A will test this.

Good luck — we're looking forward to seeing what you build.
