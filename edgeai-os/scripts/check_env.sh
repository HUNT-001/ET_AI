#!/usr/bin/env bash
# EdgeAI-OS Environment Audit Script
# Checks Phases 1-8 of the setup doc. Safe to run repeatedly (read-only checks).

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { printf "  ${GREEN}✅ %-25s${NC} %s\n" "$1" "$2"; }
miss() { printf "  ${RED}❌ %-25s${NC} not found\n" "$1"; }

check_cmd() {
  local name="$1" cmd="$2" versionflag="${3:---version}"
  if command -v "$cmd" >/dev/null 2>&1; then
    ver=$("$cmd" $versionflag 2>&1 | head -n1)
    ok "$name" "$ver"
  else
    miss "$name"
  fi
}

check_py_pkg() {
  if python3 -c "import $1" >/dev/null 2>&1; then
    ver=$(python3 -c "import $1; print(getattr($1,'__version__','installed'))" 2>/dev/null)
    ok "$1" "$ver"
  else
    miss "$1"
  fi
}

echo "############################################"
echo "PHASE 1 — Development Machine"
echo "############################################"
check_cmd "Python" python3 "--version"
check_cmd "Node.js" node "--version"
check_cmd "Java" java "-version"
check_cmd "Rust" rustc "--version"
check_cmd "Go" go "version"
check_cmd "C++ (g++)" g++ "--version"
check_cmd "CMake" cmake "--version"
check_cmd "Docker" docker "--version"
check_cmd "VS Code" code "--version"

echo ""
echo "############################################"
echo "PHASE 2 — Version Control"
echo "############################################"
check_cmd "Git" git "--version"
check_cmd "GitHub CLI" gh "--version"

echo ""
echo "############################################"
echo "PHASE 3 — Python Environment"
echo "############################################"
check_cmd "uv" uv "--version"
check_cmd "conda" conda "--version"
for pkg in numpy pandas scipy sklearn matplotlib plotly cv2 PIL torch torchvision transformers sentence_transformers accelerate onnx onnxruntime faiss chromadb langchain llama_index fastapi uvicorn pydantic sqlalchemy networkx; do
  check_py_pkg "$pkg"
done

echo ""
echo "############################################"
echo "PHASE 4 — Local AI Runtime"
echo "############################################"
check_cmd "Ollama" ollama "--version"
check_cmd "llama.cpp (llama-cli)" llama-cli "--version"
check_py_pkg onnxruntime
check_cmd "OpenVINO (mo)" mo "--version"

echo ""
echo "############################################"
echo "PHASE 5 — Databases"
echo "############################################"
check_cmd "PostgreSQL" psql "--version"
check_cmd "MongoDB" mongod "--version"
check_cmd "Redis" redis-server "--version"
check_cmd "Neo4j" neo4j "--version"
check_py_pkg chromadb
python3 -c "import qdrant_client" >/dev/null 2>&1 && ok "qdrant-client" "installed" || miss "qdrant-client"

echo ""
echo "############################################"
echo "PHASE 6 — Backend"
echo "############################################"
check_py_pkg fastapi
check_py_pkg uvicorn

echo ""
echo "############################################"
echo "PHASE 7 — Frontend"
echo "############################################"
check_cmd "npm" npm "--version"
check_cmd "npx" npx "--version"
if [ -d node_modules/react ] || npm ls -g react >/dev/null 2>&1; then ok "React" "check per-project"; else miss "React (per-project, expected)"; fi

echo ""
echo "############################################"
echo "PHASE 8 — AI Infra (model files, not code)"
echo "############################################"
echo "  (Models are downloaded, not pip-installed — see recommendation below)"

echo ""
echo "############################################"
echo "SUMMARY"
echo "############################################"
echo "Run this on YOUR machine (not the assistant's sandbox) for a real picture."
echo "Save as check_env.sh, then: chmod +x check_env.sh && ./check_env.sh"
