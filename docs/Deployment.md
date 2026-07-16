# Deployment Guide

The same orchestrator + agents run across every target below. What changes
is only the inference backend each agent calls internally.

## Desktop
- Package with Electron or Tauri, bundle the FastAPI backend as a sidecar
  process, run inference via Ollama or ONNX Runtime locally.

## Browser
- Run inference via WebGPU / Transformers.js / WebLLM / ONNX Runtime Web.
  No Python backend required in this mode — agents' model-calling logic
  needs a JS/WASM equivalent path.

## Edge (Jetson / Raspberry Pi / Intel NUC)
- Same Python backend as desktop. Use TensorRT (Jetson, NVIDIA only) or
  OpenVINO (Intel) for accelerated inference; fall back to ONNX Runtime
  or llama.cpp/GGUF elsewhere.

## Embedded (ESP32 / STM32 / FPGA)
- Out of scope for the Python orchestrator — this tier runs a minimal
  firmware component (see `firmware/`) that talks to the rest of the
  platform over MQTT/CAN/Modbus, feeding the Sensor/Vision agents rather
  than running the orchestrator itself.

## Minimum Viable Local Stack
```bash
docker compose up -d          # Postgres, Redis, Chroma
uvicorn backend.main:app --reload --port 8000
```

## Proving "no cloud inference" (for OSDHack)
1. Disconnect network / block outbound API calls.
2. Confirm `/health` and `/orchestrate` still respond.
3. Confirm the model calls inside each agent route through a local runtime
   (Ollama, ONNX Runtime, llama.cpp) rather than a cloud API — this is the
   check to automate once real model calls replace the current stubs.
