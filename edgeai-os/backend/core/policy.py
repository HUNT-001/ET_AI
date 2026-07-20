"""
Human-in-the-loop policy — decides when an automated answer/action must be
held for a human before it's acted on.

Safety-critical industrial workflows should not auto-execute on shaky evidence.
This gates on low retrieval/answer confidence and on the VerifierAgent's
grounding status, so an unverified or low-confidence answer is flagged
`requires_approval` (the dashboard shows an "Approve" state) instead of being
presented as settled fact.
"""

from __future__ import annotations

# Below this confidence, hold for a human even if grounded.
CONFIDENCE_THRESHOLD = 0.5


def approval_decision(confidence, verification: dict | None = None) -> dict:
    reasons: list[str] = []
    if confidence is not None and confidence < CONFIDENCE_THRESHOLD:
        reasons.append(f"confidence {round(float(confidence), 2)} below {CONFIDENCE_THRESHOLD}")
    if verification and verification.get("status") != "verified":
        flagged = len(verification.get("flagged", []))
        reasons.append(f"verification {verification.get('status')}"
                       + (f" ({flagged} unverified claim(s))" if flagged else ""))
    return {"requires_approval": bool(reasons), "reasons": reasons,
            "auto_approved": not reasons}
