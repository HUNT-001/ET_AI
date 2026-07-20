"""
Optional LangGraph execution runtime.

This wraps the *existing* agents in a LangGraph StateGraph — Planner → Executor
→ Verify — so the platform can run on a standard graph runtime when that's
desired (visual graphs, durable/interruptible execution). It reuses every
agent through the Orchestrator; it is NOT a rewrite of the agents.

It is strictly opt-in (`EDGEAI_RUNTIME=langgraph`), and the hand-written
Orchestrator remains the default and the fallback: if `langgraph` isn't
installed, `run_graph` raises a clear error and callers fall back to
`Orchestrator.plan_and_execute`. This keeps the working, tested runtime intact
while making the graph-based runtime available.

Enable:  pip install langgraph  +  EDGEAI_RUNTIME=langgraph
"""

from __future__ import annotations

from typing import Any


def langgraph_available() -> bool:
    try:
        import langgraph  # noqa: F401
        return True
    except Exception:
        return False


def build_graph(orchestrator):
    """Compile a StateGraph: planner node -> executor node -> verify node."""
    from typing import TypedDict

    from langgraph.graph import StateGraph, END

    class State(TypedDict):
        goal: str
        plan: list
        results: list

    def planner_node(state: State) -> dict:
        resp = orchestrator.dispatch("planner", state["goal"])
        plan = resp.result.get("plan", []) if isinstance(resp.result, dict) else []
        return {"plan": plan, "results": []}

    def executor_node(state: State) -> dict:
        results = []
        for step in state["plan"]:
            r = orchestrator.dispatch(step["agent"], step.get("task", state["goal"]),
                                      step.get("payload", {}))
            results.append({"agent": r.agent_name, "confidence": r.confidence,
                            "result": r.result, "notes": r.notes})
        return {"results": results}

    def verify_node(state: State) -> dict:
        # Persist the completed plan to shared memory (parity with the native runtime).
        orchestrator.memory.commit_long_term({"goal": state["goal"], "plan": state["plan"],
                                              "runtime": "langgraph"})
        return {}

    g = StateGraph(State)
    g.add_node("planner", planner_node)
    g.add_node("executor", executor_node)
    g.add_node("verify", verify_node)
    g.set_entry_point("planner")
    g.add_edge("planner", "executor")
    g.add_edge("executor", "verify")
    g.add_edge("verify", END)
    return g.compile()


def run_graph(goal: str, orchestrator, payload: dict | None = None) -> dict[str, Any]:
    if not langgraph_available():
        raise RuntimeError("langgraph is not installed. `pip install langgraph` or unset EDGEAI_RUNTIME.")
    app = build_graph(orchestrator)
    out = app.invoke({"goal": goal, "plan": [], "results": []})
    return {"goal": goal, "plan": out.get("plan", []), "results": out.get("results", []),
            "runtime": "langgraph"}
