"""Tests for optional QR code export."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from creator_link_kit.qr import (
    QrDependencyError,
    QrJob,
    make_qr_jobs_from_csv,
    make_qr_jobs_from_urls,
    safe_filename,
    write_qr_codes,
)


class SafeFilenameTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(safe_filename("glowwithgreta"), "glowwithgreta")

    def test_strips_unsafe(self):
        self.assertEqual(safe_filename("Greta Mohr / YT!!"), "Greta-Mohr-YT")

    def test_empty_fallback(self):
        self.assertEqual(safe_filename("   "), "link")
        self.assertEqual(safe_filename("@@@"), "link")


class JobBuilderTests(unittest.TestCase):
    def test_urls(self):
        jobs = make_qr_jobs_from_urls(
            ["https://example.com/a", "", "https://example.com/b"]
        )
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0].stem, "qr-001")
        self.assertEqual(jobs[1].url, "https://example.com/b")

    def test_csv_with_handle(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "links.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["handle", "generated_url"])
                writer.writeheader()
                writer.writerow(
                    {
                        "handle": "glowwithgreta",
                        "generated_url": "https://shop.example.com/?utm_source=youtube",
                    }
                )
                writer.writerow(
                    {"handle": "", "generated_url": "https://shop.example.com/other"}
                )
            jobs = make_qr_jobs_from_csv(path)
            self.assertEqual(len(jobs), 2)
            self.assertEqual(jobs[0].stem, "glowwithgreta")
            self.assertEqual(jobs[1].stem, "qr-002")


class WriteQrTests(unittest.TestCase):
    def test_missing_dependency(self):
        with mock.patch.dict("sys.modules", {"segno": None}):
            # Force ImportError path by simulating missing module
            import creator_link_kit.qr as qr_mod

            original = qr_mod._require_segno

            def boom():
                raise QrDependencyError("missing")

            qr_mod._require_segno = boom  # type: ignore[assignment]
            try:
                with self.assertRaises(QrDependencyError):
                    write_qr_codes(
                        [QrJob("https://example.com", "x")],
                        Path("/tmp"),
                    )
            finally:
                qr_mod._require_segno = original  # type: ignore[assignment]

    def test_write_with_fake_segno(self):
        class FakeQr:
            def save(self, path, **kwargs):
                Path(path).write_text("qr", encoding="utf-8")

        class FakeSegno:
            @staticmethod
            def make(url, error="m"):
                return FakeQr()

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with mock.patch(
                "creator_link_kit.qr._require_segno", return_value=FakeSegno
            ):
                summary = write_qr_codes(
                    [
                        QrJob("https://example.com/a", "alpha"),
                        QrJob("https://example.com/b", "ALPHA"),  # case collision
                        QrJob("https://example.com/c", "alpha-2"),  # suffix collision
                        QrJob("https://example.com/d", "../unsafe"),
                        QrJob("not-a-url", "bad"),
                    ],
                    out,
                    fmt="svg",
                )
            self.assertEqual(summary.total, 5)
            self.assertEqual(summary.written, 4)
            self.assertEqual(summary.failed, 1)
            self.assertTrue((out / "alpha.svg").exists())
            self.assertTrue((out / "alpha-2.svg").exists())
            self.assertTrue((out / "alpha-2-2.svg").exists())
            self.assertTrue((out / "unsafe.svg").exists())


if __name__ == "__main__":
    unittest.main()

