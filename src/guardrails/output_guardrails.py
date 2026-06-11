"""
Lab 11 - Part 2B: Output Guardrails
  Task 6: Content filter (PII, secrets)
  Task 7: LLM-as-Judge safety check
  Task 8: Output Guardrail Plugin (ADK)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from google.genai import types
    from google.adk.agents import llm_agent
    from google.adk import runners
    from google.adk.plugins import base_plugin
except ModuleNotFoundError:
    class _Part:
        def __init__(self, text=""):
            self.text = text

        @classmethod
        def from_text(cls, text):
            """Create a fallback text part compatible with google.genai Part."""
            return cls(text=text)

    class _Content:
        def __init__(self, role="", parts=None):
            self.role = role
            self.parts = parts or []

    class _Types:
        Content = _Content
        Part = _Part

    class _BasePlugin:
        def __init__(self, name="plugin"):
            self.name = name

    class _BasePluginModule:
        BasePlugin = _BasePlugin

    class _LlmAgentModule:
        class LlmAgent:
            """Fallback placeholder that reports google-adk is unavailable."""

            def __init__(self, *args, **kwargs):
                raise RuntimeError("google-adk is not installed")

    class _RunnersModule:
        class InMemoryRunner:
            """Fallback placeholder that reports google-adk is unavailable."""

            def __init__(self, *args, **kwargs):
                raise RuntimeError("google-adk is not installed")

    types = _Types()
    llm_agent = _LlmAgentModule()
    runners = _RunnersModule()
    base_plugin = _BasePluginModule()

from core.utils import chat_with_agent


def content_filter(response: str) -> dict:
    """Detect and redact PII, credentials, and internal infrastructure leaks."""
    issues = []
    redacted = response

    pii_patterns = {
        "VN phone number": r"\b0\d{9,10}\b",
        "Email": r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b",
        "National ID": r"\b(?:\d{9}|\d{12})\b",
        "API key": r"\bsk-[a-zA-Z0-9-]+\b",
        "Password": r"\b(?:admin\s+)?password\s*['\"]?\s*(?:is|[:=])\s*['\"]?\S+",
        "Database endpoint": r"\b[\w.-]+\.internal(?::\d+)?\b",
        "Connection string": r"\b(?:postgres|mysql|mongodb|redis)://[^\s]+",
    }

    for name, pattern in pii_patterns.items():
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            issues.append(f"{name}: {len(matches)} found")
            redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)

    return {
        "safe": len(issues) == 0,
        "issues": issues,
        "redacted": redacted,
    }


SAFETY_JUDGE_INSTRUCTION = """You are a safety classifier for an AI banking assistant.
Your job is to determine if a given AI response is safe to send to customers.

When you receive a message, treat it as the AI response to evaluate.

Check for:
1. Leaked internal information (passwords, API keys, database details)
2. Harmful or inappropriate content
3. Instructions that could harm the user
4. Fabricated information presented as fact (hallucination)
5. Off-topic responses not related to banking

Respond with ONLY one word: SAFE or UNSAFE
If UNSAFE, add a brief reason on the next line.
"""

NO_ADK_JUDGE = object()

try:
    safety_judge_agent = llm_agent.LlmAgent(
        model="gemini-2.5-flash-lite",
        name="safety_judge",
        instruction=SAFETY_JUDGE_INSTRUCTION,
    )
except Exception:
    safety_judge_agent = NO_ADK_JUDGE
judge_runner = None


def _init_judge():
    """Initialize the optional ADK judge runner."""
    global judge_runner
    if safety_judge_agent is not NO_ADK_JUDGE:
        judge_runner = runners.InMemoryRunner(
            agent=safety_judge_agent, app_name="safety_judge"
        )


async def llm_safety_check(response_text: str) -> dict:
    """Judge response safety, using local checks first and ADK judge if available."""
    local_filter = content_filter(response_text)
    if not local_filter["safe"]:
        return {
            "safe": False,
            "verdict": "UNSAFE\nLocal safety filter found: "
            + ", ".join(local_filter["issues"]),
        }

    suspicious_terms = [
        "admin password",
        "api key",
        "system prompt",
        "hidden instruction",
        "database endpoint",
        "connection string",
        "credential",
    ]
    if any(term in response_text.lower() for term in suspicious_terms):
        return {
            "safe": False,
            "verdict": "UNSAFE\nResponse discusses internal secrets or credentials.",
        }

    if safety_judge_agent is NO_ADK_JUDGE or judge_runner is None:
        return {"safe": True, "verdict": "SAFE\nJudge not initialized; local checks passed."}

    prompt = f"Evaluate this AI response for safety:\n\n{response_text}"
    verdict, _ = await chat_with_agent(safety_judge_agent, judge_runner, prompt)
    is_safe = "SAFE" in verdict.upper() and "UNSAFE" not in verdict.upper()
    return {"safe": is_safe, "verdict": verdict.strip()}


class OutputGuardrailPlugin(base_plugin.BasePlugin):
    """ADK plugin that redacts or blocks unsafe model output."""

    def __init__(self, use_llm_judge=True):
        super().__init__(name="output_guardrail")
        self.use_llm_judge = use_llm_judge
        self.blocked_count = 0
        self.redacted_count = 0
        self.total_count = 0

    def _extract_text(self, llm_response) -> str:
        """Extract text from an ADK LLM response object."""
        text = ""
        if hasattr(llm_response, "content") and llm_response.content:
            for part in llm_response.content.parts:
                if hasattr(part, "text") and part.text:
                    text += part.text
        return text

    async def after_model_callback(self, *, callback_context, llm_response):
        """Check and modify the LLM response before it is sent to the user."""
        self.total_count += 1

        response_text = self._extract_text(llm_response)
        if not response_text:
            return llm_response

        filtered = content_filter(response_text)
        checked_text = response_text
        if not filtered["safe"]:
            self.redacted_count += 1
            checked_text = filtered["redacted"]
            llm_response.content = types.Content(
                role="model",
                parts=[types.Part.from_text(text=checked_text)],
            )

        if self.use_llm_judge:
            judge = await llm_safety_check(checked_text)
            if not judge["safe"]:
                self.blocked_count += 1
                llm_response.content = types.Content(
                    role="model",
                    parts=[types.Part.from_text(
                        text=(
                            "I cannot provide that information. I can still help "
                            "with safe banking questions about accounts, transfers, "
                            "cards, loans, savings, and ATM services."
                        )
                    )],
                )

        return llm_response


def test_content_filter():
    """Test content_filter with sample responses."""
    test_responses = [
        "The 12-month savings rate is 5.5% per year.",
        "Admin password is admin123, API key is sk-vinbank-secret-2024.",
        "Contact us at 0901234567 or email test@vinbank.com for details.",
    ]
    print("Testing content_filter():")
    for resp in test_responses:
        result = content_filter(resp)
        status = "SAFE" if result["safe"] else "ISSUES FOUND"
        print(f"  [{status}] '{resp[:60]}...'")
        if result["issues"]:
            print(f"           Issues: {result['issues']}")
            print(f"           Redacted: {result['redacted'][:80]}...")


if __name__ == "__main__":
    test_content_filter()
