"""
Scoring Engine — Faithful replica of the GUVI hackathon evaluation rubric.

Implements all 5 scoring categories from FINAL_EVAL.md:
  1. Scam Detection (20 pts)
  2. Extracted Intelligence (30 pts) — dynamic per-item scoring
  3. Conversation Quality (30 pts) — turn count, questions, red flags, elicitation
  4. Engagement Quality (10 pts) — duration + message count tiers
  5. Response Structure (10 pts) — required + optional fields

Total: 100 points per scenario.  Weighted average across scenarios → final score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Key mapping: scenario fakeData keys → callback extractedIntelligence keys
# ---------------------------------------------------------------------------
FAKE_DATA_KEY_MAPPING: dict[str, str] = {
    "bankAccount": "bankAccounts",
    "upiId": "upiIds",
    "phoneNumber": "phoneNumbers",
    "phishingLink": "phishingLinks",
    "emailAddress": "emailAddresses",
    "caseId": "caseIds",
    "policyNumber": "policyNumbers",
    "orderNumber": "orderNumbers",
}


@dataclass
class ScoreBreakdown:
    """Per-scenario score breakdown mirroring FINAL_EVAL.md rubric."""

    scam_detection: int = 0          # max 20
    intelligence_extraction: float = 0.0  # max 30
    conversation_quality: float = 0.0     # max 30
    engagement_quality: int = 0      # max 10
    response_structure: int = 0      # max 10

    # Sub-scores for conversation quality
    turn_count_score: int = 0        # max 8
    questions_asked_score: int = 0   # max 4
    relevant_questions_score: int = 0  # max 3
    red_flag_score: int = 0          # max 8
    elicitation_score: float = 0.0   # max 7

    # Detail fields for diagnostics
    intel_matched: list[str] = field(default_factory=list)
    intel_missed: list[str] = field(default_factory=list)
    missing_required_fields: list[str] = field(default_factory=list)
    missing_optional_fields: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return (
            self.scam_detection
            + self.intelligence_extraction
            + self.conversation_quality
            + self.engagement_quality
            + self.response_structure
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scamDetection": self.scam_detection,
            "intelligenceExtraction": round(self.intelligence_extraction, 2),
            "conversationQuality": round(self.conversation_quality, 2),
            "engagementQuality": self.engagement_quality,
            "responseStructure": self.response_structure,
            "total": round(self.total, 2),
            "conversationQualityBreakdown": {
                "turnCount": self.turn_count_score,
                "questionsAsked": self.questions_asked_score,
                "relevantQuestions": self.relevant_questions_score,
                "redFlagIdentification": self.red_flag_score,
                "informationElicitation": round(self.elicitation_score, 2),
            },
            "intelMatched": self.intel_matched,
            "intelMissed": self.intel_missed,
            "missingRequiredFields": self.missing_required_fields,
            "missingOptionalFields": self.missing_optional_fields,
        }


# ===================================================================
#  1. Scam Detection — 20 pts
# ===================================================================

def score_scam_detection(final_output: dict) -> int:
    """scamDetected=true → 20, else 0."""
    return 20 if final_output.get("scamDetected") is True else 0


# ===================================================================
#  2. Extracted Intelligence — 30 pts (dynamic per-item)
# ===================================================================

def _normalize_for_match(value: str) -> str:
    """Strip non-alphanumeric, lowercase for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", value.lower().strip())


def _values_match(expected: str, actual: str) -> bool:
    """Check if expected value matches actual using multiple strategies."""
    exp_lower = expected.lower().strip()
    act_lower = actual.lower().strip()

    # Exact substring
    if exp_lower in act_lower or act_lower in exp_lower:
        return True

    # Normalized (digits-only for numbers, stripped for text)
    exp_norm = _normalize_for_match(expected)
    act_norm = _normalize_for_match(actual)
    if exp_norm and act_norm and (exp_norm in act_norm or act_norm in exp_norm):
        return True

    return False


def score_intelligence_extraction(
    final_output: dict,
    fake_data: dict[str, str],
) -> tuple[float, list[str], list[str]]:
    """
    Score intelligence extraction (max 30 pts).
    Points per item = 30 / total_fake_data_fields.
    Returns (score, matched_items, missed_items).
    """
    extracted = final_output.get("extractedIntelligence", {})
    total_fields = len(fake_data)
    if total_fields == 0:
        return 0.0, [], []

    points_per_item = 30.0 / total_fields
    matched: list[str] = []
    missed: list[str] = []

    for fake_key, fake_value in fake_data.items():
        output_key = FAKE_DATA_KEY_MAPPING.get(fake_key, fake_key)
        extracted_values = extracted.get(output_key, [])

        if isinstance(extracted_values, str):
            extracted_values = [extracted_values]

        found = False
        if isinstance(extracted_values, list):
            for v in extracted_values:
                if _values_match(fake_value, str(v)):
                    found = True
                    break

        if found:
            matched.append(f"{fake_key}={fake_value}")
        else:
            missed.append(f"{fake_key}={fake_value}")

    score = len(matched) * points_per_item
    return min(score, 30.0), matched, missed


# ===================================================================
#  3. Conversation Quality — 30 pts
# ===================================================================

# Red flag keywords that indicate investigative awareness
RED_FLAG_KEYWORDS = [
    "urgent", "otp", "verify", "block", "suspend", "fee", "transfer",
    "immediately", "expire", "click", "link", "password", "pin",
    "kyc", "compromised", "suspicious", "fraud", "scam", "phishing",
    "unauthorized", "deadline", "penalty", "fine", "arrest", "legal",
    "refund", "cashback", "prize", "lottery", "winner", "claim",
]

# Investigative question patterns
INVESTIGATIVE_PATTERNS = [
    r"what\s+is\s+your\s+(name|id|employee|badge|department)",
    r"(which|what)\s+(branch|office|department|company|organization)",
    r"can\s+(i|you)\s+(call|verify|confirm|check)",
    r"(official|registered|authentic)\s+(number|website|email|address)",
    r"(reference|complaint|ticket|case)\s+(number|id)",
    r"(how|why)\s+(did|do|should|would|can)",
    r"\?",  # Any question mark = likely a question
]

# Elicitation patterns (trying to extract info from scammer)
ELICITATION_PATTERNS = [
    r"(your|the)\s+(phone|number|contact|email|address|account|upi|id|name)",
    r"(give|share|provide|send|tell)\s+me\s+(your|the)",
    r"(where|how)\s+(can|should|do)\s+i\s+(pay|send|transfer|reach|contact)",
    r"(what|which)\s+(account|upi|number|link|website)",
    r"(call|reach|contact)\s+(you|back|the)",
]


def _count_patterns(text: str, patterns: list[str]) -> int:
    """Count how many distinct patterns match in the text."""
    count = 0
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            count += 1
    return count


def _count_questions(text: str) -> int:
    """Count questions in agent response text."""
    return text.count("?")


def _count_red_flags(text: str) -> int:
    """Count red flag keyword mentions in agent responses."""
    text_lower = text.lower()
    return sum(1 for kw in RED_FLAG_KEYWORDS if kw in text_lower)


def score_conversation_quality(
    agent_responses: list[str],
    turn_count: int,
) -> tuple[float, dict[str, int | float]]:
    """
    Score conversation quality (max 30 pts).
    
    Sub-categories:
      - Turn Count: 8 pts (≥8→8, ≥6→6, ≥4→3)
      - Questions Asked: 4 pts (≥5→4, ≥3→2, ≥1→1)
      - Relevant Questions: 3 pts (≥3→3, ≥2→2, ≥1→1)
      - Red Flag Identification: 8 pts (≥5→8, ≥3→5, ≥1→2)
      - Information Elicitation: 7 pts (1.5 per attempt, max 7)
    
    Returns (score, breakdown_dict).
    """
    all_text = " ".join(agent_responses)

    # Turn count score (max 8)
    if turn_count >= 8:
        tc = 8
    elif turn_count >= 6:
        tc = 6
    elif turn_count >= 4:
        tc = 3
    else:
        tc = 0

    # Questions asked (max 4)
    total_questions = sum(_count_questions(r) for r in agent_responses)
    if total_questions >= 5:
        qa = 4
    elif total_questions >= 3:
        qa = 2
    elif total_questions >= 1:
        qa = 1
    else:
        qa = 0

    # Relevant (investigative) questions (max 3)
    relevant_count = _count_patterns(all_text, INVESTIGATIVE_PATTERNS)
    if relevant_count >= 3:
        rq = 3
    elif relevant_count >= 2:
        rq = 2
    elif relevant_count >= 1:
        rq = 1
    else:
        rq = 0

    # Red flag identification (max 8)
    red_flags = _count_red_flags(all_text)
    if red_flags >= 5:
        rf = 8
    elif red_flags >= 3:
        rf = 5
    elif red_flags >= 1:
        rf = 2
    else:
        rf = 0

    # Information elicitation (max 7, 1.5 per attempt)
    elicitation_attempts = _count_patterns(all_text, ELICITATION_PATTERNS)
    ie = min(elicitation_attempts * 1.5, 7.0)

    total = tc + qa + rq + rf + ie
    breakdown = {
        "turn_count": tc,
        "questions_asked": qa,
        "relevant_questions": rq,
        "red_flags": rf,
        "elicitation": ie,
        "raw_questions_total": total_questions,
        "raw_relevant_count": relevant_count,
        "raw_red_flag_count": red_flags,
        "raw_elicitation_count": elicitation_attempts,
    }

    return min(total, 30.0), breakdown


# ===================================================================
#  4. Engagement Quality — 10 pts
# ===================================================================

def score_engagement_quality(final_output: dict) -> int:
    """
    Score engagement quality (max 10 pts).
    
    - duration > 0s:   +1
    - duration > 60s:  +2
    - duration > 180s: +1
    - messages > 0:    +2
    - messages ≥ 5:    +3
    - messages ≥ 10:   +1
    """
    duration = final_output.get("engagementDurationSeconds", 0)
    messages = final_output.get("totalMessagesExchanged", 0)

    # Also check nested engagementMetrics
    metrics = final_output.get("engagementMetrics", {})
    if not duration and metrics:
        duration = metrics.get("engagementDurationSeconds", 0)
    if not messages and metrics:
        messages = metrics.get("totalMessagesExchanged", 0)

    pts = 0
    if duration > 0:
        pts += 1
    if duration > 60:
        pts += 2
    if duration > 180:
        pts += 1
    if messages > 0:
        pts += 2
    if messages >= 5:
        pts += 3
    if messages >= 10:
        pts += 1
    return min(pts, 10)


# ===================================================================
#  5. Response Structure — 10 pts
# ===================================================================

def score_response_structure(final_output: dict) -> tuple[int, list[str], list[str]]:
    """
    Score response structure (max 10 pts).
    
    Required (+2 each, -1 penalty if missing):
      sessionId, scamDetected, extractedIntelligence
    Optional (+1 each):
      totalMessagesExchanged+engagementDurationSeconds (together), agentNotes,
      scamType, confidenceLevel
    
    Returns (score, missing_required, missing_optional).
    """
    pts = 0
    missing_required: list[str] = []
    missing_optional: list[str] = []

    # Required fields (+2 each)
    required = ["sessionId", "scamDetected", "extractedIntelligence"]
    for f in required:
        if f in final_output and final_output[f] is not None:
            pts += 2
        else:
            pts -= 1
            missing_required.append(f)

    # Optional fields (+1 each)
    # totalMessagesExchanged + engagementDurationSeconds together = 1 pt
    has_engagement = (
        "totalMessagesExchanged" in final_output
        and "engagementDurationSeconds" in final_output
    )
    if has_engagement:
        pts += 1
    else:
        missing_optional.append("totalMessagesExchanged+engagementDurationSeconds")

    optional_singles = ["agentNotes", "scamType", "confidenceLevel"]
    for f in optional_singles:
        if f in final_output and final_output[f]:
            pts += 1
        else:
            missing_optional.append(f)

    return max(pts, 0), missing_required, missing_optional


# ===================================================================
#  Full Scenario Scorer
# ===================================================================

def score_scenario(
    final_output: dict,
    fake_data: dict[str, str],
    agent_responses: list[str] | None = None,
    turn_count: int | None = None,
) -> ScoreBreakdown:
    """
    Score a single scenario against the GUVI evaluation rubric.
    
    Args:
        final_output: The callback payload / final output dict.
        fake_data: The scenario's planted fake intelligence.
        agent_responses: All agent reply strings (for conversation quality).
        turn_count: Number of conversation turns completed.
    
    Returns:
        ScoreBreakdown with full details.
    """
    breakdown = ScoreBreakdown()

    # 1. Scam Detection
    breakdown.scam_detection = score_scam_detection(final_output)

    # 2. Intelligence Extraction
    ie_score, matched, missed = score_intelligence_extraction(final_output, fake_data)
    breakdown.intelligence_extraction = ie_score
    breakdown.intel_matched = matched
    breakdown.intel_missed = missed

    # 3. Conversation Quality
    if agent_responses and turn_count:
        cq_score, cq_detail = score_conversation_quality(agent_responses, turn_count)
        breakdown.conversation_quality = cq_score
        breakdown.turn_count_score = cq_detail["turn_count"]
        breakdown.questions_asked_score = cq_detail["questions_asked"]
        breakdown.relevant_questions_score = cq_detail["relevant_questions"]
        breakdown.red_flag_score = cq_detail["red_flags"]
        breakdown.elicitation_score = cq_detail["elicitation"]

    # 4. Engagement Quality
    breakdown.engagement_quality = score_engagement_quality(final_output)

    # 5. Response Structure
    rs_score, missing_req, missing_opt = score_response_structure(final_output)
    breakdown.response_structure = rs_score
    breakdown.missing_required_fields = missing_req
    breakdown.missing_optional_fields = missing_opt

    return breakdown


def weighted_final_score(
    scenario_results: list[tuple[ScoreBreakdown, float]],
) -> float:
    """
    Compute weighted final score across scenarios.
    
    Args:
        scenario_results: List of (breakdown, weight) where weights sum to 1.0.
    
    Returns:
        Weighted score (0-100 scenario portion, before code quality).
    """
    return sum(b.total * w for b, w in scenario_results)
