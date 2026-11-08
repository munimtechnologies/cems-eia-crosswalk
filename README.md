# cems-eia-crosswalk

An agent skill and a small offline checker for anyone joining EPA CEMS (CAMPD) emissions units to EIA-860/923 plants and generators, for example through PUDL's `core_epa__assn_eia_epacamd` crosswalk.

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no person has checked the listed rows against the plants. Code and skill: Apache-2.0. Tables: CC BY 4.0 (derived from PUDL, CC BY 4.0, Catalyst Cooperative, and Open Grid Emissions' manual crosswalk, MIT).

## What is in it

- [`skills/cems-eia-crosswalk/SKILL.md`](skills/cems-eia-crosswalk/SKILL.md): tells coding agents (Claude Code, Codex, Cursor and others) the known traps in the crosswalk: unmatched units dropped silently, PUDL's 3-year trailing window for yearly CEMS values, whole combined-cycle blocks with no row, steam generators folded onto gas turbines, links to much smaller generators, EPA-only 88xxxx plant ids. It also says how to run the checker and how to explain what it finds.
- [`check_units.py`](skills/cems-eia-crosswalk/check_units.py) 0.1.0: standard-library Python, no network. Give it a CSV with `plant_id_epa`, `emissions_unit_id_epa` (and optionally `report_year`). It flags units that hit a known problem.
- [`known_issues.csv`](skills/cems-eia-crosswalk/known_issues.csv): 19 crosswalk rows that are missing or point at the wrong generator, with candidate EIA generators.
- [`gap_units_2018_2024.csv`](skills/cems-eia-crosswalk/gap_units_2018_2024.csv): 317 unit-years (2018-2024) with CEMS load, no crosswalk row and no unlinked operating EIA generator to link to.

Every row comes from a pre-registered check of PUDL nightly builds (5-8 November 2026). Each plan was published before its data was read, and the results are in [munimtechnologies/eia860m-slip](https://github.com/munimtechnologies/eia860m-slip): `docs/xwpair.md`, `docs/ccsplit.md`, `docs/ccsub.md`, `docs/xwdev.md`, `docs/xwpudl.md` and `docs/xwgap.md`. The structural problems are reported upstream in [catalyst-cooperative/pudl#5752](https://github.com/catalyst-cooperative/pudl/issues/5752).

## Use

As an agent skill:

```
npx skills add munimtechnologies/cems-eia-crosswalk
```

Or directly:

```
git clone --depth 1 --branch v0.1.0 https://github.com/munimtechnologies/cems-eia-crosswalk
python cems-eia-crosswalk/skills/cems-eia-crosswalk/check_units.py units.csv --year 2024
```

Options: `--json` for machine-readable output; `--fail-on-hit` exits 1 if anything is flagged, for CI.

Tests: `python -m unittest -v test_check_units`.

## Limits

Findings are leads, not diagnoses. PUDL rebuilds nightly, so a listed row may already be fixed in a newer build. A clean result only means none of these known rows matched. Nobody at Catalyst Cooperative, EPA or Singularity Energy has reviewed these results.
