from __future__ import annotations

import base64
import json
import re
import shutil
from pathlib import Path
from types import MethodType
from typing import Any, Callable, Iterable

import pypdfium2 as pdfium
import requests

from ..config import (
    DOCLING_ARTIFACTS_DIR,
    DOCLING_EASYOCR_DIR,
    DOCLING_EASYOCR_LANGS,
    DOCLING_PDF_BACKEND,
    DOCLING_PDF_FORMULA_ENRICHMENT,
    DOCLING_PDF_OCR_ENABLED,
    DOCLING_REMOTE_TIMEOUT_SECONDS,
    DOCLING_SERVE_API_KEY,
    DOCLING_SERVE_URL,
)
from .markdown_ingest import UnitHint, infer_content_type, looks_like_structural_unit_title


HEADING_LABEL_KEYWORDS = ("title", "section_header", "heading", "header")
ENGLISH_STRUCTURAL_TITLE_PATTERN = re.compile(
    r"^(chapter|part|section)\s+(?:\d+(?:\.\d+)*|[ivxlcdm]+|[a-z])(?:\b|[).:-])",
    re.IGNORECASE,
)
FAILED_PAGE_PATTERN = re.compile(r"page\s+(\d+)\b", re.IGNORECASE)
SIMPLIFIED_CHINESE = {"ch_sim", "zh", "zh-cn", "zh_cn", "zh-hans", "zh_hans"}
PdfProgressCallback = Callable[[int, int, str], None]
LARGE_PDF_PAGE_THRESHOLD = 120
LARGE_PDF_FILE_SIZE_THRESHOLD_BYTES = 12 * 1024 * 1024
LOW_MEMORY_QUEUE_MAX_SIZE = 2
LOW_MEMORY_BATCH_SIZE = 1
LOW_MEMORY_BATCH_POLLING_INTERVAL_SECONDS = 0.05


def required_easyocr_model_files(languages: Iterable[str]) -> list[str]:
    required = {"craft_mlt_25k.pth", "english_g2.pth"}
    normalized = {str(language).strip().lower() for language in languages if str(language).strip()}
    if normalized & SIMPLIFIED_CHINESE:
        required.add("zh_sim_g2.pth")
    return sorted(required)


def missing_easyocr_model_files(model_dir: Path, languages: Iterable[str]) -> list[str]:
    return [
        filename
        for filename in required_easyocr_model_files(languages)
        if not (model_dir / filename).exists()
    ]


def apply_low_memory_docling_profile(pipeline_options: object) -> object:
    setattr(pipeline_options, "queue_max_size", LOW_MEMORY_QUEUE_MAX_SIZE)
    setattr(pipeline_options, "ocr_batch_size", LOW_MEMORY_BATCH_SIZE)
    setattr(pipeline_options, "layout_batch_size", LOW_MEMORY_BATCH_SIZE)
    setattr(pipeline_options, "table_batch_size", LOW_MEMORY_BATCH_SIZE)
    setattr(
        pipeline_options,
        "batch_polling_interval_seconds",
        LOW_MEMORY_BATCH_POLLING_INTERVAL_SECONDS,
    )
    return pipeline_options


def should_use_low_memory_docling(
    page_count: int | None,
    file_size_bytes: int | None = None,
) -> bool:
    if page_count is not None and page_count >= LARGE_PDF_PAGE_THRESHOLD:
        return True
    if file_size_bytes is not None and file_size_bytes >= LARGE_PDF_FILE_SIZE_THRESHOLD_BYTES:
        return True
    return False


def get_pdf_page_count_for_docling(pdf_path: Path) -> int | None:
    try:
        with pdfium.PdfDocument(str(pdf_path)) as document:
            return len(document)
    except Exception:
        return None


def build_docling_pipeline_options(*, low_memory: bool = False) -> object:
    try:
        from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
    except ImportError as exc:
        raise ValueError(
            "PDF 匯入需要先在這個專案的 `.venv` 安裝 Docling 與 EasyOCR。"
            "請先執行 `.venv\\Scripts\\python.exe -m pip install -r requirements.txt`。"
        ) from exc

    pipeline_options = PdfPipelineOptions(
        artifacts_path=DOCLING_ARTIFACTS_DIR,
        do_ocr=DOCLING_PDF_OCR_ENABLED,
        do_table_structure=True,
        do_formula_enrichment=DOCLING_PDF_FORMULA_ENRICHMENT,
    )
    if low_memory:
        apply_low_memory_docling_profile(pipeline_options)

    if not DOCLING_PDF_OCR_ENABLED:
        return pipeline_options

    DOCLING_EASYOCR_DIR.mkdir(parents=True, exist_ok=True)
    languages = list(DOCLING_EASYOCR_LANGS)
    missing_models = missing_easyocr_model_files(DOCLING_EASYOCR_DIR, languages)

    pipeline_options.ocr_options = EasyOcrOptions(
        lang=languages,
        model_storage_directory=str(DOCLING_EASYOCR_DIR),
        download_enabled=not missing_models,
        use_gpu=False,
    )
    return pipeline_options


def build_docling_converter(*, low_memory: bool = False) -> object:
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError as exc:
        raise ValueError(
            "PDF 匯入需要先在這個專案的 `.venv` 安裝 Docling 與 EasyOCR。"
            "請先執行 `.venv\\Scripts\\python.exe -m pip install -r requirements.txt`。"
        ) from exc

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=build_docling_pipeline_options(low_memory=low_memory),
            )
        }
    )


def build_docling_converter_with_progress(
    progress_callback: PdfProgressCallback | None = None,
    *,
    low_memory: bool = False,
) -> object:
    converter = build_docling_converter(low_memory=low_memory)
    if progress_callback is None:
        return converter

    try:
        from docling.datamodel.base_models import InputFormat
        from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
    except ImportError:
        return converter

    pipeline = converter._get_pipeline(InputFormat.PDF)  # type: ignore[attr-defined]
    if not isinstance(pipeline, StandardPdfPipeline):
        return converter

    original_build_document = pipeline._build_document

    def build_document_with_progress(conv_res):
        total_pages = int(getattr(conv_res.input, "page_count", 0) or 0)
        if total_pages > 0:
            progress_callback(0, total_pages, "starting")
        completed_pages: set[int] = set()
        failed_pages: set[int] = set()

        original_create_run_ctx = pipeline._create_run_ctx

        def create_run_ctx_with_progress():
            ctx = original_create_run_ctx()
            if not getattr(ctx, "stages", None):
                return ctx

            assemble_stage = ctx.stages[-1]
            original_emit = assemble_stage._emit

            def emit_with_progress(self, items):
                materialized_items = list(items)
                for item in materialized_items:
                    page_no = int(getattr(item, "page_no", 0) or 0)
                    if page_no <= 0:
                        continue
                    if getattr(item, "is_failed", False) or getattr(item, "error", None):
                        failed_pages.add(page_no)
                    else:
                        completed_pages.add(page_no)
                    progress_callback(len(completed_pages | failed_pages), total_pages, "pages")
                return original_emit(materialized_items)

            assemble_stage._emit = MethodType(emit_with_progress, assemble_stage)
            return ctx

        pipeline._create_run_ctx = create_run_ctx_with_progress
        try:
            result = original_build_document(conv_res)
            if total_pages > 0:
                progress_callback(total_pages, total_pages, "done")
            return result
        finally:
            pipeline._create_run_ctx = original_create_run_ctx

    pipeline._build_document = build_document_with_progress
    return converter


def convert_pdf_with_docling_local(
    pdf_path: Path,
    *,
    progress_callback: PdfProgressCallback | None = None,
    low_memory: bool = False,
) -> object:
    converter = build_docling_converter_with_progress(
        progress_callback,
        low_memory=low_memory,
    )
    return converter.convert(str(pdf_path), raises_on_error=False)


def convert_pdf_with_docling_fallback(
    pdf_path: Path,
    *,
    progress_callback: PdfProgressCallback | None = None,
) -> object:
    page_count = get_pdf_page_count_for_docling(pdf_path)
    file_size_bytes = pdf_path.stat().st_size if pdf_path.exists() else None
    prefer_low_memory = should_use_low_memory_docling(page_count, file_size_bytes)
    attempt_profiles = [True] if prefer_low_memory else [False, True]
    last_result: object | None = None

    for low_memory in attempt_profiles:
        conversion_result = convert_pdf_with_docling_local(
            pdf_path,
            progress_callback=progress_callback,
            low_memory=low_memory,
        )
        last_result = conversion_result
        if conversion_status_name(conversion_result) == "success":
            return conversion_result

    if last_result is None:
        raise RuntimeError("Docling did not return a conversion result.")
    return last_result


def serialize_unit_hints(unit_hints: list[UnitHint]) -> list[dict[str, Any]]:
    return [
        {
            "title": hint.title,
            "heading_level": hint.heading_level,
            "page_start": hint.page_start,
            "page_end": hint.page_end,
            "content_type": hint.content_type,
        }
        for hint in unit_hints
    ]


def deserialize_unit_hints(raw_hints: list[dict[str, Any]] | None) -> list[UnitHint]:
    hints: list[UnitHint] = []
    for entry in raw_hints or []:
        title = str(entry.get("title", "")).strip()
        if not title:
            continue
        hints.append(
            UnitHint(
                title=title,
                heading_level=int(entry.get("heading_level", 2)),
                page_start=_coerce_optional_int(entry.get("page_start")),
                page_end=_coerce_optional_int(entry.get("page_end")),
                content_type=str(entry.get("content_type", "section")).strip() or "section",
            )
        )
    return hints


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_docling_serve_convert_url() -> str:
    base_url = DOCLING_SERVE_URL.strip().rstrip("/")
    if not base_url:
        return ""
    if base_url.endswith("/v1/convert/source"):
        return base_url
    return f"{base_url}/v1/convert/source"


def extract_docling_serve_error(payload: dict[str, Any]) -> str:
    errors = payload.get("errors")
    if isinstance(errors, list):
        parts: list[str] = []
        for entry in errors:
            if isinstance(entry, str) and entry.strip():
                parts.append(entry.strip())
            elif isinstance(entry, dict):
                message = str(entry.get("message", "")).strip()
                if message:
                    parts.append(message)
        if parts:
            return " | ".join(parts)
    detail = str(payload.get("detail", "")).strip()
    return detail


def iterate_docling_json_items(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        if "label" in node and any(key in node for key in ("text", "orig", "orig_text", "raw_text", "title", "name")):
            yield node
        for value in node.values():
            yield from iterate_docling_json_items(value)
        return
    if isinstance(node, list):
        for entry in node:
            yield from iterate_docling_json_items(entry)


def extract_docling_unit_hints_from_json_content(json_content: dict[str, Any] | None) -> list[UnitHint]:
    if not isinstance(json_content, dict):
        return []
    return extract_docling_unit_hints_from_items(
        iterate_docling_json_items(json_content),
        allow_empty_fallback=False,
    )


def write_pdf_artifacts(
    pdf_path: Path,
    markdown_text: str,
    unit_hints: list[UnitHint],
    *,
    artifact_dir: Path | None,
) -> None:
    if artifact_dir is None:
        return

    artifact_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_path, artifact_dir / "original.pdf")

    docling_dir = artifact_dir / "docling"
    docling_dir.mkdir(parents=True, exist_ok=True)
    (docling_dir / "source.md").write_text(markdown_text, encoding="utf-8")
    (docling_dir / "outline.json").write_text(
        json.dumps(serialize_unit_hints(unit_hints), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_pdf_source(
    source_path: str,
    *,
    artifact_dir: Path | None = None,
    progress_callback: PdfProgressCallback | None = None,
) -> tuple[str, str, list[UnitHint]]:
    if DOCLING_PDF_BACKEND == "local":
        if progress_callback is None:
            return load_pdf_source_local(
                source_path,
                artifact_dir=artifact_dir,
            )
        return load_pdf_source_local(
            source_path,
            artifact_dir=artifact_dir,
            progress_callback=progress_callback,
        )
    if DOCLING_PDF_BACKEND != "remote":
        raise ValueError(
            "`DOCLING_PDF_BACKEND` 只接受 `local` 或 `remote`。"
        )
    if not resolve_docling_serve_convert_url():
        raise ValueError(
            "目前 `DOCLING_PDF_BACKEND=remote`，但尚未設定 `DOCLING_SERVE_URL=http://<server>:5001`。"
        )
    if progress_callback is None:
        return load_pdf_source_remote(source_path, artifact_dir=artifact_dir)
    return load_pdf_source_remote(source_path, artifact_dir=artifact_dir, progress_callback=progress_callback)


def load_pdf_source_local(
    source_path: str,
    *,
    artifact_dir: Path | None = None,
    progress_callback: PdfProgressCallback | None = None,
) -> tuple[str, str, list[UnitHint]]:
    pdf_path = Path(source_path).expanduser()
    if not pdf_path.exists():
        raise ValueError(f"找不到 PDF 檔案：{pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("PDF 匯入只接受副檔名為 `.pdf` 的本地檔案。")

    try:
        conversion_result = convert_pdf_with_docling_fallback(
            pdf_path,
            progress_callback=progress_callback,
        )
    except Exception as exc:  # pragma: no cover - depends on local Docling runtime
        if DOCLING_PDF_OCR_ENABLED:
            missing_models = missing_easyocr_model_files(DOCLING_EASYOCR_DIR, DOCLING_EASYOCR_LANGS)
        else:
            missing_models = []
        if missing_models:
            missing_display = "、".join(missing_models)
            raise ValueError(
                "Docling 無法完成這份 PDF 的本地解析。"
                f"目前缺少這些 EasyOCR 模型：{missing_display}。"
                "請先執行 "
                "`.venv\\Scripts\\python.exe scripts\\bootstrap_docling_easyocr.py --allow-insecure-fallback`。"
            ) from exc
        raise ValueError(
            "Docling 無法完成這份 PDF 的本地解析。"
            "請確認 Docling 模型已準備完成；若這份 PDF 有掃描頁面，也請確認 EasyOCR 模型已下載完成，再重試一次。"
        ) from exc

    ensure_complete_pdf_conversion(conversion_result)
    document = getattr(conversion_result, "document", None)
    if document is None:
        raise ValueError("Docling 沒有回傳可用的文件結果，無法建立這份 PDF 的學習單元。")

    markdown_text = document.export_to_markdown().strip()
    if not markdown_text:
        raise ValueError("Docling 沒有從這份 PDF 解析出可用的文字內容。")

    unit_hints = extract_docling_unit_hints(document)
    write_pdf_artifacts(pdf_path, markdown_text, unit_hints, artifact_dir=artifact_dir)
    return markdown_text, str(pdf_path), unit_hints


def load_pdf_source_remote(
    source_path: str,
    *,
    artifact_dir: Path | None = None,
    progress_callback: PdfProgressCallback | None = None,
) -> tuple[str, str, list[UnitHint]]:
    pdf_path = Path(source_path).expanduser()
    if not pdf_path.exists():
        raise ValueError(f"找不到 PDF 檔案：{pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("PDF 匯入只接受副檔名為 `.pdf` 的本地檔案。")

    convert_url = resolve_docling_serve_convert_url()
    payload = {
        "sources": [
            {
                "kind": "file",
                "filename": pdf_path.name,
                "base64_string": base64.b64encode(pdf_path.read_bytes()).decode("ascii"),
            }
        ],
        "options": {
            "to_formats": ["md", "json"],
        },
    }
    headers = {
        "Accept": "application/json",
    }
    if DOCLING_SERVE_API_KEY:
        headers["X-API-Key"] = DOCLING_SERVE_API_KEY

    try:
        response = requests.post(
            convert_url,
            json=payload,
            headers=headers,
            timeout=DOCLING_REMOTE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        response_payload = response.json()
    except requests.HTTPError as exc:
        detail = ""
        if exc.response is not None:
            detail = exc.response.text.strip()
            status_code = exc.response.status_code
        else:
            status_code = "unknown"
        if detail:
            raise ValueError(
                f"官方 docling-serve 回傳 {status_code}。"
                f"請檢查 `{convert_url}` 是否可用。詳細訊息：{detail}"
            ) from exc
        raise ValueError(
            f"官方 docling-serve 回傳 {status_code}。請檢查 `{convert_url}` 是否可用。"
        ) from exc
    except requests.ConnectionError as exc:
        raise ValueError(
            "無法連上官方 docling-serve。"
            f"請確認 `DOCLING_SERVE_URL={DOCLING_SERVE_URL}` 正確，且服務已啟動。"
        ) from exc
    except requests.Timeout as exc:
        raise ValueError(
            "官方 docling-serve 逾時。"
            f"可考慮調大 `DOCLING_REMOTE_TIMEOUT_SECONDS`，目前是 {DOCLING_REMOTE_TIMEOUT_SECONDS} 秒。"
        ) from exc

    error_message = extract_docling_serve_error(response_payload)
    if error_message:
        raise ValueError(f"官方 docling-serve 沒有成功完成這份 PDF 的解析：{error_message}")

    document_payload = response_payload.get("document")
    if not isinstance(document_payload, dict):
        raise ValueError("官方 docling-serve 沒有回傳 `document` 結果。")

    markdown_text = str(document_payload.get("md_content", "")).strip()
    if not markdown_text:
        raise ValueError("官方 docling-serve 沒有回傳可用的 Markdown 內容。")

    json_content = document_payload.get("json_content")
    if isinstance(json_content, str):
        try:
            json_content = json.loads(json_content)
        except json.JSONDecodeError:
            json_content = None

    unit_hints = extract_docling_unit_hints_from_json_content(json_content)
    if not unit_hints:
        unit_hints = [
            UnitHint(
                title="PDF 解析內容",
                heading_level=2,
                page_start=1,
                page_end=1,
                content_type="section",
            )
        ]

    write_pdf_artifacts(pdf_path, markdown_text, unit_hints, artifact_dir=artifact_dir)
    return markdown_text, str(pdf_path), unit_hints


def extract_docling_unit_hints(document: object) -> list[UnitHint]:
    return extract_docling_unit_hints_from_items(
        iterate_docling_items(document),
        allow_empty_fallback=True,
    )


def _copy_unit_hint(hint: UnitHint) -> UnitHint:
    return UnitHint(
        title=hint.title,
        heading_level=hint.heading_level,
        page_start=hint.page_start,
        page_end=hint.page_end,
        content_type=hint.content_type,
    )


def _unit_hint_page_extent(hint: UnitHint) -> int | None:
    if hint.page_end is not None:
        return hint.page_end
    return hint.page_start


def expand_hierarchical_unit_hint_ranges(unit_hints: list[UnitHint]) -> list[UnitHint]:
    expanded_hints = [_copy_unit_hint(hint) for hint in unit_hints]
    ancestor_stack: list[int] = []

    for index, hint in enumerate(expanded_hints):
        while ancestor_stack and expanded_hints[ancestor_stack[-1]].heading_level >= hint.heading_level:
            ancestor_stack.pop()

        current_extent = _unit_hint_page_extent(hint)
        if current_extent is not None:
            for ancestor_index in ancestor_stack:
                ancestor_hint = expanded_hints[ancestor_index]
                ancestor_extent = _unit_hint_page_extent(ancestor_hint)
                if ancestor_hint.page_start is None:
                    ancestor_hint.page_start = hint.page_start
                if ancestor_extent is None or current_extent > ancestor_extent:
                    ancestor_hint.page_end = max(current_extent, ancestor_hint.page_start or current_extent)

        ancestor_stack.append(index)

    return expanded_hints


def extract_docling_unit_hints_from_items(
    items: Iterable[Any],
    *,
    allow_empty_fallback: bool,
) -> list[UnitHint]:
    collected_hints: list[UnitHint] = []
    current_hint: UnitHint | None = None
    current_pages: set[int] = set()
    max_page = 1

    def finalize_current_hint() -> None:
        nonlocal current_hint, current_pages
        if current_hint is None:
            return

        if current_pages:
            if current_hint.page_start is None:
                current_hint.page_start = min(current_pages)
            current_hint.page_end = max(max(current_pages), current_hint.page_start or 1)
        elif current_hint.page_start is not None:
            current_hint.page_end = current_hint.page_start
        else:
            current_hint.page_start = 1
            current_hint.page_end = max_page

        collected_hints.append(current_hint)
        current_hint = None
        current_pages = set()

    for item in items:
        pages = extract_page_numbers(item)
        if pages:
            max_page = max(max_page, max(pages))

        text = extract_item_text(item)
        if not text:
            continue

        if is_heading_like(item, text):
            title = clean_heading_title(text)
            if not title:
                continue

            normalized_title = normalize_title(title)
            if current_hint is not None and normalize_title(current_hint.title) == normalized_title:
                current_pages.update(pages)
                if current_hint.page_start is None and pages:
                    current_hint.page_start = min(pages)
                continue

            finalize_current_hint()
            current_hint = UnitHint(
                title=title,
                heading_level=infer_heading_level(item, title),
                page_start=min(pages) if pages else None,
                content_type=infer_content_type(title),
            )
            current_pages = set(pages)
            continue

        if current_hint is not None:
            current_pages.update(pages)

    finalize_current_hint()

    if collected_hints:
        return expand_hierarchical_unit_hint_ranges(collected_hints)
    if not allow_empty_fallback:
        return []

    return [
        UnitHint(
            title="PDF 瑙ｆ瀽鍏у",
            heading_level=2,
            page_start=1,
            page_end=max_page,
            content_type="section",
        )
    ]


def iterate_docling_items(document: object) -> Iterable[Any]:
    iterator = getattr(document, "iterate_items", None)
    if not callable(iterator):
        return []

    items = iterator()
    for entry in items:
        if isinstance(entry, tuple):
            yield entry[0]
        else:
            yield entry


def extract_item_text(item: object) -> str:
    if isinstance(item, dict):
        for attr_name in ("text", "orig", "orig_text", "raw_text", "title", "name"):
            value = item.get(attr_name)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    for attr_name in ("text", "orig", "orig_text", "raw_text", "title", "name"):
        value = getattr(item, attr_name, None)
        if isinstance(value, str) and value.strip():
            return value.strip()

    export_to_markdown = getattr(item, "export_to_markdown", None)
    if callable(export_to_markdown):
        try:
            value = export_to_markdown()
        except TypeError:
            value = ""
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def extract_page_numbers(item: object) -> list[int]:
    page_numbers: list[int] = []
    provenance_entries = item.get("prov", []) if isinstance(item, dict) else (getattr(item, "prov", None) or [])
    for entry in provenance_entries:
        if isinstance(entry, dict):
            page_no = entry.get("page_no")
        else:
            page_no = getattr(entry, "page_no", None)
        if isinstance(page_no, int) and page_no > 0:
            page_numbers.append(page_no)
    return sorted(set(page_numbers))


def extract_item_label(item: object) -> Any:
    if isinstance(item, dict):
        return item.get("label", "")
    return getattr(item, "label", "")


def conversion_status_name(conversion_result: object) -> str:
    raw_status = getattr(conversion_result, "status", "")
    if isinstance(raw_status, str):
        return raw_status.strip().lower()
    return str(raw_status).split(".")[-1].strip().lower()


def extract_conversion_error_messages(conversion_result: object) -> list[str]:
    messages: list[str] = []
    for error in getattr(conversion_result, "errors", []) or []:
        message = getattr(error, "error_message", "")
        if isinstance(message, str) and message.strip():
            messages.append(message.strip())
    return messages


def extract_failed_page_numbers(error_messages: Iterable[str]) -> list[int]:
    page_numbers: set[int] = set()
    for message in error_messages:
        match = FAILED_PAGE_PATTERN.search(message)
        if match:
            page_numbers.add(int(match.group(1)))
    return sorted(page_numbers)


def ensure_complete_pdf_conversion(conversion_result: object) -> None:
    status_name = conversion_status_name(conversion_result)
    if status_name == "success":
        return

    error_messages = extract_conversion_error_messages(conversion_result)
    total_pages = int(getattr(getattr(conversion_result, "input", None), "page_count", 0) or 0)
    parsed_pages = len(getattr(conversion_result, "pages", []) or [])
    failed_pages = extract_failed_page_numbers(error_messages)

    if status_name == "partial_success":
        detail_parts: list[str] = []
        if total_pages > 0:
            detail_parts.append(f"成功頁數 {parsed_pages}/{total_pages}")
        if failed_pages:
            preview = ", ".join(str(page_no) for page_no in failed_pages[:8])
            if len(failed_pages) > 8:
                preview += " ..."
            detail_parts.append(f"失敗頁面 {len(failed_pages)} 頁（例如 {preview}）")
        detail = f" {'；'.join(detail_parts)}。" if detail_parts else ""
        raise ValueError(
            "Docling 只完成了部分 PDF 解析，系統已停止匯入，避免用殘缺內容建立學習任務。"
            f"{detail}"
        )

    first_error = error_messages[0] if error_messages else "Docling 沒有回傳可用結果。"
    raise ValueError(f"Docling 未能完成這份 PDF 的解析：{first_error}")


def is_heading_like(item: object, text: str) -> bool:
    label = normalize_label(extract_item_label(item))
    if any(keyword in label for keyword in HEADING_LABEL_KEYWORDS):
        return True

    normalized_text = clean_heading_title(text)
    if len(normalized_text) > 160:
        return False

    return looks_like_structural_unit_title(normalized_text)


def infer_heading_level(item: object, text: str) -> int:
    label = normalize_label(extract_item_label(item))
    if "title" in label:
        return 1

    normalized_text = clean_heading_title(text)
    if re.match(r"^第[\d一二三四五六七八九十百千零两]+章", normalized_text):
        return 1
    if re.match(r"^(chapter|part)\s+(?:\d+(?:\.\d+)*|[ivxlcdm]+|[a-z])(?:\b|[).:-])", normalized_text, re.IGNORECASE):
        return 1
    if re.match(r"^\d+\.\d+\.\d+\b", normalized_text):
        return 3
    if re.match(r"^第[\d一二三四五六七八九十百千零两]+节", normalized_text):
        return 2
    if re.match(r"^section\s+(?:\d+(?:\.\d+)*|[ivxlcdm]+|[a-z])(?:\b|[).:-])", normalized_text, re.IGNORECASE):
        return 2
    if re.match(r"^\d+\.\d+\b", normalized_text):
        return 2
    if infer_content_type(normalized_text) != "section":
        return 3
    return 2


def clean_heading_title(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip())
    normalized = normalized.strip("*#`> ")
    return normalized


def normalize_label(label: Any) -> str:
    if isinstance(label, dict):
        raw_value = label.get("value", label)
        return str(raw_value).split(".")[-1].strip().lower()
    raw_value = getattr(label, "value", label)
    return str(raw_value).split(".")[-1].strip().lower()


def normalize_title(text: str) -> str:
    return clean_heading_title(text).casefold()
