"""Offline regression fixtures; writes are restricted to temporary directories."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.validate_package import ASSEMBLY, PROJECT, STEP, check_step, main, validate


MINIMAL_STEP = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('fixture'), '2;1');
ENDSEC;
DATA;
#1=PRODUCT('fixture','fixture',$,(#2));
#2=PRODUCT_CONTEXT('',#1,'mechanical');
ENDSEC;
END-ISO-10303-21;
"""


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = "Keep folder hierarchy: No\nNumber of Files Copied: 2\n" + (
            f"X:\\original\\{ASSEMBLY}\tM.27.00\tV1\n"
            "X:\\original\\Top.ipt\tM.27.00\tV1\n"
        )
        self.write("packngo.log", self.log, "utf-16")
        self.write(PROJECT, '<?xml version="1.0" encoding="utf-16"?><InventorProject><Path>.</Path></InventorProject>', "utf-16")
        self.write(STEP, MINIMAL_STEP)
        self.write(ASSEMBLY, "fixture only; not valid native CAD")
        self.write("Top.ipt", "fixture only; not valid native CAD")

    def write(self, name, content, encoding="utf-8"):
        (self.root / name).write_text(content, encoding=encoding)

    def codes(self, report, level="errors"):
        return {item["code"] for item in report[level]}

    def test_complete_fixture_and_hash_inventory(self):
        report = validate(self.root)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["manifest"]["listed_files"], 2)
        self.assertEqual(report["step"]["entities"], 2)
        self.assertEqual(len(report["assets"]), 4)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in report["assets"]))

    def test_missing_native_component_fails_cli_and_json(self):
        (self.root / "Top.ipt").unlink()
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = main(["--root", str(self.root), "--json"])
        report = json.loads(stream.getvalue())
        self.assertEqual(status, 1)
        self.assertIn("native_missing", self.codes(report))
        self.assertEqual(report["errors"][0]["path"], "Top.ipt")

    def test_utf8_bom_manifest(self):
        self.write("packngo.log", self.log, "utf-8-sig")
        self.assertEqual(validate(self.root)["errors"], [])

    def test_declared_count_mismatch(self):
        self.write("packngo.log", self.log.replace("Copied: 2", "Copied: 3"))
        self.assertIn("manifest_count", self.codes(validate(self.root)))

    def test_duplicate_flattened_names(self):
        self.write("packngo.log", self.log.replace("Top.ipt", ASSEMBLY.lower()))
        self.assertIn("manifest_duplicate", self.codes(validate(self.root)))

    def test_hierarchical_manifest_is_not_silently_flattened(self):
        self.write("packngo.log", self.log.replace("hierarchy: No", "hierarchy: Yes"))
        self.assertIn("manifest_unreadable", self.codes(validate(self.root)))

    def test_missing_manifest_and_malformed_project(self):
        (self.root / "packngo.log").unlink()
        self.write(PROJECT, "<broken")
        codes = self.codes(validate(self.root))
        self.assertIn("manifest_unreadable", codes)
        self.assertIn("project_unreadable", codes)

    def test_missing_project_resources_warn_once(self):
        self.write(PROJECT, '<InventorProject><Path>.\\Materials\\test.adsklib</Path><Path>.\\Materials\\test.adsklib</Path></InventorProject>')
        report = validate(self.root)
        self.assertEqual(report["errors"], [])
        self.assertEqual(len(report["warnings"]), 1)
        self.assertIn("project_resource_missing", self.codes(report, "warnings"))

    def test_external_resources_warn_without_lookup(self):
        self.write(PROJECT, '<InventorProject><Path>X:\\private\\library.adsklib</Path><Path>..\\outside</Path></InventorProject>')
        report = validate(self.root)
        self.assertEqual(len(report["warnings"]), 2)
        self.assertEqual(self.codes(report, "warnings"), {"project_external_resource"})

    def test_empty_and_unlisted_native_files(self):
        self.write("Top.ipt", "")
        self.write("Extra.ipt", "extra fixture")
        report = validate(self.root)
        self.assertIn("asset_empty", self.codes(report))
        self.assertIn("native_unlisted", self.codes(report, "warnings"))

    def test_validation_does_not_change_files(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        validate(self.root)
        after = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.assertEqual(before, after)

    def test_inventory_permission_error_is_structured(self):
        for json_output in (False, True):
            with self.subTest(json=json_output):
                stream = io.StringIO()
                with patch.object(Path, "iterdir", side_effect=PermissionError("listing denied")), contextlib.redirect_stdout(stream):
                    status = main(["--root", str(self.root)] + (["--json"] if json_output else []))
                self.assertEqual(status, 1)
                if json_output:
                    report = json.loads(stream.getvalue())
                    self.assertEqual(report["errors"], [{"code": "inventory_unreadable", "path": ".", "message": "listing denied"}])
                    self.assertEqual(report["manifest"]["listed_files"], 2)
                    self.assertEqual(report["step"]["entities"], 2)
                    self.assertEqual(len(report["assets"]), 3)  # known required assets still checked
                else:
                    self.assertIn("ERROR [inventory_unreadable] .: listing denied", stream.getvalue())

    def test_inventory_iteration_failure_is_structured(self):
        def partial_entries(path):
            yield path / "Top.ipt"
            raise OSError("listing interrupted")
        with patch.object(Path, "iterdir", partial_entries):
            report = validate(self.root)
        self.assertEqual(self.codes(report), {"inventory_unreadable"})
        self.assertEqual(report["errors"][0]["message"], "listing interrupted")

    def test_missing_root_fails(self):
        self.assertIn("package_missing", self.codes(validate(self.root / "absent")))


class StepTests(unittest.TestCase):
    def test_strings_comments_and_escaped_quotes_are_not_references(self):
        text = MINIMAL_STEP.replace("'fixture'", "'it''s #999 = ENDSEC;'")
        text = text.replace("DATA;", "DATA;\n/* #888=PRODUCT('fake'); */")
        summary, problems = check_step(text)
        self.assertEqual(problems, [])
        self.assertEqual(summary["entity_types"]["PRODUCT"], 1)

    def test_undefined_reference(self):
        _, problems = check_step(MINIMAL_STEP.replace("(#2)", "(#3)"))
        self.assertTrue(any("Undefined" in item for item in problems))

    def test_duplicate_definition(self):
        _, problems = check_step(MINIMAL_STEP.replace("#2=", "#1="))
        self.assertTrue(any("Duplicate" in item for item in problems))

    def test_truncation(self):
        _, problems = check_step(MINIMAL_STEP.replace("END-ISO-10303-21;", ""))
        self.assertTrue(any("closing marker" in item for item in problems))

    def test_entities_can_share_a_line(self):
        summary, problems = check_step(MINIMAL_STEP.replace(";\n#2", "; #2"))
        self.assertEqual(summary["entities"], 2)
        self.assertEqual(problems, [])

    def test_unterminated_string_or_comment(self):
        for suffix in ("/* unclosed", "'unclosed"):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                check_step(MINIMAL_STEP + suffix)


if __name__ == "__main__":
    unittest.main()
