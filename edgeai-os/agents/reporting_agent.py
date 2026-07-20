"""
ReportingAgent — turns another agent's structured output into a
human-readable report / audit-ready evidence package.

Called by ComplianceAgent (evidence packages) and available for general
cross-agent summaries. Status: real (not a stub). Deterministic Markdown
rendering — no model needed, so evidence packages are reproducible and
auditable, which matters for the compliance/audit framing in PS8.
"""

from __future__ import annotations

from datetime import datetime, timezone

from agents.base import AgentRequest, AgentResponse, BaseAgent


def render_evidence_package(title: str, sections: list[dict]) -> str:
    """sections: [{"heading": str, "body": str or list[str]}]. Returns Markdown."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# {title}", "", f"_Generated: {stamp}_", ""]
    for sec in sections:
        lines.append(f"## {sec.get('heading', '')}")
        body = sec.get("body", "")
        if isinstance(body, list):
            if body:
                lines.extend(f"- {item}" for item in body)
            else:
                lines.append("_(none)_")
        else:
            lines.append(str(body))
        lines.append("")
    return "\n".join(lines).strip()


class ReportingAgent(BaseAgent):
    name = "reporting"
    description = (
        "Generates human-readable reports and ComplianceAgent's audit-ready "
        "evidence packages from other agents' structured output. "
        "Deterministic, reproducible Markdown rendering."
    )
    tools: list[str] = ["markdown_renderer"]

    def run(self, request: AgentRequest) -> AgentResponse:
        title = request.payload.get("title", "Report")
        sections = request.payload.get("sections", [])
        report = render_evidence_package(title, sections)
        return AgentResponse(
            agent_name=self.name,
            result=report,
            confidence=1.0,
            tool_calls=["markdown_renderer"],
            notes=f"Rendered {len(sections)} section(s).",
        )
