#!/usr/bin/env python3
# cems-eia-crosswalk check_units.py 0.1.0
# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name. No person has checked the listed rows by hand.
"""Flag EPA CEMS units that hit known problems in the EPA-EIA crosswalk.

Reads a CSV that has at least the columns plant_id_epa and emissions_unit_id_epa
(optionally report_year). PUDL's core_epa__assn_eia_epacamd, a list of CEMS units,
or a joined emissions table all work. Standard library only; no network.

It checks each unit against two tables shipped next to this script:
  known_issues.csv        19 crosswalk rows that are missing or point at the wrong
                          generator (pre-registered checks, PUDL nightly, Nov 2026)
  gap_units_2018_2024.csv 317 unit-years with a CEMS peak load, no crosswalk row
                          and no unlinked operating EIA generator to link to
and one rule: EPA-assigned plant ids that start with 88 (six digits) have no EIA plant.

Exit codes: 0 done; 1 hits found and --fail-on-hit given; 2 bad input.
"""
import argparse
import csv
import json
import os
import sys

__version__ = "0.1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
KNOWN = os.path.join(HERE, "known_issues.csv")
GAPS = os.path.join(HERE, "gap_units_2018_2024.csv")

GAP_TEXT = {
    "absent": ("No EIA-860 generator row at EIA plant {eia} in PUDL for {year}, so there is "
               "nothing to link to. PUDL's yearly CEMS table uses a 3-year trailing window, so "
               "the unit may have stopped running before {year} (W. H. Zimmer, EIA 6019, retired "
               "May 2022, still has a 2024 row). Check the hourly CEMS table for that year."),
    "not_operating": ("EIA-860 lists generators at EIA plant {eia} in {year} but none with an "
                      "operating status; the unit has no crosswalk row."),
    "all_linked": ("Every operating combustion generator at EIA plant {eia} is already linked "
                   "to other CEMS units in {year}; this unit has no row. Generators that fit its "
                   "peak: {fit}. In Open Grid Emissions' manual crosswalk: {oge}."),
}


def norm_plant(v):
    s = (v or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def norm_unit(v):
    return (v or "").strip()


def norm_year(v):
    s = norm_plant(v)
    return s if s.isdigit() else ""


def load_known(path=KNOWN):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        key = (norm_plant(r["plant_id_epa"]), norm_unit(r["emissions_unit_id_epa"]))
        out.setdefault(key, []).append(r)
    return out


def load_gaps(path=GAPS):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        key = (norm_plant(r["plant_id_epa"]), norm_unit(r["emissions_unit_id_epa"]))
        out.setdefault(key, []).append(r)
    return out


def years_in(spans):
    """'2018-2020;2023-2024' -> {'2018', '2019', '2020', '2023', '2024'}."""
    out = set()
    for span in spans.split(";"):
        a, _, b = span.strip().partition("-")
        if not b:
            out.add(a)
        else:
            out.update(str(y) for y in range(int(a), int(b) + 1))
    return out


def is_epa_only_id(plant):
    return len(plant) == 6 and plant.startswith("88") and plant.isdigit()


def check_rows(rows, known=None, gaps=None):
    """rows: iterable of dicts. Returns a list of findings (dicts)."""
    known = load_known() if known is None else known
    gaps = load_gaps() if gaps is None else gaps
    findings = []
    seen = set()
    for r in rows:
        plant = norm_plant(r.get("plant_id_epa"))
        unit = norm_unit(r.get("emissions_unit_id_epa"))
        year = norm_year(r.get("report_year"))
        if not plant or not unit:
            continue
        key = (plant, unit, year)
        if key in seen:
            continue
        seen.add(key)
        for k in known.get((plant, unit), []):
            if year and year not in years_in(k["report_years"]):
                continue
            findings.append({
                "plant_id_epa": plant, "emissions_unit_id_epa": unit, "report_year": year or None,
                "kind": k["kind"], "issue_id": k["issue_id"],
                "linked_in_pudl": k["linked_in_pudl"] or None,
                "suggested": "%s/%s" % (k["suggested_plant_id_eia"], k["suggested_generator_ids"]),
                "report_years": k["report_years"], "in_oge_manual": k["in_oge_manual"],
                "source_doc": k["source_doc"], "message": k["note"],
            })
        g_rows = gaps.get((plant, unit), [])
        if year:
            g_rows = [g for g in g_rows if g["report_year"] == year]
        for g in g_rows:
            text = GAP_TEXT.get(g["reason"], "Gap unit ({reason}).").format(
                eia=g["plant_id_eia"], year=g["report_year"], reason=g["reason"],
                fit=g["linked_generators_that_fit"] or "none",
                oge="yes" if g["in_oge_manual"] == "True" else "no")
            findings.append({
                "plant_id_epa": plant, "emissions_unit_id_epa": unit,
                "report_year": g["report_year"], "kind": "gap_" + g["reason"],
                "issue_id": None, "peak_mw": g["max_gross_load_mw"],
                "in_oge_manual": "yes" if g["in_oge_manual"] == "True" else "no",
                "source_doc": "xwgap.md", "message": text,
            })
        if is_epa_only_id(plant) and (plant, "*88*") not in seen:
            seen.add((plant, "*88*"))
            findings.append({
                "plant_id_epa": plant, "emissions_unit_id_epa": unit, "report_year": year or None,
                "kind": "epa_only_plant_id", "issue_id": None, "source_doc": "xwgap.md",
                "message": ("Plant id %s is an EPA-assigned 88xxxx id: EIA has no plant with this "
                            "id, so there may be no EIA generator to match." % plant),
            })
    return findings


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        missing = [c for c in ("plant_id_epa", "emissions_unit_id_epa") if c not in cols]
        if missing:
            raise ValueError("input lacks column(s): " + ", ".join(missing))
        return list(reader)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("csv", help="CSV with plant_id_epa, emissions_unit_id_epa (and optionally report_year)")
    p.add_argument("--year", help="only check this report_year (overrides the column)")
    p.add_argument("--json", action="store_true", help="print findings as JSON")
    p.add_argument("--fail-on-hit", action="store_true", help="exit 1 if anything is flagged")
    p.add_argument("--version", action="version", version=__version__)
    a = p.parse_args(argv)
    try:
        rows = read_csv(a.csv)
    except (OSError, ValueError, csv.Error) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    if a.year:
        for r in rows:
            r["report_year"] = a.year
    found = check_rows(rows)
    if a.json:
        print(json.dumps({"version": __version__, "rows_read": len(rows), "findings": found}, indent=1))
    else:
        units = {(f["plant_id_epa"], f["emissions_unit_id_epa"]) for f in found}
        print("cems-eia-crosswalk %s: %d rows read, %d findings on %d units"
              % (__version__, len(rows), len(found), len(units)))
        for f in found:
            yr = f.get("report_year") or "any year"
            print("- %s/%s (%s) %s: %s" % (f["plant_id_epa"], f["emissions_unit_id_epa"], yr,
                                          f["kind"], f["message"]))
            if f.get("suggested"):
                print("    linked in PUDL: %s; candidate: %s; in OGE manual table: %s"
                      % (f.get("linked_in_pudl") or "no row", f["suggested"], f["in_oge_manual"]))
        print("These are leads from pre-registered checks of PUDL nightly builds (5-8 Nov 2026); "
              "no person has checked them against the plants.")
    return 1 if (found and a.fail_on_hit) else 0


if __name__ == "__main__":
    sys.exit(main())
