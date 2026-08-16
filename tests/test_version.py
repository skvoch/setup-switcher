import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from switcher import version as version_module


class VersionTests(unittest.TestCase):
    def test_reads_embedded_release_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            version_file = Path(directory) / "VERSION"
            version_file.write_text("1.2.3-alpha.4", encoding="utf-8")
            with patch.object(version_module, "VERSION_FILE", version_file):
                self.assertEqual(version_module.current_version(), "1.2.3-alpha.4")

    def test_missing_or_empty_version_falls_back_to_dev(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            version_file = Path(directory) / "VERSION"
            with patch.object(version_module, "VERSION_FILE", version_file):
                self.assertEqual(version_module.current_version(), "dev")
                version_file.write_text("", encoding="utf-8")
                self.assertEqual(version_module.current_version(), "dev")

    def test_semantic_prerelease_comparison(self) -> None:
        self.assertTrue(version_module.is_newer_version("1.0.0", "1.0.0-alpha.1"))
        self.assertTrue(version_module.is_newer_version("v1.0.0-alpha.2", "1.0.0-alpha.1"))
        self.assertFalse(version_module.is_newer_version("1.0.0-alpha.1", "1.0.0-alpha.1"))
        self.assertFalse(version_module.is_newer_version("0.9.9", "1.0.0-alpha.1"))


if __name__ == "__main__":
    unittest.main()
