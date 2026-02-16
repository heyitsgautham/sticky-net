"""
GUVI Hackathon Scoring Engine — exact replica of the evaluation system.

Mirrors the scoring logic from EVAL_SYS.md:
    - Scam Detection:           20 pts
    - Intelligence Extraction:  40 pts (10 per fakeData item, capped at 40)
    - Engagement Quality:       20 pts
    - Response Structure:       20 pts
    Total:                     100 pts per scenario
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Key mapping: fakeData keys → extractedIntelligence keys
# ---------------------------------------------------------------------------
FAKE_DATA_KEY_MAPPING: dict[str, str] = {
    "bankAccount": "bankAccounts",
    "upiId": "upiIds",
    "phoneNumber": "phoneNumbers",
    "phishingLink": "phishingLinks",
    "emailAddress": "emailAddresses",
}


# ---------------------------------------------------------------------------
# Score breakdown dataclass
# ---------------------------------------------------------------------------
@dataclass
class ScoreBreakdown:
    """Detailed per-scenario score breakdown with issue tracking."""

    scenario_id: str = ""
    scam_detection: float = 0.0
    intelligence_extraction: float = 0.0
    engagement_quality: float = 0.0
    response_structure: float = 0.0
    issues: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return (
            self.scam_detection
            + self.intelligence_extraction
            + self.engagement_quality
            + self.response_structure
        )

    def summary(self) -> str:
        lines = [
            f"Scenario: {self.scenario_id}",
            f"  Total:               {self.total:.1f}/100",
            f"  Scam Detection:      {self.scam_detection:.1f}/20",
            f"  Intel Extraction:    {self.intelligence_extraction:.1f}/40",
            f"  Engagement Quality:  {self.engagement_quality:.1f}/20",
            f"  Response Structure:  {self.response_structure:.1f}/20",
        ]
        if self.issues:
            lines.append("  Issues:")
            for issue in self.issues:
                lines.append(f"    - {issue}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 1. Scam Detection (20 pts)
# ---------------------------------------------------------------------------
def score_scam_detection(final_output: dict, *, breakdown: ScoreBreakdown | None = None) -> float:
    """scamDetected=true → 20 pts, else 0."""
    if final_output.get("scamDetected", False):
        return 20.0
    if breakdown:
        breakdown.issues.append("scamDetected is False or missing — lost 20 pts")
    return 0.0


# ---------------------------------------------------------------------------
# 2. Intelligence Extraction (40 pts)
# ---------------------------------------------------------------------------
def score_intelligence_extraction(
    final_output: dict,
    fake_data: dict,
    *,
    breakdown: ScoreBreakdown | None = None,
) -> float:
    """10 pts per fakeData item found via substring match, capped at 40."""
    extracted = final_output.get("extractedIntelligence", {})
    points = 0.0

    for fake_key, fake_value in fake_data.items():
        output_key = FAKE_DATA_KEY_MAPPING.get(fake_key, fake_key)
        extracted_values = extracted.get(output_key, [])

        matched = False
        if isinstance(extracted_values, list):
            if any(fake_value in str(v) for v in extracted_values):
                matched = True
        elif isinstance(extracted_values, str):
            if fake_value in extracted_values:
                matched = True

        if matched:
            points += 10.0
        elif breakdown:
            breakdown.issues.append(
                f"fakeData '{fake_key}' = '{fake_value}' NOT found in "
                f"extractedIntelligence.{output_key} — lost 10 pts"
            )

    return min(points, 40.0)


# ---------------------------------------------------------------------------
# 3. Engagement Quality (20 pts)
# ---------------------------------------------------------------------------
def score_engagement_quality(
    final_output: dict,
    *,
    breakdown: ScoreBreakdown | None = None,
) -> float:
    """
    +5 if duration > 0
    +5 if duration > 60
    +5 if messages > 0
    +5 if messages >= 5
    """
    metrics = final_output.get("engagementMetrics", {})
    duration = metrics.get("engagementDurationSeconds", 0)
    messages = metrics.get("totalMessagesExchanged", 0)

    points = 0.0
    if duration > 0:
        points += 5.0
    else:
        if breakdown:
            breakdown.issues.append(
                "engagementDurationSeconds is 0 or missing — lost 5 pts"
            )
    if duration > 60:
        points += 5.0
    else:
        if breakdown:
            breakdown.issues.append(
                "engagementDurationSeconds <= 60 — lost 5 pts"
            )
    if messages > 0:
        points += 5.0
    else:
        if breakdown:
            breakdown.issues.append(
                "totalMessagesExchanged is 0 or missing — lost 5 pts"
            )
    if messages >= 5:
        points += 5.0
    else:
        if breakdown:
            breakdown.issues.append(
                "totalMessagesExchanged < 5 — lost 5 pts"
            )

    return points


# ---------------------------------------------------------------------------
# 4. Response Structure (20 pts)
# ---------------------------------------------------------------------------
def score_response_structure(
    final_output: dict,
    *,
    breakdown: ScoreBreakdown | None = None,
) -> float:
    """
    Required: status (+5), scamDetected (+5), extractedIntelligence (+5)
    Optional: engagementMetrics (+2.5), agentNotes (+2.5)
    """
    points = 0.0
    required_fields = ["status", "scamDetected", "extractedIntelligence"]
    optional_fields = ["engagementMetrics", "agentNotes"]

    for f in required_fields:
        if f in final_output:
            points += 5.0
        elif breakdown:
            breakdown.issues.append(f"Required field '{f}' missing — lost 5 pts")

    for f in optional_fields:
        if f in final_output and final_output[f]:
            points += 2.5
        elif breakdown:
            breakdown.issues.append(
                f"Optional field '{f}' missing or empty — lost 2.5 pts"
            )

    return min(points, 20.0)


# ---------------------------------------------------------------------------
# Full per-scenario scoring
# ---------------------------------------------------------------------------
def score_scenario(final_output: dict, fake_data: dict, scenario_id: str = "") -> ScoreBreakdown:
    """Score a single scenario — returns full breakdown with issues."""
    bd = ScoreBreakdown(scenario_id=scenario_id)
    bd.scam_detection = score_scam_detection(final_output, breakdown=bd)
    bd.intelligence_extraction = score_intelligence_extraction(
        final_output, fake_data, breakdown=bd
    )
    bd.engagement_quality = score_engagement_quality(final_output, breakdown=bd)
    bd.response_structure = score_response_structure(final_output, breakdown=bd)
    return bd


def score_scenario_dict(final_output: dict, fake_data: dict) -> dict:
    """Legacy dict-based scoring — returns dict with keys matching GUVI evaluator."""
    sd = score_scam_detection(final_output)
    ie = score_intelligence_extraction(final_output, fake_data)
    eq = score_engagement_quality(final_output)
    rs = score_response_structure(final_output)
    return {
        "scamDetection": sd,
        "intelligenceExtraction": ie,
        "engagementQuality": eq,
        "responseStructure": rs,
        "total": sd + ie + eq + rs,
    }


# ---------------------------------------------------------------------------
# Weighted final score across scenarios
# ---------------------------------------------------------------------------
def weighted_final_score(
    breakdowns: list[ScoreBreakdown],
    weights: list[float],
) -> float:
    """
    Compute weighted average across scenarios.
    weights: list of floats that sum to 1.0
    """
    assert len(breakdowns) == len(weights), (
        f"Mismatched lengths: {len(breakdowns)} breakdowns vs {len(weights)} weights"
    )
    return sum(bd.total * w for bd, w in zip(breakdowns, weights))


def weighted_final_score_dicts(
    scenario_scores: list[dict],
    weights: list[float],
) -> float:
    """Legacy dict-based weighted scoring."""
    assert len(scenario_scores) == len(weights)
    return sum(s["total"] * w for s, w in zip(scenario_scores, weights))
