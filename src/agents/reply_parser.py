"""Turn the agent's raw Gemini output into a reply and the intelligence it found."""

import contextlib
import json

import structlog
from pydantic import ValidationError

from src.api.schemas import AgentJsonResponse, ExtractedIntelligence
from src.llm import strip_code_fences

logger = structlog.get_logger()


def parse_agent_reply(raw: str) -> tuple[str, ExtractedIntelligence | None]:
    """Return ``(reply_text, intelligence)`` from the agent's one-pass JSON output.

    Three levels, from best to worst:
      1. The whole object validates as AgentJsonResponse.
      2. The text is a JSON object with reply_text; intelligence is kept if it parses.
      3. Anything else is used as the reply as-is, with no intelligence.

    Level 2 keeps raw JSON from ever reaching the scammer as a reply.
    """
    text = strip_code_fences(raw)

    try:
        parsed = AgentJsonResponse(**json.loads(text))
    except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
        logger.warning(f"Failed to parse agent JSON response: {exc}")
    else:
        intel = parsed.extracted_intelligence
        logger.info(
            "Successfully parsed JSON response from agent",
            emotional_tone=parsed.emotional_tone,
            intel_found=bool(
                intel.bankAccounts or intel.upiIds or intel.phoneNumbers or intel.phishingLinks
            ),
        )
        return parsed.reply_text, intel

    try:
        raw_json = json.loads(text)
    except json.JSONDecodeError:
        raw_json = None
    if isinstance(raw_json, dict) and "reply_text" in raw_json:
        logger.info("Extracted reply_text from partially-valid JSON")
        salvaged = None
        intel_dict = raw_json.get("extracted_intelligence")
        if isinstance(intel_dict, dict):
            # Skip intel that does not parse; the reply alone is still usable.
            with contextlib.suppress(Exception):
                salvaged = ExtractedIntelligence(**intel_dict)
        return str(raw_json["reply_text"]), salvaged

    logger.debug("Using raw response (JSON parsing failed)")
    return raw, None
