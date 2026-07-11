# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Initial repo structure (Phases 1-10 scaffold)
- `Orchestrator` + `MemoryLayer` (in-memory stub)
- 11 agent stubs implementing `BaseAgent`: Planner, Knowledge, Vision,
  Reasoning, Compliance, Forecasting, Simulation, Optimization, Reporting,
  Monitoring, Notification
- FastAPI backend with `/health`, `/agents`, `/orchestrate`,
  `/agents/dispatch`, `/memory`
- docker-compose for Postgres, Redis, ChromaDB
- Base documentation set (Architecture, TechStack, API, Deployment, Roadmap)
- MIT License
- `scripts/check_env.sh` environment audit script
