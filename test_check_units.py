# Tests for skills/cems-eia-crosswalk (check_units.py 0.2.0, known_issues.csv, gap_units_2018_2024.csv,
# gap_retirement_2018_2024.csv, SKILL.md).
# Copyright 2026 MV2, Munim, Inc. Apache-2.0. Made with AI agents working in MV2's name.
import csv
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "skills", "cems-eia-crosswalk")
sys.path.insert(0, SKILL)
import check_units as cu  # noqa: E402

KINDS = {"whole_cc_block_no_row", "linked_to_small_generator", "steam_generator_folded_onto_ct"}


def kinds(findings, plant, unit):
    return [f["kind"] for f in findings if f["plant_id_epa"] == plant and f["emissions_unit_id_epa"] == unit]


class TestTables(unittest.TestCase):
    def test_known_issues(self):
        with open(cu.KNOWN, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 19)
        self.assertEqual({r["kind"] for r in rows}, KINDS)
        self.assertEqual(len({r["issue_id"] for r in rows}), 19)
        for r in rows:
            self.assertTrue(r["plant_id_epa"].isdigit(), r)
            self.assertTrue(r["emissions_unit_id_epa"], r)
            self.assertTrue(r["suggested_generator_ids"], r)
            self.assertIn(r["in_oge_manual"], {"yes", "no", "partly", "not_checked"}, r)
            self.assertTrue(cu.years_in(r["report_years"]) <= {str(y) for y in range(2018, 2025)}, r)
        by_kind = {}
        for r in rows:
            by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
        self.assertEqual(by_kind, {"whole_cc_block_no_row": 12, "linked_to_small_generator": 4,
                                   "steam_generator_folded_onto_ct": 3})

    def test_gap_units(self):
        with open(cu.GAPS, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 317)
        per_year = {}
        for r in rows:
            per_year[r["report_year"]] = per_year.get(r["report_year"], 0) + 1
        # docs/xwgap.md in munimtechnologies/eia860m-slip, "Gap units by year"
        self.assertEqual(per_year, {"2018": 24, "2019": 34, "2020": 41, "2021": 46,
                                    "2022": 44, "2023": 53, "2024": 75})
        self.assertEqual(sum(1 for r in rows if r["report_year"] == "2024" and r["reason"] == "absent"), 62)

    def test_gap_retirement(self):
        with open(cu.RETIRED, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 228)
        per_year, classes = {}, {}
        for r in rows:
            per_year[r["report_year"]] = per_year.get(r["report_year"], 0) + 1
            if r["report_year"] == "2024":
                classes[r["class"]] = classes.get(r["class"], 0) + 1
        # docs/xwstale.md in munimtechnologies/eia860m-slip, "Classes by report year"
        self.assertEqual(per_year, {"2018": 18, "2019": 27, "2020": 28, "2021": 28,
                                    "2022": 23, "2023": 39, "2024": 65})
        self.assertEqual(classes, {"retired_before": 33, "other": 28, "never_listed": 4})
        # Exactly the absent and not_operating rows of the gap table, with the same reason.
        with open(cu.GAPS, newline="", encoding="utf-8") as f:
            gaps = {(g["report_year"], g["plant_id_epa"], g["emissions_unit_id_epa"]): g["reason"]
                    for g in csv.DictReader(f) if g["reason"] in ("absent", "not_operating")}
        ret = {(r["report_year"], r["plant_id_epa"], r["emissions_unit_id_epa"]): r["xwgap_reason"]
               for r in rows}
        self.assertEqual(ret, gaps)

    def test_years_in(self):
        self.assertEqual(cu.years_in("2022-2024"), {"2022", "2023", "2024"})
        self.assertEqual(cu.years_in("2018-2020;2023-2024"), {"2018", "2019", "2020", "2023", "2024"})
        self.assertEqual(cu.years_in("2024"), {"2024"})


class TestCheck(unittest.TestCase):
    def test_2024_sample(self):
        rows = [
            {"report_year": "2024", "plant_id_epa": "60345", "emissions_unit_id_epa": "OCEC1A"},
            {"report_year": "2024", "plant_id_epa": "6019", "emissions_unit_id_epa": "1"},
            {"report_year": "2024", "plant_id_epa": "880079", "emissions_unit_id_epa": "37"},
            {"report_year": "2024", "plant_id_epa": "3", "emissions_unit_id_epa": "1"},
            {"report_year": "2024", "plant_id_epa": "1571", "emissions_unit_id_epa": "SMECO"},
        ]
        f = cu.check_rows(rows)
        self.assertEqual(kinds(f, "60345", "OCEC1A"), ["whole_cc_block_no_row"])
        self.assertEqual(kinds(f, "6019", "1"), ["gap_absent"])
        self.assertEqual(kinds(f, "880079", "37"), ["gap_absent", "epa_only_plant_id"])
        self.assertEqual(kinds(f, "3", "1"), [])
        self.assertEqual(kinds(f, "1571", "SMECO"), ["linked_to_small_generator"])
        ocec = [x for x in f if x["emissions_unit_id_epa"] == "OCEC1A"][0]
        self.assertEqual(ocec["suggested"], "60345/1A;1ST")
        zimmer = [x for x in f if x["plant_id_epa"] == "6019"][0]
        self.assertEqual(zimmer["peak_mw"], "1313.0")
        self.assertIn("trailing window", zimmer["message"])
        self.assertEqual(zimmer["retirement_class"], "retired_before")
        self.assertEqual(zimmer["last_eia860_listing"], "2022")
        self.assertEqual(zimmer["latest_retirement_year"], "2022")
        self.assertIn("retired by 2022, before 2024", zimmer["message"])
        epa_only = [x for x in f if x["plant_id_epa"] == "880079" and x["kind"] == "gap_absent"][0]
        self.assertEqual(epa_only["retirement_class"], "never_listed")
        self.assertIsNone(epa_only["last_eia860_listing"])

    def test_retirement_other_and_all_linked(self):
        f = cu.check_rows([{"report_year": "2024", "plant_id_epa": "55243",
                            "emissions_unit_id_epa": "CT2-1A"}])
        self.assertEqual([x["kind"] for x in f], ["gap_absent"])
        self.assertEqual(f[0]["retirement_class"], "other")
        self.assertEqual(f[0]["last_eia860_listing"], "2023")
        self.assertIsNone(f[0]["latest_retirement_year"])
        self.assertIn("a combustion generator has no retirement date", f[0]["message"])
        f = cu.check_rows([{"report_year": "2021", "plant_id_epa": "1571", "emissions_unit_id_epa": "SMECO"}])
        self.assertNotIn("retirement_class", f[0])
        f = cu.check_rows([{"report_year": "2024", "plant_id_epa": "356", "emissions_unit_id_epa": "8"}])
        self.assertEqual([x["kind"] for x in f], ["gap_not_operating"])
        self.assertEqual(f[0]["retirement_class"], "retired_before")
        self.assertEqual(f[0]["latest_retirement_year"], "2023")

    def test_year_filter(self):
        f = cu.check_rows([{"report_year": "2018", "plant_id_epa": "60345", "emissions_unit_id_epa": "OCEC1A"}])
        self.assertEqual(f, [])
        f = cu.check_rows([{"report_year": "2021", "plant_id_epa": "1571", "emissions_unit_id_epa": "SMECO"}])
        self.assertEqual([x["kind"] for x in f], ["gap_all_linked"])
        self.assertIn("in Open Grid Emissions' manual crosswalk: yes".lower(), f[0]["message"].lower())

    def test_no_year_and_normalising(self):
        f = cu.check_rows([{"plant_id_epa": "6019.0", "emissions_unit_id_epa": " 1 "}])
        self.assertEqual(sorted(x["report_year"] for x in f), ["2023", "2024"])
        self.assertEqual({x["retirement_class"] for x in f}, {"retired_before"})
        f = cu.check_rows([{"plant_id_epa": "1571", "emissions_unit_id_epa": "SMECO"}])
        self.assertEqual(sorted(x["kind"] for x in f), ["gap_all_linked", "gap_all_linked", "linked_to_small_generator"])

    def test_duplicates_counted_once(self):
        row = {"report_year": "2024", "plant_id_epa": "55098", "emissions_unit_id_epa": "1"}
        f = cu.check_rows([row, dict(row)])
        self.assertEqual(kinds(f, "55098", "1"), ["whole_cc_block_no_row"])

    def test_epa_only_rule(self):
        self.assertTrue(cu.is_epa_only_id("880102"))
        self.assertFalse(cu.is_epa_only_id("8801"))
        self.assertFalse(cu.is_epa_only_id("55098"))


class TestCli(unittest.TestCase):
    def _csv(self, text):
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return path

    def run_main(self, args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cu.main(args)
        return code, out.getvalue(), err.getvalue()

    def test_missing_column(self):
        code, _, err = self.run_main([self._csv("plant_id_epa,unit\n1,2\n")])
        self.assertEqual(code, 2)
        self.assertIn("emissions_unit_id_epa", err)

    def test_fail_on_hit(self):
        path = self._csv("plant_id_epa,emissions_unit_id_epa\n55524,5\n3,1\n")
        self.assertEqual(self.run_main([path, "--year", "2024"])[0], 0)
        code, out, _ = self.run_main([path, "--year", "2024", "--fail-on-hit"])
        self.assertEqual(code, 1)
        self.assertIn("55524/5 (2024) whole_cc_block_no_row", out)
        self.assertIn("no person has checked", out)
        self.assertIn("cems-eia-crosswalk 0.2.0", out)

    def test_clean_passes_fail_on_hit(self):
        path = self._csv("report_year,plant_id_epa,emissions_unit_id_epa\n2024,3,1\n")
        code, out, _ = self.run_main([path, "--fail-on-hit", "--json"])
        self.assertEqual(code, 0)
        self.assertIn('"findings": []', out)


class TestSkillDoc(unittest.TestCase):
    def test_frontmatter(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertTrue(text.startswith("---\n"))
        head = text.split("---\n")[1]
        fields = dict(line.split(": ", 1) for line in head.strip().splitlines())
        self.assertEqual(fields["name"], "cems-eia-crosswalk")
        self.assertEqual(fields["license"], "Apache-2.0")
        self.assertGreater(len(fields["description"]), 200)
        self.assertLess(len(fields["description"]), 1024)
        self.assertNotIn(": ", fields["description"])
        self.assertIn("made with AI agents", text)
        self.assertNotIn("MIT License", text)
        for name in ("check_units.py", "known_issues.csv", "gap_units_2018_2024.csv",
                     "gap_retirement_2018_2024.csv", "xwstale.md"):
            self.assertIn(name, text)
        # The skill must not tell agents to download code at run time.
        self.assertNotIn("git clone", text)
        self.assertNotIn("curl ", text)
        self.assertIn("version 0.2.0", text)
        self.assertEqual(cu.__version__, "0.2.0")


if __name__ == "__main__":
    unittest.main()
