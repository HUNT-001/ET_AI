# Tech Stack

| Layer | Choice | Status |
|---|---|---|
| Backend | FastAPI + Uvicorn | ✅ scaffolded, tested |
| Orchestration | Custom (`backend/core/orchestrator.py`) | ✅ scaffolded, tested |
| Agent framework | Custom (`agents/base.py` + registry) | ✅ scaffolded, tested |
| Memory | In-memory stub → Redis (working/short-term) + Postgres (long-term/incident) | ⏳ stub only |
| Vector DB | ChromaDB (or Qdrant) | ⏳ not wired in |
| Knowledge graph | Neo4j | ⏳ not wired in |
| Relational DB | PostgreSQL | ⏳ docker-compose ready, not wired in |
| Frontend | Next.js + React + TypeScript + Tailwind + shadcn/ui | ⏳ not started |
| Visualization | ECharts / Plotly / Leaflet / MapLibre | ⏳ not started |
| Local LLM/SLM | Ollama, llama.cpp/GGUF, Qwen 2.5 3B / Phi-4 Mini / Gemma 3 4B | ⏳ not installed |
| Vision | YOLOv11, RT-DETR, MobileSAM | ⏳ not installed |
| OCR | PaddleOCR / EasyOCR | ⏳ not installed |
| Speech | Whisper Tiny/Small | ⏳ not installed |
| Embeddings | bge-small / nomic-embed / e5-small | ⏳ not installed |
| Forecasting | LightGBM / XGBoost / LSTM / TFT | ⏳ not installed |
| Anomaly detection | Isolation Forest / Autoencoder / One-Class SVM | ⏳ not installed |
| Edge runtimes | ONNX Runtime ✅ (installed), llama.cpp, TensorRT, OpenVINO, WebGPU, Transformers.js, LiteRT | ⏳ partial |
| Deployment targets | Desktop (Electron/Tauri), Browser (WebGPU/WebLLM), Edge (Jetson/Pi/NUC), Embedded (ESP32/STM32/FPGA) | ⏳ not started |

Legend: ✅ done · ⏳ planned. Update this table as each piece lands —
it doubles as your build progress tracker.
