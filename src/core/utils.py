"""
Lab 11 - Helper Utilities
"""
try:
    from google.genai import types
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

    types = _Types()


async def chat_with_agent(agent, runner, user_message: str, session_id=None):
    """Send a message to the agent and return response text plus session."""
    user_id = "student"
    app_name = runner.app_name

    session = None
    if session_id is not None:
        try:
            session = await runner.session_service.get_session(
                app_name=app_name, user_id=user_id, session_id=session_id
            )
        except (ValueError, KeyError):
            pass

    if session is None:
        session = await runner.session_service.create_session(
            app_name=app_name, user_id=user_id
        )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    final_response = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=content
    ):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_response += part.text

    return final_response, session
