"""
Agent registry — the single place that lists every agent available to the
Orchestrator, aligned to ET AI Hackathon 2026 Problem Statement 8
("AI for Industrial Knowledge Intelligence: Unified Asset & Operations Brain").

PRIMARY_AGENTS are the 5 agents named explicitly in the PS8 brief's
"What You May Build" section -- these are what judges will look for by name.
SUPPORTING_AGENTS are internal building blocks the primary agents call.
"""

from agents.base import AgentRequest, AgentResponse, BaseAgent

from agents.ingestion_agent import IngestionAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.maintenance_agent import MaintenanceAgent
from agents.compliance_agent import ComplianceAgent
from agents.lessons_learned_agent import LessonsLearnedAgent

from agents.planner_agent import PlannerAgent
from agents.vision_agent import VisionAgent
from agents.reasoning_agent import ReasoningAgent
from agents.forecasting_agent import ForecastingAgent
from agents.monitoring_agent import MonitoringAgent
from agents.reporting_agent import ReportingAgent
from agents.notification_agent import NotificationAgent

# The 5 agents PS8 names explicitly -- lead with these in any pitch/demo.
PRIMARY_AGENTS: list[BaseAgent] = [
    IngestionAgent(),      # Universal Document Ingestion & Knowledge Graph Agent
    KnowledgeAgent(),      # Expert Knowledge Copilot
    MaintenanceAgent(),    # Maintenance Intelligence & RCA Agent
    ComplianceAgent(),     # Quality & Regulatory Compliance Intelligence
    LessonsLearnedAgent(), # Lessons Learned & Failure Intelligence Engine
]

# Internal agents the primary 5 call -- not part of PS8's named checklist,
# but what makes the primary agents actually work.
SUPPORTING_AGENTS: list[BaseAgent] = [
    PlannerAgent(),
    VisionAgent(),
    ReasoningAgent(),
    ForecastingAgent(),
    MonitoringAgent(),
    ReportingAgent(),
    NotificationAgent(),
]

REGISTRY: list[BaseAgent] = PRIMARY_AGENTS + SUPPORTING_AGENTS
AGENTS_BY_NAME: dict[str, BaseAgent] = {a.name: a for a in REGISTRY}

__all__ = [
    "AgentRequest", "AgentResponse", "BaseAgent",
    "PRIMARY_AGENTS", "SUPPORTING_AGENTS", "REGISTRY", "AGENTS_BY_NAME",
]
