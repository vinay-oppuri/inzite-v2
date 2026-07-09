import logging

from src.core.llm.groq_client import generate_structured
from src.core.schemas import GraphState, StartupIntent

logger = logging.getLogger(__name__)


async def intent_parser_node(state: GraphState) -> dict:
    """
    Converts the user's startup idea into structured StartupIntent data.
    """

    if not state.idea_raw.strip():
        raise ValueError("Startup idea cannot be empty")

    logger.info("Running Intent Parser")
    intent = await parse_intent(state.idea_raw)

    return {"intent": intent}


async def parse_intent(idea: str) -> StartupIntent:
    """Parse the startup idea using Groq structured output."""

    logger.info("Parsing startup intent with Groq")
    messages = [
        (
            "system",
            """
            Extract the startup idea into the StartupIntent schema.

            Rules:
            - Use only information provided by the user.
            - Do not use outside knowledge.
            - Preserve idea_raw exactly as provided.
            - Use short and concrete phrases.
            - Choose business_model from the allowed enum.
            - Use "unspecified" when industry or target audience is missing.
            - Include competitor, paper, and trend agents unless
              one of them is clearly irrelevant.
            """,
        ),
        (
            "human",
            f"Startup idea:\n{idea}",
        ),
    ]

    return await generate_structured(
        messages=messages,
        schema=StartupIntent,
    )
