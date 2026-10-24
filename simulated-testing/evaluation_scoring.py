"""GUVI's 100-point rubric for one scenario, replicated from EVAL_SYS.md."""

from dataclasses import dataclass, field

# GUVI scoring: fakeData key → extractedIntelligence response key
FAKE_DATA_KEY_MAPPING = {
    "bankAccount": "bankAccounts",
    "upiId": "upiIds",
    "phoneNumber": "phoneNumbers",
    "phishingLink": "phishingLinks",
    "emailAddress": "emailAddresses",
}


# ---------------------------------------------------------------------------
# GUVI Scoring (from EVAL_SYS.md — exact replication)
# ---------------------------------------------------------------------------
@dataclass
class ScoreBreakdown:
    """Per-scenario score breakdown matching GUVI's 4 dimensions."""
    scenario_id: str = ""
    scam_detection: float = 0.0       # /20
    intelligence_extraction: float = 0.0  # /40
    engagement_quality: float = 0.0   # /20
    response_structure: float = 0.0   # /20
    issues: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return (self.scam_detection + self.intelligence_extraction +
                self.engagement_quality + self.response_structure)

    def summary(self) -> str:
        parts = [
            f"  {self.scenario_id}: {self.total:.1f}/100",
            f"    Detection:    {self.scam_detection:.0f}/20",
            f"    Intelligence: {self.intelligence_extraction:.0f}/40",
            f"    Engagement:   {self.engagement_quality:.0f}/20",
            f"    Structure:    {self.response_structure:.0f}/20",
        ]
        if self.issues:
            parts.append("    Issues:")
            for issue in self.issues:
                parts.append(f"      - {issue}")
        return "\n".join(parts)


def score_scam_detection(final_output: dict) -> tuple[float, list[str]]:
    """20 pts if scamDetected == True."""
    issues = []
    detected = final_output.get("scamDetected", False)
    if detected is True or detected == "true" or detected == 1:
        return 20.0, issues
    issues.append(f"scamDetected={detected} (expected True)")
    return 0.0, issues


def score_intelligence(final_output: dict, fake_data: dict) -> tuple[float, list[str]]:
    """10 pts per fakeData item matched (substring), capped at 40."""
    issues = []
    if not fake_data:
        return 0.0, issues

    intel = final_output.get("extractedIntelligence", {})
    score = 0.0

    for fake_key, fake_value in fake_data.items():
        response_key = FAKE_DATA_KEY_MAPPING.get(fake_key, fake_key)
        found = False

        # Check in the mapped response key
        values = intel.get(response_key, [])
        if isinstance(values, list):
            for v in values:
                if fake_value in str(v):
                    found = True
                    break
        elif isinstance(values, str):
            if fake_value in values:
                found = True

        # Also search across ALL intel fields (broader match)
        if not found:
            for key, val in intel.items():
                if isinstance(val, list):
                    for v in val:
                        if fake_value in str(v):
                            found = True
                            break
                elif isinstance(val, str):
                    if fake_value in val:
                        found = True
                if found:
                    break

        if found:
            score += 10.0
        else:
            issues.append(f"Missing {fake_key}={fake_value} (looked in {response_key})")

    return min(score, 40.0), issues


def score_engagement(final_output: dict) -> tuple[float, list[str]]:
    """
    20 pts total:
      +5 if engagementDurationSeconds > 0
      +5 if engagementDurationSeconds > 60
      +5 if totalMessagesExchanged > 0
      +5 if totalMessagesExchanged >= 5
    """
    issues = []
    score = 0.0
    metrics = final_output.get("engagementMetrics", {})
    duration = metrics.get("engagementDurationSeconds", 0)
    messages = metrics.get("totalMessagesExchanged", 0)

    if duration > 0:
        score += 5.0
    else:
        issues.append("engagementDurationSeconds == 0")
    if duration > 60:
        score += 5.0
    else:
        issues.append(f"engagementDurationSeconds={duration} (want >60)")
    if messages > 0:
        score += 5.0
    else:
        issues.append("totalMessagesExchanged == 0")
    if messages >= 5:
        score += 5.0
    else:
        issues.append(f"totalMessagesExchanged={messages} (want >=5)")

    return score, issues


def score_structure(final_output: dict) -> tuple[float, list[str]]:
    """
    20 pts total:
      +5 if status present
      +5 if scamDetected present
      +5 if extractedIntelligence present
      +2.5 if engagementMetrics present
      +2.5 if agentNotes present
    """
    issues = []
    score = 0.0

    if "status" in final_output:
        score += 5.0
    else:
        issues.append("Missing 'status'")

    if "scamDetected" in final_output:
        score += 5.0
    else:
        issues.append("Missing 'scamDetected'")

    if "extractedIntelligence" in final_output:
        score += 5.0
    else:
        issues.append("Missing 'extractedIntelligence'")

    if "engagementMetrics" in final_output:
        score += 2.5
    else:
        issues.append("Missing 'engagementMetrics'")

    if final_output.get("agentNotes"):
        score += 2.5
    else:
        issues.append("Missing/empty 'agentNotes'")

    return score, issues


def score_scenario(final_output: dict, fake_data: dict, scenario_id: str) -> ScoreBreakdown:
    """Full 100-point scoring for one scenario."""
    bd = ScoreBreakdown(scenario_id=scenario_id)

    det, det_issues = score_scam_detection(final_output)
    bd.scam_detection = det
    bd.issues.extend(det_issues)

    intel, intel_issues = score_intelligence(final_output, fake_data)
    bd.intelligence_extraction = intel
    bd.issues.extend(intel_issues)

    eng, eng_issues = score_engagement(final_output)
    bd.engagement_quality = eng
    bd.issues.extend(eng_issues)

    struct, struct_issues = score_structure(final_output)
    bd.response_structure = struct
    bd.issues.extend(struct_issues)

    return bd
