from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy.orm import Session

from .config import PROJECT_ROOT, ensure_runtime_dirs
from .db import get_session, initialize_database
from .models import LearningUnit, Resource
from .services.pdf_page_viewer import (
    get_available_unit_pdf_page_numbers,
    get_or_create_unit_pdf_preview_page,
    get_or_render_pdf_page,
    get_or_create_unit_pdf_subset,
    get_original_pdf_path,
)
from .services.import_jobs import (
    ImportJobPayload,
    create_import_job,
    get_import_job,
    list_recent_import_jobs,
)
from .services.settings_service import get_app_settings, update_app_settings
from .services.study_service import (
    complete_daily_task,
    complete_review_task,
    content_has_math,
    get_daily_task,
    get_dashboard_summary,
    get_resource,
    get_review_task,
    render_markdown,
    review_is_available,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_runtime_dirs()
    initialize_database()
    yield


app = FastAPI(
    title="Learning Supervisor",
    description="以 PDF 為核心的本地學習與複習工作流。",
    lifespan=lifespan,
)

initialize_database()
app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "app" / "static"), name="static")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))
STATIC_DIR = PROJECT_ROOT / "app" / "static"

SETTINGS_THEME_OPTIONS = (
    ("reader", "閱讀紙頁 | 更接近書頁閱讀感"),
    ("frost", "霧面玻璃 | 冷色半透明材質"),
)
SETTINGS_DENSITY_OPTIONS = (
    ("immersive", "沉浸 | 更寬鬆、更強調聚焦"),
    ("balanced", "平衡 | 兼顧資訊量與留白"),
    ("compact", "緊湊 | 更高密度的儀表板排版"),
)
SETTINGS_MOTION_OPTIONS = (
    ("full", "完整 | 保留主要動效與轉場"),
    ("soft", "柔和 | 降低動效強度"),
    ("minimal", "極簡 | 只保留必要動作"),
)
SETTINGS_THEME_LABELS = {
    "reader": "閱讀紙頁",
    "frost": "霧面玻璃",
}
SETTINGS_MOTION_LABELS = {
    "full": "完整",
    "soft": "柔和",
    "minimal": "極簡",
}
PDF_INLINE_PREVIEW_PAGE_LIMIT = 2


def _static_version(path: str) -> str:
    file_path = STATIC_DIR / path
    if not file_path.exists():
        return "0"
    return str(int(file_path.stat().st_mtime))


def render_template(request: Request, template_name: str, context: dict, session: Session) -> object:
    app_settings = context.get("app_settings") or get_app_settings(session)
    context.update(
        {
            "request": request,
            "today": date.today(),
            "app_settings": app_settings,
            "css_version": _static_version("app.css"),
            "js_version": _static_version("app.js"),
        }
    )
    return templates.TemplateResponse(template_name, context)


def _settings_form_values(app_settings: object) -> dict:
    return {
        "default_priority": app_settings.default_priority,
        "default_learning_mode": app_settings.default_learning_mode,
        "review_intervals_csv": app_settings.review_intervals_csv,
        "low_confidence_followup_days": app_settings.low_confidence_followup_days,
        "allow_weekend_scheduling": app_settings.allow_weekend_scheduling,
        "render_math_enabled": app_settings.render_math_enabled,
        "study_material_theme": app_settings.study_material_theme,
        "dashboard_density": app_settings.dashboard_density,
        "motion_level": app_settings.motion_level,
        "queue_preview_count_study": app_settings.queue_preview_count_study,
        "queue_preview_count_review": app_settings.queue_preview_count_review,
        "dashboard_hero_title_text": app_settings.dashboard_hero_title_text,
        "dashboard_hero_title_size_px": app_settings.dashboard_hero_title_size_px,
        "dashboard_major_event_content": app_settings.dashboard_major_event_content or "",
        "dashboard_major_event_date": (
            app_settings.dashboard_major_event_date.isoformat()
            if app_settings.dashboard_major_event_date
            else ""
        ),
    }


def _settings_template_context(app_settings: object, **extra_context: object) -> dict:
    context = {
        "settings_form": _settings_form_values(app_settings),
        "theme_options": SETTINGS_THEME_OPTIONS,
        "density_options": SETTINGS_DENSITY_OPTIONS,
        "motion_options": SETTINGS_MOTION_OPTIONS,
        "theme_labels": SETTINGS_THEME_LABELS,
        "motion_labels": SETTINGS_MOTION_LABELS,
        "app_settings": app_settings,
    }
    context.update(extra_context)
    return context


def _unit_material_context(unit: object) -> dict:
    pdf_document_path = get_original_pdf_path(unit.resource)
    pdf_page_numbers = get_available_unit_pdf_page_numbers(unit) if pdf_document_path is not None else []
    pdf_page_count = len(pdf_page_numbers)
    pdf_inline_preview_pages = [
        {
            "document_page_number": index + 1,
            "source_page_number": page_number,
            "preview_url": f"/units/{unit.id}/pdf-preview/{page_number}",
        }
        for index, page_number in enumerate(pdf_page_numbers[:PDF_INLINE_PREVIEW_PAGE_LIMIT])
    ]
    return {
        "content_html": Markup(render_markdown(unit.content_markdown)),
        "has_math_content": content_has_math(unit.content_markdown),
        "pdf_page_numbers": pdf_page_numbers,
        "pdf_viewer_page_numbers": list(range(1, pdf_page_count + 1)),
        "pdf_available": bool(pdf_page_numbers),
        "pdf_page_count": pdf_page_count,
        "pdf_has_multiple_pages": pdf_page_count > 1,
        "pdf_inline_preview_pages": pdf_inline_preview_pages,
        "pdf_document_url": (
            f"/units/{unit.id}/pdf"
            if pdf_page_numbers
            else ""
        ),
    }


def _dashboard_hero_title_lines(app_settings: object) -> list[str]:
    raw_value = str(getattr(app_settings, "dashboard_hero_title_text", "") or "").strip()
    lines = [line.strip() for line in raw_value.splitlines() if line.strip()]
    return lines or ["今日學習總覽"]


def _dashboard_major_event_context(app_settings: object, today: date) -> dict:
    content = str(getattr(app_settings, "dashboard_major_event_content", "") or "").strip()
    event_date = getattr(app_settings, "dashboard_major_event_date", None)
    if not content or event_date is None:
        return {
            "has_event": False,
            "content": "",
            "date_label": "",
            "message": "最近沒有重大事件",
        }

    delta_days = (event_date - today).days
    if delta_days > 0:
        message = f"距離「{content}」還有 {delta_days} 天"
    elif delta_days == 0:
        message = f"「{content}」就是今天"
    else:
        message = f"距離「{content}」已經過去了 {-delta_days} 天"

    return {
        "has_event": True,
        "content": content,
        "date_label": event_date.isoformat(),
        "message": message,
    }


@app.get("/")
def dashboard(request: Request, session: Session = Depends(get_session)):
    summary = get_dashboard_summary(session)
    app_settings = get_app_settings(session)
    return render_template(
        request,
        "dashboard.html",
        {
            "summary": summary,
            "app_settings": app_settings,
            "recent_import_jobs": list_recent_import_jobs(),
            "dashboard_hero_title_lines": _dashboard_hero_title_lines(app_settings),
            "dashboard_major_event": _dashboard_major_event_context(app_settings, summary.today),
        },
        session,
    )


@app.get("/resources/new")
def new_resource(request: Request, session: Session = Depends(get_session)):
    active_import_job_id = request.query_params.get("job", "").strip()
    return render_template(
        request,
        "resource_form.html",
        {
            "active_import_job_id": active_import_job_id,
        },
        session,
    )


@app.post("/resources")
def create_resource(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    source_path: str = Form(""),
    deadline: str = Form(...),
    priority: int = Form(2),
    learning_mode: str = Form("application"),
):
    try:
        payload = ImportJobPayload(
            title=title,
            description=description,
            source_path=source_path,
            deadline=deadline,
            priority=priority,
            learning_mode=learning_mode,
        )
        date.fromisoformat(payload.deadline)
        job_state = create_import_job(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response_payload = {
        "job_id": job_state["job_id"],
        "status": job_state["status"],
        "progress_percent": job_state["progress_percent"],
        "status_label": job_state["status_label"],
        "detail": job_state["detail"],
    }
    if request.headers.get("x-learning-supervisor-import") == "async":
        return JSONResponse(response_payload, status_code=status.HTTP_202_ACCEPTED)

    return RedirectResponse(url=f"/resources/new?job={job_state['job_id']}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/imports/{job_id}")
def import_job_status(job_id: str):
    job_state = get_import_job(job_id)
    if job_state is None:
        raise HTTPException(status_code=404, detail="找不到這個匯入任務。")
    return JSONResponse(job_state)


@app.get("/resources/{resource_id}")
def resource_detail(resource_id: str, request: Request, session: Session = Depends(get_session)):
    resource = get_resource(session, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="找不到這份學習資源。")
    return render_template(
        request,
        "resource_detail.html",
        {
            "resource": resource,
            "render_markdown": render_markdown,
            "Markup": Markup,
        },
        session,
    )


@app.get("/tasks/{task_id}")
def study_task_detail(task_id: str, request: Request, session: Session = Depends(get_session)):
    task = get_daily_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到這個學習任務。")
    material_context = _unit_material_context(task.unit)
    return render_template(
        request,
        "task_detail.html",
        {
            "task": task,
            "task_kind": "study",
            **material_context,
        },
        session,
    )


@app.post("/tasks/{task_id}/complete")
def submit_study_task(
    task_id: str,
    summary_text: str = Form(...),
    reflection_note: str = Form(""),
    confidence_score: int = Form(...),
    completion_percent: int = Form(...),
    session: Session = Depends(get_session),
):
    try:
        task = complete_daily_task(
            session,
            task_id=task_id,
            summary_text=summary_text,
            reflection_note=reflection_note,
            confidence_score=confidence_score,
            completion_percent=completion_percent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RedirectResponse(url=f"/resources/{task.unit.resource.id}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/reviews/{review_id}")
def review_task_detail(review_id: str, request: Request, session: Session = Depends(get_session)):
    review = get_review_task(session, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="找不到這個複習任務。")
    if review.status != "completed" and not review_is_available(review):
        raise HTTPException(status_code=403, detail="這個複習任務尚未解鎖。")
    material_context = _unit_material_context(review.unit)
    return render_template(
        request,
        "review_detail.html",
        {
            "review": review,
            "task_kind": "review",
            **material_context,
        },
        session,
    )


@app.get("/resources/{resource_id}/pdf-pages/{page_number}.png")
def resource_pdf_page(resource_id: str, page_number: int, session: Session = Depends(get_session)):
    resource = session.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="找不到資源。")

    try:
        image_path = get_or_render_pdf_page(resource, page_number)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(image_path, media_type="image/png")


@app.get("/resources/{resource_id}/original.pdf")
def resource_original_pdf(resource_id: str, session: Session = Depends(get_session)):
    resource = session.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="鎵句笉鍒拌硣婧愩€?")

    pdf_path = get_original_pdf_path(resource)
    if pdf_path is None:
        raise HTTPException(status_code=404, detail="姝や換鍕欑殑鍘熷 PDF 涓嶅彲鐢ㄣ€?")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{pdf_path.name}"'},
    )


@app.get("/units/{unit_id}/pdf")
def unit_pdf_subset(unit_id: str, session: Session = Depends(get_session)):
    unit = session.get(LearningUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="找不到這個學習單元。")

    try:
        pdf_path = get_or_create_unit_pdf_subset(unit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{pdf_path.name}"'},
    )


@app.head("/units/{unit_id}/pdf")
def unit_pdf_subset_head(unit_id: str, session: Session = Depends(get_session)):
    unit = session.get(LearningUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="找不到這個學習單元。")

    try:
        pdf_path = get_or_create_unit_pdf_subset(unit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(
        content=b"",
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{pdf_path.name}"',
            "Content-Length": str(pdf_path.stat().st_size),
            "Accept-Ranges": "bytes",
        },
    )


@app.get("/units/{unit_id}/pdf-preview/{page_number}")
def unit_pdf_preview_page(unit_id: str, page_number: int, session: Session = Depends(get_session)):
    unit = session.get(LearningUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="找不到這個學習單元。")

    try:
        pdf_path = get_or_create_unit_pdf_preview_page(unit, page_number)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{pdf_path.name}"'},
    )


@app.head("/units/{unit_id}/pdf-preview/{page_number}")
def unit_pdf_preview_page_head(unit_id: str, page_number: int, session: Session = Depends(get_session)):
    unit = session.get(LearningUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="找不到這個學習單元。")

    try:
        pdf_path = get_or_create_unit_pdf_preview_page(unit, page_number)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(
        content=b"",
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{pdf_path.name}"',
            "Content-Length": str(pdf_path.stat().st_size),
            "Accept-Ranges": "bytes",
        },
    )


@app.head("/resources/{resource_id}/original.pdf")
def resource_original_pdf_head(resource_id: str, session: Session = Depends(get_session)):
    resource = session.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="鎵句笉鍒拌硣婧愩€?")

    pdf_path = get_original_pdf_path(resource)
    if pdf_path is None:
        raise HTTPException(status_code=404, detail="姝や換鍕欑殑鍘熷 PDF 涓嶅彲鐢ㄣ€?")

    return Response(
        content=b"",
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{pdf_path.name}"',
            "Content-Length": str(pdf_path.stat().st_size),
            "Accept-Ranges": "bytes",
        },
    )


@app.post("/reviews/{review_id}/complete")
def submit_review_task(
    review_id: str,
    summary_text: str = Form(...),
    reflection_note: str = Form(""),
    confidence_score: int = Form(...),
    session: Session = Depends(get_session),
):
    app_settings = get_app_settings(session)
    try:
        review = complete_review_task(
            session,
            review_id=review_id,
            summary_text=summary_text,
            reflection_note=reflection_note,
            confidence_score=confidence_score,
            low_confidence_followup_days=app_settings.low_confidence_followup_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RedirectResponse(url=f"/resources/{review.unit.resource.id}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/settings")
def settings_page(request: Request, session: Session = Depends(get_session)):
    app_settings = get_app_settings(session)
    success_message = None
    if request.query_params.get("saved") == "1":
        success_message = "設定已儲存。新的資源匯入與頁面顯示會套用這份設定。"
    return render_template(
        request,
        "settings.html",
        _settings_template_context(app_settings, success_message=success_message),
        session,
    )


@app.post("/settings")
def save_settings(
    request: Request,
    default_priority: int = Form(2),
    default_learning_mode: str = Form("application"),
    review_intervals_csv: str = Form("1,3,7,14"),
    low_confidence_followup_days: int = Form(2),
    allow_weekend_scheduling: bool = Form(False),
    render_math_enabled: bool = Form(False),
    study_material_theme: str = Form("reader"),
    dashboard_density: str = Form("balanced"),
    motion_level: str = Form("full"),
    queue_preview_count_study: int = Form(8),
    queue_preview_count_review: int = Form(6),
    dashboard_hero_title_text: str = Form("今日學習總覽"),
    dashboard_hero_title_size_px: int = Form(72),
    dashboard_major_event_content: str = Form(""),
    dashboard_major_event_date: str = Form(""),
    session: Session = Depends(get_session),
):
    current_settings = get_app_settings(session)
    submitted_values = {
        "default_priority": default_priority,
        "default_learning_mode": default_learning_mode,
        "review_intervals_csv": review_intervals_csv,
        "low_confidence_followup_days": low_confidence_followup_days,
        "allow_weekend_scheduling": allow_weekend_scheduling,
        "render_math_enabled": render_math_enabled,
        "study_material_theme": study_material_theme,
        "dashboard_density": dashboard_density,
        "motion_level": motion_level,
        "queue_preview_count_study": queue_preview_count_study,
        "queue_preview_count_review": queue_preview_count_review,
        "dashboard_hero_title_text": dashboard_hero_title_text,
        "dashboard_hero_title_size_px": dashboard_hero_title_size_px,
        "dashboard_major_event_content": dashboard_major_event_content,
        "dashboard_major_event_date": dashboard_major_event_date,
    }

    try:
        update_app_settings(
            session,
            default_priority=default_priority,
            default_learning_mode=default_learning_mode,
            review_intervals_csv=review_intervals_csv,
            low_confidence_followup_days=low_confidence_followup_days,
            allow_weekend_scheduling=allow_weekend_scheduling,
            render_math_enabled=render_math_enabled,
            study_material_theme=study_material_theme,
            dashboard_density=dashboard_density,
            motion_level=motion_level,
            queue_preview_count_study=queue_preview_count_study,
            queue_preview_count_review=queue_preview_count_review,
            dashboard_hero_title_text=dashboard_hero_title_text,
            dashboard_hero_title_size_px=dashboard_hero_title_size_px,
            dashboard_major_event_content=dashboard_major_event_content,
            dashboard_major_event_date=dashboard_major_event_date,
        )
    except ValueError as exc:
        return render_template(
            request,
            "settings.html",
            _settings_template_context(
                current_settings,
                error_message=str(exc),
                settings_form=submitted_values,
            ),
            session,
        )

    return RedirectResponse(url="/settings?saved=1", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/health")
def health_check():
    return {"status": "ok"}
