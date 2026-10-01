# Learning-Supervisor Memory

## Purpose Snapshot

- `Learning-Supervisor` is a local-first, single-user study supervision app.
- The current product is already a runnable web app, not just an MVP plan.
- The repo is runtime-sensitive because local application state lives under
  `data/state/`.

## Stable Decisions

- Keep the product single-user and localhost-first unless a task explicitly
  changes the boundary.
- Treat local PDF import as the current ingest path; URL ingestion is still a
  future capability.
- Keep the default PDF path local-first, with remote `docling-serve` only as
  an explicit opt-in backend.
- Keep Docling as the PDF parsing core unless a human explicitly requests a
  replacement architecture.
- Long PDF imports now run through persisted background jobs under
  `data/state/import_jobs/` instead of relying on one long blocking web
  request.
- Study and review pages now show only the first two inline preview pages on
  the left, rendered as PNGs from the original PDF, while the click-to-open
  overlay uses a chapter-scoped PDF subset that preserves the original PDF
  bytes.
- Keep user-facing copy in Chinese unless a human explicitly changes that goal.
- Use project docs in this order for cold-start takeover:
  `README.md` -> `AGENTS.md` -> `MEMORY.md` -> `docs/agent/current-state.md`.

## Canonical Commands

Environment setup:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the app:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Hot-reload development only:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Validation:

```powershell
node --check app/static/app.js
.venv\Scripts\python.exe -m compileall app tests
.venv\Scripts\python.exe -m unittest
```

## Known Risks And Gotchas

- `data/state/` is live runtime state, not a safe cleanup zone.
- `data/state/import_jobs/` is also live runtime state; it stores import-job
  JSON snapshots plus worker stdout/stderr logs.
- The project is protected-project mode: observe and verify before restructuring
  or changing model-adjacent behavior.
- `Project-source/` is still the correct home for shared raw PDFs; derived app
  state and normalized content belong in this repo instead.
- Legacy duplicate timer, import-polling, and PDF-preview helper blocks were
  removed from `app/static/app.js`; the remaining active definitions are the
  final import handler, `initTaskTimerV3`, and the document-frame PDF preview.
- `.task-timer-alert` must keep `[hidden] { display: none; }`; its base grid
  display otherwise overrides the native hidden attribute on a fresh timer.
- PowerShell output on this machine can still show mojibake for some Chinese
  strings. Verify in the browser before assuming the UI text itself is broken.
- For Windows runtime verification of long imports, a clean non-`--reload`
  `uvicorn` process has been more reliable than repeated `--reload` sessions.
