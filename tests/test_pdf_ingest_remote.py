from __future__ import annotations

import json
import tempfile
import unittest
from base64 import b64encode
from pathlib import Path
from unittest.mock import patch

import requests

from app.services.pdf_ingest import load_pdf_source


class FakeHttpResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.status_code = 200
        self.text = json.dumps(payload)

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class PdfIngestBackendSelectionTests(unittest.TestCase):
    def test_load_pdf_source_defaults_to_local_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "lecture.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\nlocal smoke\n")

            expected_result = ("# Chapter 1", str(pdf_path), [])

            with patch(
                "app.services.pdf_ingest.load_pdf_source_local",
                return_value=expected_result,
            ) as mock_local:
                result = load_pdf_source(str(pdf_path))

            self.assertEqual(result, expected_result)
            mock_local.assert_called_once_with(str(pdf_path), artifact_dir=None)

    def test_remote_backend_without_url_raises_clear_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "lecture.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\nremote smoke\n")

            with patch("app.services.pdf_ingest.DOCLING_PDF_BACKEND", "remote"), patch(
                "app.services.pdf_ingest.DOCLING_SERVE_URL",
                "",
            ):
                with self.assertRaisesRegex(ValueError, "DOCLING_SERVE_URL"):
                    load_pdf_source(str(pdf_path))


class PdfIngestRemoteTests(unittest.TestCase):
    def test_docling_serve_source_conversion_returns_markdown_and_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_path = Path(tmp_dir)
            pdf_path = temp_path / "lecture.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\nremote smoke\n")
            artifact_dir = temp_path / "resource"

            captured: dict[str, object] = {}

            def fake_post(url, json, headers, timeout):
                captured["url"] = url
                captured["timeout"] = timeout
                captured["accept"] = headers.get("Accept")
                captured["api_key"] = headers.get("X-API-Key")
                captured["json"] = json
                return FakeHttpResponse(
                    {
                        "document": {
                            "md_content": "# Chapter 1\n\nRemote body.\n",
                            "json_content": {
                                "items": [
                                    {
                                        "text": "Chapter 1",
                                        "label": "section_header",
                                        "prov": [{"page_no": 2}],
                                    },
                                    {
                                        "text": "This paragraph belongs to the first chapter.",
                                        "label": "text",
                                        "prov": [{"page_no": 3}],
                                    },
                                    {
                                        "text": "Example 1",
                                        "label": "section_header",
                                        "prov": [{"page_no": 4}],
                                    },
                                ]
                            },
                        },
                        "errors": [],
                    }
                )

            with patch("app.services.pdf_ingest.DOCLING_PDF_BACKEND", "remote"), patch(
                "app.services.pdf_ingest.DOCLING_SERVE_URL",
                "https://docling.example",
            ), patch(
                "app.services.pdf_ingest.DOCLING_SERVE_API_KEY",
                "secret-key",
            ), patch(
                "app.services.pdf_ingest.requests.post",
                side_effect=fake_post,
            ):
                markdown_text, source_reference, unit_hints = load_pdf_source(
                    str(pdf_path),
                    artifact_dir=artifact_dir,
                )

            self.assertEqual(markdown_text, "# Chapter 1\n\nRemote body.")
            self.assertEqual(source_reference, str(pdf_path))
            self.assertEqual(len(unit_hints), 2)
            self.assertEqual(unit_hints[0].title, "Chapter 1")
            self.assertEqual(unit_hints[0].page_start, 2)
            self.assertEqual(unit_hints[0].page_end, 3)
            self.assertEqual(unit_hints[1].title, "Example 1")
            self.assertEqual(unit_hints[1].page_start, 4)
            self.assertEqual(captured["url"], "https://docling.example/v1/convert/source")
            self.assertEqual(captured["accept"], "application/json")
            self.assertEqual(captured["api_key"], "secret-key")
            self.assertEqual(captured["json"]["sources"][0]["filename"], "lecture.pdf")
            self.assertEqual(
                captured["json"]["sources"][0]["base64_string"],
                b64encode(pdf_path.read_bytes()).decode("ascii"),
            )
            self.assertEqual(captured["json"]["options"], {"to_formats": ["md", "json"]})
            self.assertEqual(captured["json"]["sources"][0]["kind"], "file")
            self.assertTrue((artifact_dir / "original.pdf").exists())
            self.assertTrue((artifact_dir / "docling" / "source.md").exists())
            self.assertTrue((artifact_dir / "docling" / "outline.json").exists())

    def test_docling_serve_connection_error_raises_clear_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "lecture.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\nremote smoke\n")

            with patch("app.services.pdf_ingest.DOCLING_PDF_BACKEND", "remote"), patch(
                "app.services.pdf_ingest.DOCLING_SERVE_URL",
                "https://docling.example",
            ), patch(
                "app.services.pdf_ingest.requests.post",
                side_effect=requests.ConnectionError("connection refused"),
            ):
                with self.assertRaisesRegex(ValueError, "無法連上官方 docling-serve"):
                    load_pdf_source(str(pdf_path))


if __name__ == "__main__":
    unittest.main()
