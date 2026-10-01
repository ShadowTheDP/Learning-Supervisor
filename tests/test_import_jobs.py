from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.import_jobs import ImportJobPayload, create_import_job, get_import_job


class ImportJobsTests(unittest.TestCase):
    def test_create_import_job_persists_state_and_starts_worker_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            jobs_dir = Path(tmp_dir)

            class FakeProcess:
                pid = 43210

            with (
                patch("app.services.import_jobs.IMPORT_JOBS_DIR", jobs_dir),
                patch("app.services.import_jobs.subprocess.Popen", return_value=FakeProcess()) as popen_mock,
            ):
                payload = ImportJobPayload(
                    title="Lemma Notes",
                    description="Geometry notes",
                    source_path="C:/books/lemma.pdf",
                    deadline="2026-07-01",
                    priority=3,
                    learning_mode="application",
                )
                state = create_import_job(payload)

                self.assertEqual(state["status"], "queued")
                self.assertEqual(state["worker_pid"], 43210)
                self.assertEqual(state["payload"]["title"], "Lemma Notes")
                popen_mock.assert_called_once()

                stored = get_import_job(state["job_id"])
                assert stored is not None
                self.assertEqual(stored["worker_pid"], 43210)
                self.assertEqual(stored["payload"]["source_path"], "C:/books/lemma.pdf")

    def test_get_import_job_marks_dead_worker_as_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            jobs_dir = Path(tmp_dir)
            job_id = "job-dead-worker"
            state = {
                "version": 1,
                "job_id": job_id,
                "status": "running",
                "progress_percent": 32,
                "status_label": "正在解析 PDF",
                "detail": "Docling 正在抽取內容。",
                "created_at": "2026-06-21T10:40:40Z",
                "updated_at": "2026-06-21T10:40:41Z",
                "resource_id": None,
                "error_message": "",
                "worker_pid": 36500,
                "payload": {
                    "title": "MONT",
                    "description": "",
                    "source_path": "C:/books/mont.pdf",
                    "deadline": "2026-08-31",
                    "priority": 3,
                    "learning_mode": "application",
                },
            }
            (jobs_dir / f"{job_id}.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

            with (
                patch("app.services.import_jobs.IMPORT_JOBS_DIR", jobs_dir),
                patch("app.services.import_jobs._is_worker_process_active", return_value=False),
            ):
                repaired = get_import_job(job_id)

            assert repaired is not None
            self.assertEqual(repaired["status"], "failed")
            self.assertEqual(repaired["progress_percent"], 100)
            self.assertIn("背景匯入程序已提前結束", repaired["error_message"])


if __name__ == "__main__":
    unittest.main()
