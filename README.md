# cems-eia-crosswalk

An agent skill and a small offline checker for anyone joining EPA CEMS (CAMPD) emissions units to EIA-860/923 plants and generators, for example through PUDL's `core_epa__assn_eia_epacamd` crosswalk.

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no person has checked the listed rows against the plants. Code and skill: Apache-2.0. Tables: CC BY 4.0 (derived from PUDL, CC BY 4.0, Catalyst Cooperative, and Open Grid Emissions' manual crosswalk, MIT).

## What is in it

- [`skills/cems-eia-crosswalk/SKILL.md`](skills/cems-eia-crosswalk/SKILL.md) (0.2.2): tells coding agents (Claude Code, Codex, Cursor and others) the known traps in the crosswalk: unmatched units dropped silently, PUDL's 3-year trailing window for yearly CEMS values (which keeps retired units), retired plants that drop out of PUDL's annual EIA-860 years and come back in the EIA-860M year, whole combined-cycle blocks with no row, steam generators folded onto gas turbines, links to much smaller generators, EPA-only 88xxxx plant ids, and how to rebuild the EPA side of EPA's crosswalk from EPA's public yearly files now that the FACT API is gone. It also says how to run the checker and how to explain what it finds.
- [`check_units.py`](skills/cems-eia-crosswalk/check_units.py) 0.2.0: standard-library Python, no network. Give it a CSV with `plant_id_epa`, `emissions_unit_id_epa` (and optionally `report_year`). It flags units that hit a known problem.
- [`known_issues.csv`](skills/cems-eia-crosswalk/known_issues.csv): 19 crosswalk rows that are missing or point at the wrong generator, with candidate EIA generators.
- [`gap_units_2018_2024.csv`](skills/cems-eia-crosswalk/gap_units_2018_2024.csv): 317 unit-years (2018-2024) with CEMS load, no crosswalk row and no unlinked operating EIA generator to link to.
- [`gap_retirement_2018_2024.csv`](skills/cems-eia-crosswalk/gap_retirement_2018_2024.csv) (new in 0.2.0): for the 228 of those unit-years whose EIA plant had no EIA-860 generator row or no operating one, whether all of the plant's combustion generators had retired before the report year, the plant's last EIA-860 listing and the latest retirement year. In 2024, 33 of 65 such units are at plants that retired in 2022 or 2023.

Every row comes from a pre-registered check of PUDL nightly builds (5-8 November 2026) or of EPA's public bulk files (10 November 2026). Each plan was published before its data was read, and the results are in [munimtechnologies/eia860m-slip](https://github.com/munimtechnologies/eia860m-slip): `docs/xwpair.md`, `docs/ccsplit.md`, `docs/ccsub.md`, `docs/xwdev.md`, `docs/xwpudl.md`, `docs/xwgap.md`, `docs/xwstale.md`, `docs/xwback.md`, `docs/xwtz.md`, `docs/easeyx.md` and `docs/easeyx2.md`. The structural problems are reported upstream in [catalyst-cooperative/pudl#5752](https://github.com/catalyst-cooperative/pudl/issues/5752).

## Use

As an agent skill:

```
npx skills add munimtechnologies/cems-eia-crosswalk
```

Or directly:

```
git clone --depth 1 --branch v0.2.2 https://github.com/munimtechnologies/cems-eia-crosswalk
python cems-eia-crosswalk/skills/cems-eia-crosswalk/check_units.py units.csv --year 2024
```

Options: `--json` for machine-readable output; `--fail-on-hit` exits 1 if anything is flagged, for CI.

Tests: `python -m unittest -v test_check_units`.

## Changes

- 0.2.2 (10 November 2026): SKILL.md only; the checker and tables are unchanged. New trap 10: EPA's camd-eia-crosswalk took its EPA side from the FACT API, which no longer works. From pre-registered checks easeyx-1 and easeyx-2 (`docs/easeyx.md`, `docs/easeyx2.md`): EPA's public yearly facility files 2010-2024, stacked and deduplicated on (plant, unit, generator), hold 98.1% of the 2024 build's keys (one year's file 74.5%); the latest row gives the same state, coordinates and capacity for every comparable key and the same fuel for 99.77%; and the files' own retirement year, else the last year a unit appears, gives the build's retirement year for 92.6% of retired keys.
- 0.2.1 (9 November 2026): SKILL.md only; the checker and tables are unchanged. Trap 2 now gives the result of pre-registered check xwback-1 (`docs/xwback.md`): of 1,350 plants that became fully retired in 2002-2021, 63% drop out of PUDL's annual EIA-860 years before 2024 and 97% are listed again in report year 2026 (filled from EIA-860M), so absence from EIA-860 is not proof of anything; Astoria's undated generator CTG01 is a cancelled planned unit. Trap 7 adds the clean result of pre-registered check xwtz-1 (`docs/xwtz.md`): every CEMS unit of PUDL's yearly table in 2018-2024 resolves to an EIA plant with a timezone, so the hourly UTC times there do not borrow another plant's offset. The fallback when the skill's files are missing now names the files instead of pointing at a download.
- 0.2.0 (8 November 2026): adds `gap_retirement_2018_2024.csv` and the fields `retirement_class`, `last_eia860_listing` and `latest_retirement_year` on absent and not_operating gap findings (from pre-registered check xwstale-1); trap 2 in SKILL.md now says which 2024 gap units are retired plants; SKILL.md no longer tells agents to download anything (the files ship in the skill folder).
- 0.1.0 (8 November 2026): first release.

## Limits

Findings are leads, not diagnoses. PUDL rebuilds nightly, so a listed row may already be fixed in a newer build. A clean result only means none of these known rows matched. A retirement date in EIA-860 is what the plant reported, not proof the unit stopped burning fuel. Trap 10 compares only the EPA side with the 2024 build; the EIA side and the matching steps were not compared. Nobody at Catalyst Cooperative, EPA or Singularity Energy has reviewed these results.
