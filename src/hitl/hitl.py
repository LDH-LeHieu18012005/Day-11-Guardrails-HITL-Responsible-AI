"""
Lab 11 - Part 4: Human-in-the-Loop Design
  Task 12: Confidence Router
  Task 13: Design 3 HITL decision points
"""
from dataclasses import dataclass


HIGH_RISK_ACTIONS = [
    "transfer_money",
    "close_account",
    "change_password",
    "delete_data",
    "update_personal_info",
]


@dataclass
class RoutingDecision:
    """Decision returned by the HITL confidence router."""
    action: str
    confidence: float
    reason: str
    priority: str
    requires_human: bool


class ConfidenceRouter:
    """Route responses by confidence and banking action risk."""

    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def route(self, response: str, confidence: float,
              action_type: str = "general") -> RoutingDecision:
        """Return whether a response can be sent, reviewed, or escalated."""
        confidence = max(0.0, min(1.0, confidence))

        if action_type in HIGH_RISK_ACTIONS:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason=f"High-risk action: {action_type}",
                priority="high",
                requires_human=True,
            )

        if confidence >= self.HIGH_THRESHOLD:
            return RoutingDecision(
                action="auto_send",
                confidence=confidence,
                reason="High confidence and low-risk action",
                priority="low",
                requires_human=False,
            )

        if confidence >= self.MEDIUM_THRESHOLD:
            return RoutingDecision(
                action="queue_review",
                confidence=confidence,
                reason="Medium confidence; human review reduces false positives",
                priority="normal",
                requires_human=True,
            )

        return RoutingDecision(
            action="escalate",
            confidence=confidence,
            reason="Low confidence; human must decide before customer impact",
            priority="high",
            requires_human=True,
        )


hitl_decision_points = [
    {
        "id": 1,
        "name": "Large or unusual transfer approval",
        "trigger": "Transfer amount exceeds 50,000,000 VND or deviates from the customer's normal pattern.",
        "hitl_model": "human-in-the-loop",
        "context_needed": "Customer KYC status, account balance, device/session risk, recent transactions, beneficiary history.",
        "example": "A customer asks the assistant to transfer 120,000,000 VND to a first-time beneficiary.",
    },
    {
        "id": 2,
        "name": "Identity or credential change",
        "trigger": "The user requests password reset, phone/email change, account closure, or personal data update.",
        "hitl_model": "human-in-the-loop",
        "context_needed": "Verified identity evidence, OTP status, fraud flags, previous profile values, support ticket history.",
        "example": "A user wants to change the registered phone number and immediately reset online banking credentials.",
    },
    {
        "id": 3,
        "name": "Ambiguous safety or compliance response",
        "trigger": "LLM judge or policy classifier returns borderline scores, conflicting labels, or possible regulatory advice.",
        "hitl_model": "human-as-tiebreaker",
        "context_needed": "Conversation transcript, retrieved policy sources, judge scores, blocked patterns, proposed response.",
        "example": "The assistant drafts chargeback advice with confidence 0.72 and conflicting policy signals.",
    },
]


def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_cases = [
        ("Balance inquiry", 0.95, "general"),
        ("Interest rate question", 0.82, "general"),
        ("Ambiguous request", 0.55, "general"),
        ("Transfer $50,000", 0.98, "transfer_money"),
        ("Close my account", 0.91, "close_account"),
    ]

    print("Testing ConfidenceRouter:")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Conf':<6} {'Action Type':<18} {'Decision':<15} {'Priority':<10} {'Human?'}")
    print("-" * 80)

    for scenario, conf, action_type in test_cases:
        decision = router.route(scenario, conf, action_type)
        print(
            f"{scenario:<25} {conf:<6.2f} {action_type:<18} "
            f"{decision.action:<15} {decision.priority:<10} "
            f"{'Yes' if decision.requires_human else 'No'}"
        )

    print("=" * 80)


def test_hitl_points():
    """Display HITL decision points."""
    print("\nHITL Decision Points:")
    print("=" * 60)
    for point in hitl_decision_points:
        print(f"\n  Decision Point #{point['id']}: {point['name']}")
        print(f"    Trigger:  {point['trigger']}")
        print(f"    Model:    {point['hitl_model']}")
        print(f"    Context:  {point['context_needed']}")
        print(f"    Example:  {point['example']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
