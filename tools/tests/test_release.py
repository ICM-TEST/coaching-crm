#!/usr/bin/env python3
"""The release tool's checks, on made-up text. Run from the repo root:  python3 tools/tests/test_release.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import release  # noqa: E402


class Release(unittest.TestCase):
    def test_scan_finds_personal_data(self):
        self.assertTrue(release.scan_text("a", "billed by Jane Doe", ["jane doe"]))
        self.assertTrue(release.scan_text("a", "write to real.person@" + "gmail.com", []))
        self.assertTrue(release.scan_text("a", "token ghp_" + "a" * 30, []))

    def test_scan_leaves_made_up_data_alone(self):
        self.assertEqual(release.scan_text("a", "q@example.test and Janet", ["jane"]), [])

    def test_bump(self):
        self.assertEqual(release.bump("0.1.0", "patch"), "0.1.1")
        self.assertEqual(release.bump("0.1.3", "minor"), "0.2.0")
        self.assertEqual(release.bump("0.1.3", "major"), "1.0.0")

    def test_version_file(self):
        out = release.bumped_version_file("version: 0.1.0\nreleased: 2026-01-01\n\n- old\n", "0.1.1", "2026-02-02", "note")
        self.assertIn("version: 0.1.1", out)
        self.assertIn("released: 2026-02-02", out)
        self.assertTrue(out.endswith("- 0.1.1 (2026-02-02): note\n"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
