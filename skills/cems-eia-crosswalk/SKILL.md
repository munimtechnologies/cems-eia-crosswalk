---
name: cems-eia-crosswalk
description: Use when joining EPA CEMS / CAMPD emissions units to EIA-860 or EIA-923 plants and generators, especially through PUDL's core_epa__assn_eia_epacamd crosswalk or EPA's camd-eia-crosswalk, or when CEMS units go missing after the join, combined-cycle emissions or emission rates look wrong, or a retired plant still shows up in a recent year. Explains the known traps (unmatched units dropped silently, PUDL's 3-year trailing window, whole combined-cycle blocks with no row, steam generators folded onto gas turbines, links to much smaller generators, EPA-only 88xxxx plant ids) and runs an offline, standard-library checker that flags the user's units against 19 known problem rows and 317 gap unit-years, with whether each gap unit's plant had already retired, found by pre-registered checks of PUDL nightly builds (November 2026).
license: Apache-2.0
---

# CEMS to EIA crosswalk traps

By MV2 of Munim, Inc. (mv2@munimtech.com), from github.com/munimtechnologies/cems-eia-crosswalk (version 0.2.0). This skill and its checker were made with AI agents working in MV2's name. Skill and checker: Apache-2.0. The three tables: CC BY 4.0, derived from PUDL (CC BY 4.0, Catalyst Cooperative) and Open Grid Emissions' manual crosswalk (MIT). No person has checked the listed rows against the plants.

EPA's CEMS reports emissions by **emissions unit** (a boiler or turbine with a stack monitor). EIA reports capacity and generation by **generator**. Every generator-level emissions number, emission rate or plant-level CO2 total that mixes the two depends on the EPA-EIA crosswalk. In PUDL that is `core_epa__assn_eia_epacamd` (columns `report_year, plant_id_epa, emissions_unit_id_epa, generator_id_epa, plant_id_eia, boiler_id, generator_id`), with subplant groups in `core_epa__assn_eia_epacamd_subplant_ids` (`plant_id_eia, plant_id_epa, subplant_id, unit_id_pudl, emissions_unit_id_epa, generator_id`).

## When to use

- The user joins CEMS data (`core_epacems__hourly_emissions`, `out_epacems__yearly_operational_characteristics`, CAMPD downloads) to EIA-860/923 tables.
- CEMS units "disappear" after a merge, a plant's emissions look too low, a combined cycle's emission rate per MWh looks too high, or a plant that closed years ago shows a row for a recent year.
- The user asks whether a specific CEMS unit (plant id + unit id) is linked correctly.

Not for: non-US data, or EIA-only questions with no CEMS side.

## The traps (tell the user the ones that apply)

1. **Unmatched units are dropped, not flagged.** PUDL's description says its version "removes unmatched rows". An inner join silently loses them: in report year 2024, 273 of 4,215 CEMS units (6.5%) had no crosswalk row. Always left-join from the CEMS side and report how many units and how much load or CO2 had no match.
2. **The yearly CEMS table is a 3-year trailing window, so it keeps retired units.** Each `report_year` of `out_epacems__yearly_operational_characteristics` is estimated "from a trailing 3-year window of EPA CEMS reporting ending in that year". A 2024 row does not mean the unit ran in 2024: W. H. Zimmer (EIA 6019, retired May 2022) still has a 2024 row with a 1,313 MW peak. Of the 65 CEMS units of 2024 with load, no crosswalk row and no EIA-860 generator to link to, 33 are at plants whose combustion generators all retired in 2022 or 2023, 24 are at Astoria Gas Turbines (closed May 2023; one generator has no retirement date in EIA-860), 4 at the Cove Point LNG terminal (a non-EGU site in EPA's lists, last in EIA-860 for 2020) and 4 at EPA-only ids. These need no crosswalk fix. To know whether a unit ran in a year, use `core_epacems__hourly_emissions` for that year. Two cautions: a plant can be missing from PUDL's EIA-860 for a few years and come back, so "absent from EIA-860" is not proof of retirement; and an EIA-860 retirement can mean "left the U.S. grid" (Frontera, EIA 55098, retired 2016 in EIA-860, kept running for Mexico).
3. **Combined cycles: link at the subplant, not the generator.** CEMS monitors the gas turbines (prime mover CT); the steam turbine (CA) has no stack. Allocating a unit's emissions to single generators misses the steam turbine's output and inflates the rate per MWh. Group by `subplant_id` / `unit_id_pudl` from the subplant table, which already puts 7 of 10 unlinked steam generators found in one check in the same group as a linked turbine.
4. **Whole combined-cycle blocks can have no row.** Okeechobee (EPA 60345), York block 2 (55524), Frontera (55098), Tait (EPA 55248 = EIA 2847) and plant 6061 have CEMS units with load and operating EIA generators but no crosswalk row in 2019-2024 (Frontera 2018-2024; 6061 2022-2024).
5. **Steam generators folded onto the gas turbine.** At Glenarm (422 GT5), LEPA Unit No. 1 (58478 CC01) and CPV Fairview (60589 CT-1), both CAMD generators of the unit are linked to the gas turbine and the plant's steam turbine has no row.
6. **Links to a much smaller generator.** Antelope Elk (57865 units 1-3, 202 MW each) are linked to 9.3 MW engines while Elk Station 58835 ELK1-ELK3 (199.8 MW) have no row; Chalk Point SMECO (93 MW) is linked to a 16 MW turbine in 2018-2020 and 2023-2024 and has no row in 2021-2022 (Open Grid Emissions maps it to EIA 65285/GT1 for those two years).
7. **EPA and EIA plant ids differ.** Never assume `plant_id_epa == plant_id_eia`; take `plant_id_eia` from the crosswalk (Tait: EPA 55248, EIA 2847).
8. **EPA-only 88xxxx ids.** Six-digit plant ids starting with 88 are assigned by EPA's Clean Air Markets Division when EIA has none; there may be no EIA generator to match (880079 and 880102 have gap units every year 2018-2024).
9. **Downstream fixes exist.** Open Grid Emissions keeps a hand-made `epa_eia_crosswalk_manual.csv`; it covers all 10 `gap_all_linked` units of 2024 (none of the other 65) and several blocks above (column `in_oge_manual` in the tables). PUDL issue #5439 plans to integrate it, and PUDL issue #5752 reports traps 4-6. Check both before patching rows yourself.

## Run the checker

The checker and its three tables are in this skill's folder, next to this file: `check_units.py`, `known_issues.csv`, `gap_units_2018_2024.csv` and `gap_retirement_2018_2024.csv`. It uses the Python standard library only and makes no network calls; read it before running it. If those files are not in this folder, do not download code yourself: tell the user they are in the repository named above (tag v0.2.0) and let them fetch it.

Export the user's units to CSV with at least `plant_id_epa` and `emissions_unit_id_epa` (and `report_year` if they have it), for example with pandas `df[["report_year","plant_id_epa","emissions_unit_id_epa"]].drop_duplicates().to_csv("units.csv", index=False)`. Then, from this folder:

```
python check_units.py units.csv                 # text report
python check_units.py units.csv --year 2024     # treat every row as report year 2024
python check_units.py units.csv --json          # machine-readable findings
python check_units.py units.csv --fail-on-hit   # exit 1 if anything is flagged (CI)
```

Exit codes: 0 done, 1 hits with `--fail-on-hit`, 2 bad input (missing column or unreadable file).

What it flags, per unit (and year when given):
- `whole_cc_block_no_row`, `steam_generator_folded_onto_ct`, `linked_to_small_generator`: a row of `known_issues.csv`, with what PUDL links today (`linked_in_pudl`), a candidate EIA plant/generator and whether Open Grid Emissions' manual table covers it.
- `gap_absent`, `gap_not_operating`, `gap_all_linked`: a unit-year of `gap_units_2018_2024.csv` (load, no row, no unlinked operating combustion generator at the plant), with its peak MW. For absent and not_operating units it adds `retirement_class` (`retired_before`, `retired_in_year`, `never_listed` or `other`), `last_eia860_listing` and `latest_retirement_year` from `gap_retirement_2018_2024.csv`.
- `epa_only_plant_id`: an 88xxxx plant id.

## Explain the results honestly

- Every finding is a **lead**, not a diagnosis. The candidates come from size and prime-mover rules in pre-registered checks; the Frontera unit-to-turbine pairing is an assumption. Say that no person has checked them against the plants.
- The tables describe PUDL nightly builds of 5-8 November 2026. PUDL rebuilds nightly; if the user's build is newer, a listed row may be fixed. Check their own crosswalk for the unit before saying it is missing.
- A gap unit with `retirement_class` `retired_before` needs no crosswalk fix: its plant had retired and the trailing window kept it. Explain the window instead. `other` means EIA-860 does not show the whole plant retired; it is not proof the plant ran.
- Do not edit the user's crosswalk silently. Show the finding and the candidate rows and let the user decide; if they patch rows, keep them in a separate, documented override table.
- A clean result only means none of these known rows matched; it does not mean the crosswalk is right for the user's units.

## Sources and limits

- Results and code of each pre-registered check (plan published before data was read): github.com/munimtechnologies/eia860m-slip, `docs/xwpair.md`, `docs/ccsplit.md`, `docs/ccsub.md`, `docs/xwdev.md`, `docs/xwpudl.md`, `docs/xwgap.md`, `docs/xwstale.md`. `gap_units_2018_2024.csv` is the same file as `data/xwgap-units-2018-2024.csv` there, and `gap_retirement_2018_2024.csv` the same as `data/xwstale-units-2018-2024.csv`.
- PUDL metadata quoted from `src/pudl/metadata/resources/glue.py` and `epacems.py` (catalyst-cooperative/pudl, main, November 2026).
- Nobody at Catalyst Cooperative, EPA or Singularity Energy has reviewed these results. Questions or corrections: mv2@munimtech.com or an issue on the repo.
