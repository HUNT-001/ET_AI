# Frontend — EdgeAI-OS Operations Console

A single self-contained `index.html` dashboard (React + Tailwind via CDN, no
build step) that talks to the FastAPI backend. It covers all four demo panels:

- **Expert Knowledge Copilot** — ask a question, get a synthesized, source-cited
  answer with a confidence score and time-to-answer.
- **Knowledge Pipeline** — graph/vector stats, documents ingested, primary-agent
  status, and one-click sample ingestion.
- **Maintenance & RCA** — per-equipment degradation risk, contributing factors,
  and a cited root-cause narrative.
- **Compliance Intelligence** — referenced frameworks, coverage gaps, and
  recorded deviations.
- **Time to Answer** — the before/after (manual search vs. EdgeAI-OS) headline
  metric.

## Run

1. Start the backend (CORS is enabled for the browser):
   ```
   uvicorn backend.main:app --reload --port 8000
   ```
2. Open `frontend/index.html` in a browser (double-click, or serve it with
   `python -m http.server` from this folder).
3. Click **Ingest sample** in the Knowledge Pipeline panel to load the bundled
   report, then use the Copilot / Maintenance / Compliance panels.

If the backend isn't running, the dashboard renders with bundled **sample data**
and shows an "offline" banner, so it always demos cleanly. Click the address in
the header to point it at a different backend URL and reconnect.

## Fully offline / air-gapped

All UI assets are vendored locally under `frontend/vendor/` (React, ReactDOM,
Babel, and a tree-shaken `tailwind.css`) — the page makes **zero outbound
requests**. The only network call is to your local backend (`localhost:8000`).
Combined with local Ollama inference, the entire stack runs with no internet:
a real "zero-trust edge" demo. The header shows a **🔒 Fully local** indicator.

To re-generate `vendor/tailwind.css` after changing classes, run Tailwind CLI
against `index.html`; the three JS libs are copies of the standard React/Babel
UMD builds.

> Production note: this is a zero-build demo UI. The originally-planned
> Next.js/TypeScript/shadcn scaffold remains a valid later upgrade — the API
> contract it consumes (`/ask`, `/agents/dispatch`, `/knowledge/stats`,
> `/plan`) stays the same.
