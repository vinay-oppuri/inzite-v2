from __future__ import annotations

from src.core.llm.gemini_client import generate_structured
from src.core.schemas import GraphState, StartupIntent


async def intent_parser_node(state: GraphState) -> dict:
    """Parse the raw startup idea through Gemini structured output."""
    idea = _normalize_text(state.idea_raw)
    return {"intent": await _parse_with_gemini(idea)}


async def _parse_with_gemini(idea: str) -> StartupIntent:
    return await generate_structured(
        [
            (
                "system",
                "You extract a startup idea into the StartupIntent schema. "
                "Use only the user's idea, not outside knowledge. "
                "Keep idea_raw exactly as the user wrote it. "
                "Use concise, concrete phrases. "
                "Choose business_model from the enum. "
                "Use 'unspecified' for missing industry or audience. "
                "For agent_triggers, include competitor, paper, and trend unless "
                "one is clearly irrelevant.",
            ),
            ("human", f"Startup idea:\n{idea}"),
        ],
        StartupIntent,
    )


def _normalize_text(text: str) -> str:
    return " ".join(text.split())
