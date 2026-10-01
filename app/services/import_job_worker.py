from __future__ import annotations

import json
import sys
import traceback
from datetime import UTC, date, datetime
from pathlib import Path


if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from app.config import IMPORT_JOBS_DIR  # type: ignore
    from app.db import SessionLocal  # type: ignore
    from app.services.settings_service import get_app_settings  # type: ignore
    from app.services.study_service import create_resource_plan  # type: ignore
else:
    from ..config import IMPORT_JOBS_DIR
    from ..db import SessionLocal
    from .settings_service import get_app_settings
    from .study_service import create_resource_plan


def _job_path(job_id: str) -> Path:
    return IMPORT_JOBS_DIR / f"{job_id}.json"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_job_state(job_id: str) -> dict:
    return json.loads(_job_path(job_id).read_text(encoding="utf-8"))


def _write_job_state(job_id: str, state: dict) -> None:
    _job_path(job_id).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _replace_job_state(job_id: str, **updates: object) -> dict:
    state = _read_job_state(job_id)
    state.update(updates)
    state["updated_at"] = _now_iso()
    _write_job_state(job_id, state)
    return state


def _set_job_progress(job_id: str, percent: int, label: str, detail: str) -> None:
    _replace_job_state(
        job_id,
        progress_percent=max(0, min(100, int(percent))),
        status_label=label,
        detail=detail,
    )


def _set_pdf_parse_progress(job_id: str, completed_pages: int, total_pages: int, phase: str) -> None:
    safe_total = max(1, int(total_pages or 0))
    safe_done = max(0, min(safe_total, int(completed_pages or 0)))
    percent = 18 + round((safe_done / safe_total) * 62)

    if phase == "starting":
        detail = f"Docling 已建立解析流程，準備處理 {safe_total} 頁 PDF。"
    elif phase == "done":
        detail = f"Docling 已完成 {safe_total}/{safe_total} 頁解析，正在建立學習單元與任務。"
    else:
        detail = f"Docling 正在解析 PDF：已完成 {safe_done}/{safe_total} 頁。"

    _set_job_progress(job_id, percent, "正在解析 PDF", detail)


def run_import_job(job_id: str) -> int:
    job_state = _read_job_state(job_id)
    payload = job_state["payload"]
    _replace_job_state(job_id, status="running")

    session = SessionLocal()
    try:
        _set_job_progress(job_id, 8, "正在排隊", "後台任務已啟動，正在建立資源。")
        parsed_deadline = date.fromisoformat(str(payload["deadline"]))

        _set_job_progress(job_id, 18, "正在檢查輸入", "已接收標題、期限與 PDF 路徑。")
        app_settings = get_app_settings(session)

        resource = create_resource_plan(
            session,
            title=str(payload["title"]),
            description=str(payload["description"]),
            source_path=str(payload["source_path"]),
            deadline=parsed_deadline,
            priority=int(payload["priority"]),
            learning_mode=str(payload["learning_mode"]),
            review_intervals_csv=app_settings.review_intervals_csv,
            allow_weekend_scheduling=app_settings.allow_weekend_scheduling,
            progress_callback=lambda done, total, phase: _set_pdf_parse_progress(job_id, done, total, phase),
        )

        _set_job_progress(job_id, 82, "正在建立任務", "已完成 PDF 解析，正在建立學習單元與任務。")
        unit_count = len(resource.learning_units)
        task_count = sum(len(unit.daily_tasks) for unit in resource.learning_units)

        _replace_job_state(
            job_id,
            status="completed",
            progress_percent=100,
            status_label="匯入完成",
            detail=f"已建立 {unit_count} 個單元與 {task_count} 個學習任務。",
            resource_id=resource.id,
            error_message="",
        )
        return 0
    except Exception as exc:
        traceback.print_exc()
        _replace_job_state(
            job_id,
            status="failed",
            progress_percent=100,
            status_label="匯入失敗",
            detail="PDF 匯入沒有完成。",
            error_message=str(exc),
        )
        return 1
    finally:
        session.close()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return 2
    return run_import_job(argv[1])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
