"""Response agent using Pydantic AI with knowledge-base retrieval tools."""

import logging

from pydantic_ai import Agent, RunContext

from app.ai.schemas import AgentReply
from app.config import resolve_provider_model, settings
from app.db import get_db

logger = logging.getLogger(__name__)

AGENT_PROMPT = """You are a customer support agent for Harbor & Pine, an outdoor and home goods retailer selling inflatable paddle boards and flat-pack shelving.

Use your tools to retrieve authoritative policies from the knowledge base before answering.

Tone and brand guidelines:
- Friendly, calm, concise, and helpful.
- Address the customer by first name if known.
- Answer the core question within the first two sentences.
- Use numbered lists for instructional steps.
- Keep the response under 150 words.
- Conclude with:
  Best regards,
  Harbor & Pine Support

Strict constraints:
- NEVER mention AI, prompts, bots, or the knowledge base.
- NEVER promise refunds, shipments, replacements, dates, or calls directly. If an operational action is required, escalate to a human colleague.
- If policy information is insufficient to answer with certainty, choose action='escalate'.
"""


def create_response_agent() -> Agent[None, AgentReply]:
    """Create Pydantic AI agent equipped with knowledge base tools."""
    provider_model = resolve_provider_model(settings.AGENT_MODEL, settings.AI_PROVIDER)

    agent = Agent(
        model=provider_model,
        output_type=AgentReply,
        system_prompt=AGENT_PROMPT,
    )

    @agent.tool
    def list_sections(ctx: RunContext[None]) -> list[str]:
        """List available policy sections in the knowledge base."""
        return get_db().list_kb_sections()

    @agent.tool
    def read_section(ctx: RunContext[None], section_name: str) -> str:
        """Read all policy entries for a specific knowledge base section."""
        entries = get_db().get_kb_entries(section_name)
        if not entries:
            return f"Section '{section_name}' not found."
        formatted = []
        for e in entries:
            formatted.append(f"## {e['title']}\n{e['content']}")
        return "\n\n".join(formatted)

    return agent


async def generate_agent_reply(
    email_text: str,
    subject: str = "",
    section: str = "general",
) -> AgentReply:
    """Generate structured reply using agent or deterministic fallback."""
    if not settings.ANTHROPIC_API_KEY or settings.APP_ENV == "testing":
        # Offline deterministic default
        return AgentReply(
            action="reply",
            reply="Thank you for reaching out to Harbor & Pine. We are processing your request.",
            reasoning="Offline fallback",
            enough_information=True,
            promises_an_action=False,
        )

    try:
        agent = create_response_agent()
        query = (
            f"Subject: {subject}\nCategory: {section}\n\nEmail Thread:\n{email_text}"
        )
        result = await agent.run(query)
        return getattr(result, "output", getattr(result, "data", None))
    except Exception as e:
        logger.warning("Agent run failed (%s); escalating safely", e)
        return AgentReply(
            action="escalate",
            reply="Thank you for your message. A member of our support team will review your inquiry and follow up shortly.",
            reasoning=f"Model error fallback: {e}",
            enough_information=False,
            promises_an_action=False,
        )
