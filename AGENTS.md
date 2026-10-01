# Learning-Supervisor AGENTS

## Read Order

1. `README.md`
2. `MEMORY.md`
3. `docs/agent/current-state.md`
4. `Changing Description.txt` only when historical detail or rollout history is
   needed
5. The relevant backend, template, or static file for the current task

If the task touches long PDF import, PDF preview, or the study-task timer,
inspect these files first:

- `app/services/import_jobs.py`
- `app/services/import_job_worker.py`
- `app/services/pdf_page_viewer.py`
- `app/templates/resource_form.html`
- `app/templates/task_detail.html`
- `app/templates/review_detail.html`
- `app/templates/partials/task_pdf_stack.html`
- `app/templates/partials/review_pdf_stack.html`
- the final active helper definitions near the end of `app/static/app.js`

## Scope

- Stay inside `Project/Learning-Supervisor/` unless the user explicitly asks
  for cross-project work.
- Treat the project as runtime-sensitive and local-first.
- Preserve the single-user, localhost-first product boundary unless a task
  explicitly changes it.

## Protected Areas

- `data/state/`
- `.venv/`
- `output/` unless the task is specifically about generated artifacts
- heavy local model or cache paths referenced by the PDF pipeline

## Preferred Plugins

- `Everything MCP` for path discovery
- `QMD` for local rules, handoff docs, and plans
- `Context7` for FastAPI, Jinja, or Python-library docs
- `GitHub MCP` only when the task is truly about repo or remote history

## Validation

Use the narrowest command that proves the change:

- `node --check app/static/app.js`
- `.venv\Scripts\python.exe -m compileall app tests`
- `.venv\Scripts\python.exe -m unittest`
- `curl http://127.0.0.1:8000/health` after starting the app, when runtime
  verification is required
- For browser smoke tests on Windows, prefer
  `.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
  over repeated `--reload` runs when long Docling imports are involved.
- If you edit `app/static/app.js`, search the whole file first. Older helper
  copies still exist earlier in the file, and the last definitions currently
  win.

## Structure Direction

- Keep `app/` as the application code root.
- Keep `data/resources/` for normalized study artifacts.
- Keep `data/resources/*/pdf_pages/` and `data/resources/*/pdf_subsets/` as
  cached PDF viewer artifacts.
- Keep `data/state/` as runtime state, not as a casual cleanup target.
- Keep `data/state/import_jobs/` as persisted import-job state plus worker
  logs.
- Keep `output/` for generated exports and debug artifacts.
- When workflow or handoff expectations change, update `README.md`,
  `AGENTS.md`, `MEMORY.md`, and `docs/agent/current-state.md` together.
