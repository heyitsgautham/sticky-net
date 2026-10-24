"""Pull plain text out of Gemini responses."""

from google.genai import types


def response_text(response: types.GenerateContentResponse) -> str:
    """Join the text parts of every candidate.

    Gemini 3 returns thought_signature parts next to text parts, and reading
    ``response.text`` logs a warning about them, so this reads text parts only.
    """
    if not response.candidates:
        return ""

    text_parts = []
    for candidate in response.candidates:
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)

    return "".join(text_parts)


def strip_code_fences(raw: str) -> str:
    """Remove a surrounding ```json or ``` fence and return the inner text."""
    text = raw.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
