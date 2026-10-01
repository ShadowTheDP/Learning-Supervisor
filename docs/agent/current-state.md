# Current State

## Current Objective

Keep a stable local-first Docling-based study supervision app while making
long PDF imports recoverable and keeping chapter-scoped PDF reading usable
from docs-alone handoff.

## Current Decisions

- The product remains single-user and localhost-first.
- `README.md` is the durable project rules document.
- `AGENTS.md` handles routing and protected-project operating rules.
- `MEMORY.md` stores durable commands, risks, and stable decisions.
- The current default ingest path is local PDF import through the local-first
  Docling flow, and Docling remains the parser core.
- Long PDF imports now run as background jobs whose state is persisted under
  `data/state/import_jobs/`; the import page can recover progress after
  navigation or reload.
- Import progress is driven by real Docling page callbacks plus later
  task-generation phases, not by a fake frontend-only timer.
- Study/review left-column preview now shows only the first two unit pages as
  cached PNG images.
- Clicking those preview pages opens a chapter-scoped PDF subset in an overlay
  or fullscreen reader, and that reader still uses original PDF bytes rather
  than OCR/Markdown reflow.
- `data/state/` is runtime-sensitive application state and should not be edited
  casually.
- `data/state/import_jobs/` is also runtime-sensitive application state.
- `app/static/app.js` was slimmed by removing superseded helper copies; the
  remaining import polling, timer, and PDF preview logic is single-definition
  code at the end of the file.
- The backend still exposes `/units/{unit_id}/pdf-preview/{page_number}`, but
  the current templates no longer depend on that route for the left preview.
- User-facing copy should stay Chinese unless a human explicitly changes that
  goal.
- For browser verification on Windows, prefer a clean non-`--reload`
  `uvicorn` process when testing long imports.

## Structure Assumptions

- `app/` contains FastAPI, templates, static assets, and service logic.
- `data/resources/` stores normalized study artifacts.
- `data/resources/<resource-id>/pdf_pages/` stores rendered PNG page previews.
- `data/resources/<resource-id>/pdf_subsets/` stores cached chapter/unit PDF
  subsets and related viewer artifacts.
- `data/state/` stores local runtime state such as SQLite data.
- `data/state/import_jobs/` stores background import-job JSON state and worker
  logs.
- `output/` stores exports, smoke artifacts, and debug output.
- `tests/` covers parsing, scheduling, and template behavior.

## Next Likely Improvements

- Keep the consolidated `app/static/app.js` behavior stable while testing UI
  changes.
- A fresh timer now hides the expiry alert through `.task-timer-alert[hidden]`;
  the alert appears only after the timer reaches zero.
- Improve the final post-Docling import-progress granularity if finer backend
  instrumentation becomes necessary.
- Continue checking timer edge cases around stale localStorage, resumed pages,
  and first-use expiry behavior.
- Add URL ingestion.
- Add reminder notifications.
- Add AI-assisted question generation behind the existing local-first boundary.
- Improve adaptive review scheduling beyond fixed intervals.
