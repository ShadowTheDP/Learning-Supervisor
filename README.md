# Learning-Supervisor

## Purpose

This repository is a local-first single-user learning supervision project.

It is meant to help one person finish studying and reviewing source material
such as PDFs before a chosen deadline, with room for future URL ingestion.

The product is not a team or classroom platform. Its job is to turn raw study
material into daily learning tasks, review sessions, and accountability
records.

## Current Status

This repo now has a runnable local-only single-user web app.

Tracked today:

- the project purpose
- a FastAPI application shell
- SQLite models for resources, learning units, study tasks, review tasks, and
  check-ins
- PDF import from local `.pdf` files through local Docling, with
  chapter/page-range hints propagated into learning units
- background import jobs for long PDF parsing, with persisted job state and
  worker logs under `data/state/import_jobs/`
- Docling-linked import progress updates, plus automatic failure repair when a
  background worker exits early
- deadline-based task scheduling
- server-rendered dashboard, import flow, study flow, and review flow
- adjustable study-task timer UI with extend / early-finish controls
- chapter-scoped PDF reading on study and review pages, where the left column
  shows only the first two preview pages and click-to-open reading uses the
  original PDF bytes for that unit's page range
- corrected task-mode display for application versus dictation work
- unit tests for unit splitting, PDF structure hints, labels, scheduling,
  import-job state, and PDF page viewing

Still not implemented:

- URL ingestion
- reminder notifications
- AI-assisted question generation
- adaptive review scheduling beyond fixed intervals

## Current Agent Handoff

If a later AI agent takes over this repo, do not rely on old chat context
alone. Start here, then confirm against the current files.

Read in this order:

1. This `README.md`
2. `AGENTS.md`
3. `MEMORY.md`
4. `docs/agent/current-state.md`
5. `Changing Description.txt` only when historical detail is needed
6. `app/static/app.js` and `app/static/app.css` when the task touches UI or
   motion
7. The relevant template or backend file for the current task

Current reality as of 2026-06-27:

- The app is already a runnable Chinese local web app, not just an MVP plan.
- The product is intentionally single-user, localhost-first, and should not
  read like a commercial landing page.
- The import and settings pages are intentionally kept as centered panels
  because the user likes the way they interact with the animated background.
- Docling is still the core PDF parser. Do not replace it unless a human
  explicitly changes that decision.
- The most active runtime work is currently long-PDF import stability plus
  study/review PDF presentation, not a broad UI redesign.
- PDF ingest now defaults back to local Docling execution, with formula
  enrichment disabled by default to reduce local load, EasyOCR kept as an
  optional local OCR layer for scanned pages, and remote `docling-serve`
  preserved only as an explicit fallback backend.
- Importing a PDF now creates a background job. The browser polls
  `data/state/import_jobs/`-backed state instead of holding the main request
  open, so navigation and reload are recoverable during long parsing runs.
- Study and review pages now keep the left preview clean by rendering only the
  first two unit pages as cached PNG images. Clicking a preview opens the
  chapter-scoped PDF subset in an overlay/fullscreen reader that still uses
  the original PDF content rather than OCR or Markdown reflow.
- `app/static/app.js` now contains one active implementation for import polling,
  task timer behavior, and PDF preview.
- Study-task pages still use an adjustable local timer instead of exposing the
  scheduled minutes as a fixed user-facing duration.

Current animation direction:

- Keep the cursor energy field circular, not oval.
- Make linked particles feel like a diagonal flow from top-left toward
  bottom-right.
- Let particles respawn and continue flowing instead of looking static.
- Add a mouse gravity / attraction feel.
- Avoid dirty persistent traces.
- Avoid too many cursor-linked lines.
- Avoid concentric-disc or overly segmented cursor glow.

Current product-tone constraints:

- Keep all user-facing copy in Chinese unless a human explicitly changes that
  goal.
- Prefer a private tool feeling over a dashboard that explains itself like a
  product homepage.
- Do not reintroduce marketing language, team features, auth assumptions, or
  cloud-first framing unless explicitly requested.

Current handoff note:

- For practical handoff, trust `README.md`, `AGENTS.md`, `MEMORY.md`,
  `docs/agent/current-state.md`, the current code, and the documented
  validation commands.
- Treat runtime-sensitive directories such as `data/state/` as application
  state, not as general cleanup targets.
- For current PDF/import work, inspect these files first:
  `app/services/import_jobs.py`, `app/services/import_job_worker.py`,
  `app/services/pdf_page_viewer.py`, `app/templates/resource_form.html`,
  `app/templates/task_detail.html`, `app/templates/review_detail.html`,
  `app/templates/partials/task_pdf_stack.html`,
  `app/templates/partials/review_pdf_stack.html`, and the tail end of
  `app/static/app.js`.
- For browser verification on this Windows machine, prefer a clean
  non-`--reload` `uvicorn` process. Repeated `--reload` verification has been
  prone to stale worker/reloader states during long Docling imports and can
  look like random disconnects or `failed to fetch`.

Recommended validation after UI or motion changes:

```powershell
node --check app/static/app.js
.venv\Scripts\python.exe -m compileall app tests
.venv\Scripts\python.exe -m unittest
```

## What "Correct Work" Means Here

Human collaborators and AI agents should treat this repo as a study-control
system, not as a generic note app.

Correct ways to work on this project:

- Keep the project single-user and local-first by default.
- Treat local PDF inputs as the current source material to ingest and
  normalize.
- Keep the ingest pipeline local-first by default, and only switch to remote
  `docling-serve` when a human explicitly asks for that backend.
- Break each source into manageable learning units with deadlines.
- Track both first-pass study and later review.
- Require some proof of completion, not just a checkbox.
- Keep task history, deadlines, and review state in structured local storage.
- Prefer a dependable study loop before adding AI-heavy extras.

Avoid:

- Building multi-user, auth, or cloud sync first.
- Treating "opened a file" as equal to "learned it."
- Mixing raw sources with generated normalized content.
- Designing flashy gamification before daily accountability works.
- Coupling core study logic to a single external provider.

## Core User Story

One user should be able to:

1. Add a local PDF.
2. Set a target deadline and optional daily study capacity.
3. Let the system split the material into learning units.
4. Receive a day-by-day task plan.
5. Check in daily and record evidence of progress.
6. Get scheduled review tasks after first completion.
7. See what is due today, overdue, and at risk.

## Proposed MVP

The first useful version should include:

- Local web app, no login.
- Importer for local PDF, with URL import left for later work.
- Content normalization into Markdown or plain text.
- Resource metadata: title, source, deadline, priority, estimated effort.
- Auto-generated daily task queue.
- Manual progress tracking at chapter or section level.
- Review scheduling after completion.
- Daily dashboard: due today, overdue, completed, next review.
- Basic local reminders or missed-today flags.
- Optional AI assistance for section splitting and check-in questions, but the
  app must still function without it.

## Explicit Non-Goals

Do not build these first:

- multi-user features
- team dashboards
- social or ranking features
- remote sync as a hard requirement
- a full flashcard platform
- perfect automatic comprehension detection

## Product Flow

1. Ingest
   - PDF goes through local Docling and produces Markdown plus an outline with
     page-range hints.
   - The normalized Markdown is stored locally for study and review pages.
   - URL content remains a future ingest path.
2. Normalize
   - Assign a stable resource ID.
   - Store raw source metadata.
   - Split the content into chapters, sections, or chunk-sized learning units.
   - Estimate study effort per unit.
3. Plan
   - Ask for deadline, priority, and daily capacity.
   - Generate a schedule from today to the deadline.
   - Reserve review slots after initial completion.
4. Check in
   - Show today's due units.
   - Require progress notes, summary text, completion percentage, or question
     answers.
   - Mark missed work and reschedule when needed.
5. Review
   - Re-surface completed units on a review cadence.
   - Track whether the user retained the idea or needs re-study.

## Proposed Architecture

Recommended first implementation stack:

- Backend: FastAPI
- UI: server-rendered Jinja2 templates with room for later HTMX enhancement
- Database: SQLite
- Task scheduling: APScheduler or a small local scheduler layer
- Content parsing: Python adapters per source type
- Optional AI layer: OpenAI-compatible summarization and question generation
  behind a clean service interface

Why this stack fits:

- it stays simple for a single-user local product
- it matches the Python-based PDF pipeline already in the workspace
- it keeps deployment friction low
- it can later be wrapped as a desktop app if needed

## Environment

Current expected environment:

- Python 3.11 or newer
- Local virtual environment: `.venv/`
- Runtime dependencies tracked in `requirements.txt`

Create the local environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the app for normal browser verification on this Windows machine:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use `--reload` only when you are iterating quickly on code and are not trying
to prove long PDF import stability:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Recommended for normal use: keep the PDF backend local and prefetch the needed
artifacts once:

```powershell
.venv\Scripts\python.exe scripts\bootstrap_docling_easyocr.py --allow-insecure-fallback
```

The default runtime path is already local:

```powershell
$env:DOCLING_PDF_BACKEND = "local"
```

If your English PDFs are mostly born-digital and you want lower local CPU/RAM
usage, you can disable OCR:

```powershell
$env:DOCLING_PDF_OCR_ENABLED = "0"
```

The local backend now leaves formula enrichment off by default. If you later
need heavier formula reconstruction, opt in explicitly:

```powershell
$env:DOCLING_PDF_FORMULA_ENRICHMENT = "1"
```

Smoke-test the local English PDF path:

```powershell
.venv\Scripts\python.exe scripts\verify_docling_easyocr.py .\output\smoke_english.pdf --disable-ocr
```

Remove `--disable-ocr` when you are testing a scanned PDF or a PDF made mostly
from images.

Auto-generate a resource plus study tasks from a PDF:

```powershell
.venv\Scripts\python.exe scripts\import_pdf_tasks.py "C:\path\to\notes.pdf" --title "My Notes"
```

If you already have a cached Docling structure and want to skip re-parsing the
PDF, pass the existing `source.md` and `outline.json` instead:

```powershell
.venv\Scripts\python.exe scripts\import_pdf_tasks.py "C:\path\to\notes.pdf" `
  --docling-markdown ".\output\some_run\docling\source.md" `
  --docling-outline ".\output\some_run\docling\outline.json"
```

PowerShell note: pass a real file path directly. Do not include angle brackets
such as `<your-english-pdf>`, because PowerShell treats `<` as shell syntax.

About the local model sources:

- EasyOCR weights in `scripts/bootstrap_docling_easyocr.py` are downloaded
  directly from EasyOCR's official GitHub releases.
- Docling core artifacts in that same script still come from the official
  Hugging Face model repos. The current project does not have an official
  GitHub release mirror for those Docling model artifacts.

## Optional Remote Backend

If you later want to offload parsing again, the app can still target official
`docling-serve`, but only when you opt in explicitly:

```powershell
$env:DOCLING_PDF_BACKEND = "remote"
$env:DOCLING_SERVE_URL = "http://<server>:5001"
$env:DOCLING_SERVE_API_KEY = "<your-api-key>"  # only if your deployment requires it
```

The app will then call the official `POST /v1/convert/source` API under that
base URL and request both `md` and `json` output formats.

Useful checks:

```powershell
curl http://<server>:5001/health
```

Open:

```text
http://127.0.0.1:8000
```

## First Useful Commands

Run the pure-Python tests:

```powershell
python -m unittest
```

Run a syntax-only compile pass:

```powershell
python -m compileall app tests
```

Check the health endpoint after starting the server:

```powershell
curl http://127.0.0.1:8000/health
```

## Reusing Existing Workspace Projects

This project should reuse:

- `../../Project-source/`
  - Hold shared raw study material outside this repo.

Expected relationship:

- raw PDFs stay in `Project-source/`
- local Docling handles PDF parsing by default
- this repo stores the learning-management logic, normalized Markdown output,
  metadata, and local app state

## Proposed Data Model

Core entities:

- `Resource`
  - one imported source item
- `LearningUnit`
  - a chapter, section, or chunk to study
- `StudyPlan`
  - deadline and scheduling configuration
- `DailyTask`
  - a concrete unit due on a date
- `CheckIn`
  - evidence that work was attempted or completed
- `ReviewTask`
  - a scheduled revisit after first completion

Minimum fields worth planning for:

- `Resource`: id, title, source_type, source_path_or_url, imported_at
- `LearningUnit`: id, resource_id, title, order_index, estimated_minutes,
  status
- `StudyPlan`: id, resource_id, deadline, daily_capacity_minutes, priority
- `DailyTask`: id, unit_id, due_date, status, scheduled_minutes
- `CheckIn`: id, task_id, completed_at, note, confidence_score
- `ReviewTask`: id, unit_id, due_date, interval_days, result

## Verification of Real Progress

A useful completion signal should combine at least one of:

- a short written summary
- a self-rated confidence score
- a few generated or manual recall questions
- completion percentage on the unit
- time spent

That is the key difference between this project and a plain reading list.

## Repository Layout

Current structure:

```text
Learning-Supervisor/
  README.md
  AGENTS.md
  MEMORY.md
  Changing Description.txt
  requirements.txt
  docs/
    agent/
      current-state.md
  app/
    main.py
    config.py
    db.py
    models.py
    services/
    templates/
    static/
  data/
    resources/
    state/
  tests/
  output/
```

Use:

- `data/resources/` for normalized Markdown and PDF-derived artifacts stored in
  the app's local workspace
- `data/resources/<resource-id>/pdf_pages/` for cached rendered PNG page
  previews
- `data/resources/<resource-id>/pdf_subsets/` for cached unit/chapter PDF
  subsets and other viewer artifacts
- `data/state/` for the SQLite database plus import-job state
- `data/state/import_jobs/` for background import JSON state and worker logs
- `output/` for generated exports, reports, or debug artifacts

## First Build Order

Build in this order:

1. Resource import for local PDF
2. Deadline-based scheduling
3. Daily dashboard and check-in flow
4. Review scheduling
5. URL import
6. Optional AI-assisted chunking and questioning

This order keeps the main product loop testable early.

## Working Rules for AI Agents

If you are an AI agent working in this repo:

1. Read this README first.
2. Treat this README as the single source of truth for project rules.
3. Keep the project single-user unless a human explicitly changes the goal.
4. Prefer the local Docling path for PDF ingest unless a human explicitly asks
   to switch back to a remote backend.
5. Do not replace Docling as the parser core unless a human explicitly asks
   for that architecture change.
6. Keep raw study source material in `../../Project-source/` when possible.
7. Put generated artifacts in `output/`.
8. Keep structured local app state under `data/`, not in the repo root.
9. Prefer dependable local workflows over provider-specific shortcuts.
10. If you touch import polling, task timers, or PDF preview, inspect the
    active definitions in `app/static/app.js` before editing.
11. Do not add auth, cloud sync, or multi-user assumptions unless asked.
12. Update `Changing Description.txt` after meaningful completed work.
13. If the architecture changes, update this README in the same task.
14. Before continuing abandoned UI work, check `Current Agent Handoff` above
    for the latest user-approved direction and current visual constraints.

## Current MVP Boundary

The current first implementation intentionally supports:

- local PDF import through Docling
- background import-job execution for long PDF parsing
- automatic section splitting from headings
- fixed deadline scheduling
- written completion evidence
- per-study-task adjustable local timer
- chapter-scoped PDF reading that preserves original PDF bytes in the overlay
  viewer and uses only two clean inline preview pages on the left
- fixed-interval reviews at `1, 3, 7, 14` days

The current implementation intentionally does not yet support:

- URL import
- notifications
- spaced-repetition optimization such as FSRS
- authentication or cloud sync

## Before Push Checklist

Before pushing to GitHub, check:

- no raw large study files were copied into this repo by accident
- generated artifacts are inside `output/`
- local state stays under `data/`
- README updates were included if the scope or architecture changed
- `Changing Description.txt` reflects the completed work

## Current Gaps

- Runtime dependencies are now installed in this machine's `.venv`, but a
  fresh setup still needs `pip install -r requirements.txt`.
- The current UI is already usable, but it is still version-one product UI
  rather than a fully refined visual system.
- URL ingestion still needs a concrete parsing strategy.
- `app/static/app.js` has been consolidated to one active implementation for
  import polling, task timers, and PDF preview.
- Local bootstrap still depends on Hugging Face for Docling core artifacts, so
  a first-time setup can still hit Hugging Face SSL verification problems on
  this Windows machine. `scripts/bootstrap_docling_easyocr.py` avoids
  RapidOCR / ModelScope and keeps EasyOCR on GitHub, but it does not remove
  Hugging Face from the Docling core model path.
- Import progress is now tied to real Docling page callbacks plus later
  task-generation phases, but the final post-parse portion is still coarser
  than true per-substep backend instrumentation.
- Review scheduling currently uses a fixed interval rule rather than an
  adaptive algorithm.
- Evidence quality needs tuning so the app encourages real study without
  becoming annoying.
