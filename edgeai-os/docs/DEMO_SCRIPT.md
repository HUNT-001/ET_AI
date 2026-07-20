# EdgeAI-OS — Demo Video Script (~3.5 min)

A scene-by-scene walkthrough: what to click, what to say, timing, and a
fallback for every step. Story arc: **fragmented docs → cited & verified answer
→ causal reasoning → prediction → human-approved action → all local.**

---

## Pre-flight checklist (before you hit record)

- [ ] Ollama running with models pulled: `ollama pull qwen2.5:7b` + `ollama pull nomic-embed-text`
- [ ] Backend up **with local mode**, in `D:\ET_AI\edgeai-os`:
  ```powershell
  $env:EDGEAI_LLM="ollama"; $env:EDGEAI_OLLAMA_MODEL="qwen2.5:7b"; $env:EDGEAI_EMBED="ollama"
  uvicorn backend.main:app --port 8000
  ```
  (drop `--reload` for recording so it can't restart mid-take)
- [ ] Dashboard open (`frontend/index.html`), hard-refreshed (Ctrl+F5) → header shows **🔒 Fully local** + **Backend online**
- [ ] Click **Ingest sample** once so data is loaded (or ingest your real doc)
- [ ] A terminal visible for the "proof it's local" beat (`ollama ps`, `nvidia-smi`)
- [ ] Screen at 1080p, browser zoom ~100–110%, notifications off
- [ ] Do one silent dry-run — the **first** LLM answer is slow (model load); warm it up before recording

**Global fallback:** every panel renders on bundled sample data if the backend is down — if something hangs, keep narrating; the UI won't go blank.

---

## Scene 1 — Hook (0:00–0:20)

**On screen:** Dashboard top (logo, agent strip, the 🔒 Fully local badge).

**Say:**
> "Industrial plants lose up to a third of engineering hours just *searching* for information that already exists — scattered across a dozen disconnected systems. And when senior engineers retire, that knowledge walks out the door. EdgeAI-OS is a privacy-first industrial brain that fixes both — and it runs entirely on this laptop. Nothing leaves the machine."

**Point at:** the **🔒 Fully local** chip.

---

## Scene 2 — Cited & verified answer (0:20–1:00)

**Do:**
1. In the **Copilot**, type: *"What did the inspection find about the P-101A bearing?"* → **Ask**.
2. When the answer appears, point to the chips: `llm synthesis`, `confidence`, and **✓ all claims verified**.
3. Click a **source citation chip** → the source drawer slides in with the highlighted excerpt.

**Say:**
> "Ask a plain question, get a synthesized answer — with the exact source cited. Every claim is checked against that source by a verifier agent before you ever see it, so there are no confident hallucinations. Click the citation and you see the original passage it came from. This is running on a local Qwen model — no cloud, no API key."

**Fallback:** offline mode returns the same sample answer + working citation drawer.

---

## Scene 3 — The Reasoning Engine (1:00–1:45) ★ the wow

**Do:**
1. Scroll to the **Work Orders** panel, tag `P-101A`, click **Draft from reasoning**.
2. Let the card appear; read the **reason narrative** on it out loud.

**Say:**
> "Now the part that isn't just retrieval. Watch — I ask it to reason about this pump. It doesn't just say 'vibration is high.' It says: elevated vibration leads — through bearing wear, temperature rise, lubrication breakdown — to seal failure and an unplanned shutdown; here's roughly how long we have; and critically, *we've seen this exact pattern before, last time it was only re-torqued* — so the root cause was never fixed. That's causal, temporal, and historical reasoning combined — operational intelligence, not a search result."

**Alt (more technical, optional):** open `http://localhost:8000/docs` → `POST /reason` → run with `{"equipment_tag":"P-101A"}` to show the full structured output.

---

## Scene 4 — Predict & act, with a human in the loop (1:45–2:35)

**Do:**
1. Same work-order card — point to status **pending approval** and the audit chips.
2. Click **Approve**.
3. Point to the audit trail filling in: `notified → parts_reserved → cmms_handoff → executed`, and the `CMMS-WO-0001` reference.

**Say:**
> "From that reasoning, it auto-drafts the corrective work order — the right action, the right part, scheduled before the risk window. But industrial AI must not act on its own, so it stops here, at a human approval gate. I approve it — and now it executes every step with a full audit trail: notifies the lead, reserves the part, hands off to the maintenance system, and updates its own memory. That external handoff is a clean adapter — swap in real SAP or Maximo and it's live."

**Fallback:** works fully offline against the in-memory workflow engine.

---

## Scene 5 — Live condition monitoring (2:35–3:00)

**Do:**
1. **Live Sensors** panel → **Start feed**.
2. Let it tick; around tick ~30 the readings jump and the badge flips to **⚠ anomaly**.

**Say:**
> "And it's not only reactive. Here's a live condition feed — vibration and bearing temperature streaming through the real anomaly detector. Watch it hold steady… then a bearing fault develops, and it trips immediately. That same signal feeds the reasoning engine we just saw. In production a plant historian plugs in right here."

**Note:** this is a *simulated* feed (labeled as such) — say "simulated feed" once so it's honest.

---

## Scene 6 — Proof it's local + trustworthy (3:00–3:20)

**Do:**
1. Cut to the terminal: run `ollama ps` (shows qwen2.5:7b, 100% GPU) and/or `nvidia-smi`.

**Say:**
> "Everything you just saw ran on this machine — the model's on the GPU, the dashboard makes zero outbound calls. For a plant that won't put its P&IDs and safety data on someone else's cloud, that's the whole game. Verified answers, causal reasoning, audited actions — fully on-prem."

---

## Scene 7 — Close (3:20–3:40)

**On screen:** the architecture diagram (`docs/architecture_diagram.svg`) or the deck's architecture slide.

**Say:**
> "EdgeAI-OS: five specialized agents and a reasoning engine over one knowledge graph, self-verifying, human-governed, and fully local — backed by 60-plus automated tests. Not a RAG wrapper. An industrial operating brain."

**End card:** logo + "ET AI Hackathon 2026 · PS8".

---

## 90-second cut (if you need it short)

Scenes **1 → 2 → 3 → 4 → 7**. Drop live sensors and the terminal proof; work
"fully local" into the Scene-2 narration instead.

## Recording tips

- Narrate slightly slower than feels natural; you can speed the video 1.05× in edit.
- Pre-type the Copilot question in a notes app and paste it, so there's no typing lag on camera.
- If the first `/ask` is slow live, cut to it already answered — don't film the model warming up.
- Keep each scene as one continuous take; stitch in edit. Total target: **3:30–4:00**.
- Zoom the browser to make text legible on compressed video (110–125%).
