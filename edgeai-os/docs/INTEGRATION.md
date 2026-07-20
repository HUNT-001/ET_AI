# EdgeAI-OS — Integration & Setup Guide

Everything runs **out of the box with zero external services** (offline
embeddings, in-memory graph, extractive synthesis). Each capability below is an
opt-in upgrade toggled by an environment variable — and if a configured service
is unreachable, the platform logs a warning and falls back instead of crashing.

This is the "what you provide from your side" checklist.

---

## 1. Local LLM copilot (privacy-first) — Ollama

The Expert Knowledge Copilot synthesizes answers locally, so no plant data
leaves the host. The code is already wired; you just run Ollama.

1. Install Ollama: https://ollama.com
2. Pull a model:
   ```
   ollama pull qwen2.5:3b        # small/fast; use llama3.1:8b if you have the RAM/VRAM
   ```
3. Set env vars before starting the backend:
   ```
   EDGEAI_LLM=ollama
   EDGEAI_OLLAMA_MODEL=qwen2.5:3b
   # optional: EDGEAI_OLLAMA_HOST=http://localhost:11434
   ```

No API key. To use a cloud model instead (NOT recommended for the privacy
pitch): `EDGEAI_LLM=openai` + `OPENAI_API_KEY=sk-...` (optional
`EDGEAI_OPENAI_MODEL`).

Without either, the copilot uses deterministic offline synthesis — still cited,
just less fluent.

## 2. Local embeddings (better semantic recall) — Ollama

Replaces the offline hashing embedder with real local embeddings.

```
ollama pull nomic-embed-text
```
```
EDGEAI_EMBED=ollama
# optional: EDGEAI_OLLAMA_EMBED_MODEL=nomic-embed-text
```
The vector collection is namespaced by embedding type, so switching modes won't
mix incompatible vectors. Re-ingest your documents after switching.

## 3. OCR for scanned PDFs — Tesseract

Lets scanned inspection reports / P&IDs ingest (otherwise they're rejected with
a clear message).

1. Install the Tesseract binary:
   - Windows: https://github.com/UB-Mannheim/tesseract/wiki (note the install path)
   - macOS: `brew install tesseract` · Linux: `apt install tesseract-ocr`
2. `pip install pytesseract Pillow` (already in requirements.txt)
3. If Tesseract isn't on PATH, set `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`

OCR auto-enables when `pytesseract` is importable. No keys.

## 4. Persistent knowledge graph — Neo4j

Swaps the in-memory networkx graph for real persistence (survives restarts,
Cypher queryable). Same interface — no agent code changes.

1. Run Neo4j — either:
   - **Neo4j Desktop** / Docker: `docker run -p 7687:7687 -p 7474:7474 -e NEO4J_AUTH=neo4j/password neo4j:5`
   - **AuraDB Free** (hosted): https://neo4j.com/cloud/aura-free/
2. Set env vars:
   ```
   EDGEAI_GRAPH=neo4j
   NEO4J_URI=bolt://localhost:7687        # or neo4j+s://<id>.databases.neo4j.io for Aura
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your-password
   # optional: NEO4J_DATABASE=neo4j
   ```
The `neo4j` Python driver is already in requirements.txt.

## 5. Real documents

The single biggest credibility boost for judging: replace the synthetic sample
with 2–3 real files (a real OISD standard, a maintenance log, and ideally a
P&ID that shares an equipment tag with another doc, so cross-document graph
linkage is demonstrable). Upload them via the dashboard's **Upload document**
button or `POST /ingest/upload`.

## 5b. Expose EdgeAI-OS to other tools — MCP server (optional)

The platform can run as an **MCP server**, so Claude Desktop / IDEs / other
agents can query the plant brain directly (still fully local).

```
pip install "mcp[cli]"
python integrations/mcp_server.py
```
Tools exposed: `ask_knowledge`, `equipment_risk`, `check_compliance`,
`failure_patterns`, `ingest_document`, `graph_stats`. Add to Claude Desktop's
`claude_desktop_config.json`:
```json
{ "mcpServers": { "edgeai-os": {
    "command": "python",
    "args": ["D:/ET_AI/edgeai-os/integrations/mcp_server.py"],
    "env": {"EDGEAI_LLM":"ollama","EDGEAI_OLLAMA_MODEL":"qwen2.5-rag","EDGEAI_EMBED":"ollama"}
} } }
```

## 5c. Evaluation numbers

Generate the metrics judges ask for (entity P/R, retrieval hit@k, time-to-answer,
compliance gap precision, graph linkage, grounding):
```
python scripts/evaluate.py       # prints a report + writes benchmarks/results.json
```

## 5d. Enterprise runtime features

Built in, always on (no setup):
- **Observability** — every agent dispatch is traced (timing, confidence, tools).
  `GET /trace` returns per-agent summaries + the recent span trail.
- **Human-in-the-loop** — `/ask` returns an `approval` block; low-confidence or
  unverified answers are flagged `requires_approval` instead of auto-presented.
- **Event-driven cascade** — ingesting a document publishes `document_ingested`,
  which auto-re-checks compliance and refreshes lessons (`reactions` in the
  ingest response).
- **Reflection** — if the VerifierAgent flags ungrounded claims, `/ask` retries
  once with expanded retrieval and keeps the better-grounded answer
  (`reflected: true`).

Opt-in graph runtime:
```
pip install langgraph
set EDGEAI_RUNTIME=langgraph      # plan_and_execute now runs on a LangGraph StateGraph
```
The hand-written orchestrator stays the default and the automatic fallback if
`langgraph` is absent — nothing breaks either way.

## 5e. Industrial Reasoning Engine

Beyond retrieval — causal + temporal + episodic + planning reasoning:
- `POST /reason {"equipment_tag":"P-101A"}` → operational assessment: symptom →
  causal failure chain → hours-to-elevated-risk → recurrence/precedent →
  scheduled recommendation, as a grounded narrative.
- `POST /simulate {"equipment_tag":"P-101A"}` → what-if failure projection:
  affected assets, downtime, cost band, spare parts, compliance exposure.

Backed by `knowledge/ontology.py` (causal failure model), `knowledge/temporal.py`
(time-aware history / "what changed"), and `backend/core/episodic.py`
(organizational memory — "seen twice before"). All local, all deterministic +
grounded.

## 5f. Operational capabilities

- **Autonomous workflow (human-gated):** `POST /workorders/draft {"equipment_tag":"P-101A"}`
  reasons about the asset and drafts a work order held at the approval gate;
  `POST /workorders/{id}/approve` executes every step with a full audit trail
  (notify → reserve parts → CMMS handoff → memory). The CMMS hop is a pluggable
  adapter (`MockCMMSAdapter`) — a real SAP/Maximo adapter implements the same
  two methods. `GET /workorders` lists.
- **P&ID vision (real):** VisionAgent runs OpenCV symbol/line detection + OCR
  tag extraction on drawing images; tags land in the shared graph
  (cross-modal linkage). Needs `opencv-python-headless` (+ Tesseract for tags).
  Test drawing: `python scripts/generate_sample_pid.py`.
- **Simulated sensor stream:** `POST /stream/tick {"equipment_tag":"P-101A"}`
  advances a synthetic historian feed (labeled `simulated:true`) through the
  real SPC/anomaly logic — live-risk demo without plant hardware; a real
  OPC-UA/PI feed plugs in at the same point.
- **Neo4j live test:** `pytest tests/test_neo4j_live.py` runs the full graph
  interface against a real Neo4j when `NEO4J_URI` is reachable, and skips
  cleanly otherwise.

## 6. What you do NOT need

- **No MCP servers.** MCP connects *Claude* to external tools; it is not part of
  EdgeAI-OS's runtime. (You'd only add a document connector later if you wanted
  auto-pull from SharePoint/Drive — out of scope for the hackathon.)
- **No cloud API keys** for the privacy-first configuration.
- **No paid services** — Ollama, Tesseract, and Neo4j Community/Aura-Free are all free.

---

## Quick start (full privacy-first mode)

```powershell
# one-time
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
pip install -r requirements.txt

# env (PowerShell example)
$env:EDGEAI_LLM="ollama"; $env:EDGEAI_OLLAMA_MODEL="qwen2.5:3b"
$env:EDGEAI_EMBED="ollama"

# run
uvicorn backend.main:app --reload --port 8000
# then open frontend/index.html
```

## Env var reference

| Variable | Default | Purpose |
|---|---|---|
| `EDGEAI_LLM` | *(offline)* | `ollama` or `openai` — copilot answer synthesis |
| `EDGEAI_OLLAMA_MODEL` | `qwen2.5:3b` | Ollama chat model |
| `EDGEAI_OPENAI_MODEL` | `gpt-4o-mini` | cloud model (if `EDGEAI_LLM=openai`) |
| `OPENAI_API_KEY` | — | required only for `EDGEAI_LLM=openai` |
| `EDGEAI_EMBED` | *(offline)* | `ollama` for local embeddings |
| `EDGEAI_OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `EDGEAI_OLLAMA_HOST` | `http://localhost:11434` | Ollama daemon URL |
| `TESSERACT_CMD` | *(PATH)* | Tesseract binary path if not on PATH |
| `EDGEAI_GRAPH` | *(networkx)* | `neo4j` for persistent graph |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | — | required for `EDGEAI_GRAPH=neo4j` |
