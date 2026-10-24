"""Shared steps of the analyze routes: regex backup, intel hints and the final-turn summary."""

import time

from src.api.schemas import AnalyzeRequest, ExtractedIntelligence, HoneyPotResponse, ScamType
from src.api.session_store import accumulate_intel, get_previous_detection, get_session_start_time
from src.intelligence.extractor import ExtractionResult, IntelligenceExtractor

CONVERSATION_END = "[CONVERSATION_END]"

# The evaluator scores engagement duration; a turn takes about 25s in its own runs.
SECONDS_PER_TURN_FLOOR = 25

# What the agent should still try to draw out, keyed by the session intel field.
_MISSING_INTEL_HINTS = {
    "bankAccounts": "bank account number",
    "upiIds": "UPI ID",
    "phoneNumbers": "phone number",
    "phishingLinks": "suspicious link / website URL",
    "emailAddresses": "email address",
    "caseIds": "case / reference ID",
}


def history_as_dicts(request: AnalyzeRequest, include_current: bool) -> list[dict[str, str]]:
    """Return the conversation as sender/text dicts, optionally ending with the new message."""
    messages = [{"sender": m.sender, "text": m.text} for m in request.conversationHistory]
    if include_current:
        messages.append({"sender": "scammer", "text": request.message.text})
    return messages


def merge_regex_backup(
    intel: ExtractedIntelligence, regex_result: ExtractionResult
) -> ExtractedIntelligence:
    """Add regex finds to the validated LLM extraction, without duplicates."""
    if not regex_result.has_intelligence:
        return intel
    return intel.model_copy(
        update={
            "bankAccounts": list(set(intel.bankAccounts + regex_result.bank_accounts)),
            "upiIds": list(set(intel.upiIds + regex_result.upi_ids)),
            "phoneNumbers": list(set(intel.phoneNumbers + regex_result.phone_numbers)),
            "phishingLinks": list(set(intel.phishingLinks + regex_result.phishing_links)),
            "emailAddresses": list(set((intel.emailAddresses or []) + regex_result.emails)),
        }
    )


def missing_intel(session_intel: dict[str, set[str]]) -> list[str]:
    """Name the intel types this session has not captured yet, for the agent prompt."""
    return [hint for key, hint in _MISSING_INTEL_HINTS.items() if not session_intel.get(key)]


def to_scam_type(value: str | None) -> ScamType | None:
    """Map a detector scam_type string to the API enum; unknown types become OTHERS."""
    if not value:
        return None
    try:
        return ScamType(value)
    except ValueError:
        return ScamType.OTHERS


def engagement_seconds(session_id: str, turns: int, fallback_start: float) -> int:
    """Seconds since the session started, never less than the per-turn floor."""
    start = get_session_start_time(session_id) or fallback_start
    return max(int(time.time() - start), turns * SECONDS_PER_TURN_FLOOR)


def conversation_end_response(
    request: AnalyzeRequest, session_id: str, request_start_time: float
) -> HoneyPotResponse:
    """Build the final-turn summary the evaluator reads after [CONVERSATION_END].

    Regex runs again over the full history first, so a fresh Cloud Run instance
    with an empty in-memory session still reports the intel in the transcript.
    """
    history = history_as_dicts(request, include_current=False)
    if history:
        regex = IntelligenceExtractor().extract_from_conversation(history)
        if regex.has_intelligence:
            accumulate_intel(
                session_id,
                ExtractedIntelligence(
                    bankAccounts=regex.bank_accounts,
                    upiIds=regex.upi_ids,
                    phoneNumbers=regex.phone_numbers,
                    phishingLinks=regex.phishing_links,
                    emailAddresses=regex.emails,
                ),
            )

    accumulated = accumulate_intel(session_id, ExtractedIntelligence())
    total_msgs = len(request.conversationHistory) + 1
    prev_det = get_previous_detection(session_id)
    scam_type = prev_det.scam_type if prev_det else None
    confidence = float(prev_det.confidence) if prev_det else 0.0

    # The agent only replies after a scam detection, so honeypot turns in the
    # history prove one happened even when this instance lost the state.
    honeypot_replied = any(m["sender"] == "user" for m in history)
    if prev_det and prev_det.is_scam:
        scam_detected = True
    elif honeypot_replied:
        scam_detected = True
        scam_type = scam_type or "banking_fraud"
        confidence = confidence or 0.85
    else:
        scam_detected = False

    counts = ", ".join(
        f"{label}={len(accumulated.get(key, []))}"
        for label, key in (
            ("phones", "phoneNumbers"),
            ("accounts", "bankAccounts"),
            ("upi", "upiIds"),
            ("links", "phishingLinks"),
            ("emails", "emailAddresses"),
            ("caseIds", "caseIds"),
            ("policyNumbers", "policyNumbers"),
            ("orderNumbers", "orderNumbers"),
        )
    )
    notes = (
        f"Honeypot engaged {total_msgs} messages. "
        f"Scam type: {scam_type}. "
        f"Confidence: {confidence:.2f}. "
        f"Intelligence extracted: {counts}."
    )
    return HoneyPotResponse(
        status="success",
        reply="Thank you for your time. Goodbye.",
        sessionId=session_id,
        scamDetected=scam_detected,
        scamType=scam_type,
        confidenceLevel=confidence,
        totalMessagesExchanged=total_msgs,
        engagementDurationSeconds=engagement_seconds(session_id, total_msgs, request_start_time),
        extractedIntelligence=accumulated,
        agentNotes=notes,
    )
