from __future__ import annotations

import ctypes
import json
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..config import IMPORT_JOBS_DIR, PROJECT_ROOT


IMPORT_JOB_VERSION = 1
RUNNING_JOB_STATUSES = {"queued", "running"}


@dataclass(slots=True)
class ImportJobPayload:
    title: str
    description: str
    source_path: str
    deadline: str
    priority: int
    learning_mode: str


def _job_path(job_id: str) -> Path:
    return IMPORT_JOBS_DIR / f"{job_id}.json"


def _worker_log_path(job_id: str, stream_name: str) -> Path:
    return IMPORT_JOBS_DIR / f"{job_id}.{stream_name}.log"


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _python_executable() -> str:
    return sys.executable


def _worker_script() -> Path:
    return PROJECT_ROOT / "app" / "services" / "import_job_worker.py"


def _read_job_state(job_id: str) -> dict | None:
    path = _job_path(job_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_job_state(job_id: str, state: dict) -> None:
    _job_path(job_id).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_failed_job_state(job_id: str, state: dict, *, detail: str, error_message: str) -> dict:
    state.update(
        status="failed",
        progress_percent=100,
        status_label="匯入失敗",
        detail=detail,
        error_message=error_message,
        updated_at=_now_iso(),
    )
    _write_job_state(job_id, state)
    return state


def _is_worker_process_active(worker_pid: int | None) -> bool:
    if not isinstance(worker_pid, int) or worker_pid <= 0:
        return False

    if sys.platform == "win32":
        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(process_query_limited_information, False, worker_pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)) == 0:
                return False
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)

    import os

    try:
        os.kill(worker_pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _reconcile_job_state(state: dict) -> dict:
    status = str(state.get("status", "")).strip().lower()
    if status not in RUNNING_JOB_STATUSES:
        return state

    worker_pid = state.get("worker_pid")
    if _is_worker_process_active(worker_pid):
        return state

    job_id = str(state.get("job_id", "")).strip()
    if not job_id:
        return state

    return _write_failed_job_state(
        job_id,
        state,
        detail="背景匯入程序已中斷，PDF 沒有完成處理。",
        error_message=(
            "背景匯入程序已提前結束。這通常代表 Docling 在長 PDF 上耗盡記憶體，"
            "或子程序被系統中止。請先關閉其他高佔用程式後重試；若 PDF 不是掃描件，"
            "建議保持 OCR 關閉。"
        ),
    )


def list_recent_import_jobs(limit: int = 12) -> list[dict]:
    jobs: list[dict] = []
    for path in sorted(IMPORT_JOBS_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        jobs.append(_reconcile_job_state(state))
        if len(jobs) >= limit:
            break
    return jobs


def get_import_job(job_id: str) -> dict | None:
    state = _read_job_state(job_id)
    if state is None:
        return None
    return _reconcile_job_state(state)


def create_import_job(payload: ImportJobPayload) -> dict:
    job_id = str(uuid.uuid4())
    created_at = _now_iso()
    state = {
        "version": IMPORT_JOB_VERSION,
        "job_id": job_id,
        "status": "queued",
        "progress_percent": 0,
        "status_label": "已建立匯入任務",
        "detail": "正在準備 PDF 解析工作。",
        "created_at": created_at,
        "updated_at": created_at,
        "resource_id": None,
        "error_message": "",
        "worker_pid": None,
        "stdout_log_path": str(_worker_log_path(job_id, "stdout")),
        "stderr_log_path": str(_worker_log_path(job_id, "stderr")),
        "payload": {
            "title": payload.title,
            "description": payload.description,
            "source_path": payload.source_path,
            "deadline": payload.deadline,
            "priority": payload.priority,
            "learning_mode": payload.learning_mode,
        },
    }
    _write_job_state(job_id, state)

    stdout_handle = None
    stderr_handle = None
    try:
        stdout_handle = _worker_log_path(job_id, "stdout").open("ab")
        stderr_handle = _worker_log_path(job_id, "stderr").open("ab")
        process = subprocess.Popen(
            [_python_executable(), str(_worker_script()), job_id],
            cwd=str(PROJECT_ROOT),
            stdout=stdout_handle,
            stderr=stderr_handle,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as exc:
        _write_failed_job_state(
            job_id,
            state,
            detail="背景匯入程序沒有成功啟動。",
            error_message=f"無法啟動背景匯入程序：{exc}",
        )
        raise ValueError("無法啟動背景匯入程序，請稍後再試。") from exc
    finally:
        if stdout_handle is not None:
            stdout_handle.close()
        if stderr_handle is not None:
            stderr_handle.close()

    state["worker_pid"] = process.pid
    state["updated_at"] = _now_iso()
    _write_job_state(job_id, state)
    return state
