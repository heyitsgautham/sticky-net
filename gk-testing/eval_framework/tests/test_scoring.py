"""
Tests for the scoring engine — validates that scoring matches FINAL_EVAL.md exactly.

These tests do NOT require a running API server. They test the scoring
logic in isolation to ensure our scoring replica is accurate.
"""

import pytest

from eval_framework.scoring import (
    ScoreBreakdown,
    score_scam_detection,
    score_intelligence_extraction,
    score_conversation_quality,
    score_engagement_quality,
    score_response_structure,
    score_scenario,
    weighted_final_score,
)
from eval_framework.scenarios import (
    BANK_FRAUD_SCENARIO,
    UPI_FRAUD_SCENARIO,
    PHISHING_SCENARIO,
    TECH_SUPPORT_SCENARIO,
    INSURANCE_SCAM_SCENARIO,
    STANDARD_WEIGHTS,
)


# ===================================================================
#  Scam Detection (20 pts)
# ===================================================================

class TestScamDetection:
    def test_detected_true_gives_20(self):
        assert score_scam_detection({"scamDetected": True}) == 20

    def test_detected_false_gives_0(self):
        assert score_scam_detection({"scamDetected": False}) == 0

    def test_missing_gives_0(self):
        assert score_scam_detection({}) == 0

    def test_none_gives_0(self):
        assert score_scam_detection({"scamDetected": None}) == 0


# ===================================================================
#  Intelligence Extraction (30 pts)
# ===================================================================

class TestIntelligenceExtraction:
    def test_all_matched_3_items(self):
        """3 items → 10 pts each → 30 pts max."""
        output = {
            "extractedIntelligence": {
                "bankAccounts": ["50100487652341"],
                "upiIds": ["sbi.security@axisbank"],
                "phoneNumbers": ["+91-9823456710"],
            }
        }
        fake_data = BANK_FRAUD_SCENARIO["fakeData"]
        score, matched, missed = score_intelligence_extraction(output, fake_data)
        assert score == 30.0
        assert len(matched) == 3
        assert len(missed) == 0

    def test_partial_match_2_of_3(self):
        """2 of 3 items → 20 pts."""
        output = {
            "extractedIntelligence": {
                "bankAccounts": ["50100487652341"],
                "upiIds": ["sbi.security@axisbank"],
                "phoneNumbers": [],
            }
        }
        fake_data = BANK_FRAUD_SCENARIO["fakeData"]
        score, matched, missed = score_intelligence_extraction(output, fake_data)
        assert score == 20.0
        assert len(matched) == 2
        assert len(missed) == 1

    def test_no_match(self):
        output = {"extractedIntelligence": {"bankAccounts": [], "upiIds": [], "phoneNumbers": []}}
        fake_data = BANK_FRAUD_SCENARIO["fakeData"]
        score, matched, missed = score_intelligence_extraction(output, fake_data)
        assert score == 0.0
        assert len(missed) == 3

    def test_2_items_scenario(self):
        """2 items → 15 pts each → max 30."""
        output = {
            "extractedIntelligence": {
                "phishingLinks": ["http://amaz0n-prime-deals.fakesite.com/claim?uid=78234"],
                "emailAddresses": ["deals@amaz0n-prime-offers.com"],
            }
        }
        fake_data = PHISHING_SCENARIO["fakeData"]
        score, matched, missed = score_intelligence_extraction(output, fake_data)
        assert score == 30.0
        assert len(matched) == 2

    def test_fuzzy_phone_match(self):
        """Phone number without +91- prefix should still match."""
        output = {
            "extractedIntelligence": {
                "phoneNumbers": ["9823456710"],
                "bankAccounts": [],
                "upiIds": [],
            }
        }
        fake_data = {"phoneNumber": "+91-9823456710"}
        score, matched, missed = score_intelligence_extraction(output, fake_data)
        assert score == 30.0  # 1 item → 30/1 = 30

    def test_substring_match(self):
        """Extracted value containing expected value should match."""
        output = {
            "extractedIntelligence": {
                "bankAccounts": ["Account: 50100487652341 (SBI)"],
            }
        }
        fake_data = {"bankAccount": "50100487652341"}
        score, matched, missed = score_intelligence_extraction(output, fake_data)
        assert score == 30.0

    def test_empty_fake_data(self):
        score, matched, missed = score_intelligence_extraction({}, {})
        assert score == 0.0

    def test_dynamic_points_per_item(self):
        """With 5 items, each is worth 6 pts (30/5)."""
        output = {
            "extractedIntelligence": {
                "bankAccounts": ["1234"],
                "upiIds": ["x@y"],
                "phoneNumbers": ["+91-1234567890"],
                "emailAddresses": ["a@b.com"],
                "phishingLinks": ["http://evil.com"],
            }
        }
        fake_data = {
            "bankAccount": "1234",
            "upiId": "x@y",
            "phoneNumber": "+91-1234567890",
            "emailAddress": "a@b.com",
            "phishingLink": "http://evil.com",
        }
        score, matched, missed = score_intelligence_extraction(output, fake_data)
        assert score == 30.0
        assert len(matched) == 5


# ===================================================================
#  Conversation Quality (30 pts)
# ===================================================================

class TestConversationQuality:
    def test_high_quality_responses(self, good_agent_responses):
        score, breakdown = score_conversation_quality(good_agent_responses, turn_count=10)
        assert score >= 25.0, f"Expected ≥25 for good responses, got {score}: {breakdown}"
        # Should get max turn count
        assert breakdown["turn_count"] == 8
        # Should have plenty of questions
        assert breakdown["questions_asked"] >= 2

    def test_no_responses(self):
        score, breakdown = score_conversation_quality([], turn_count=0)
        assert score == 0.0

    def test_single_turn(self):
        score, breakdown = score_conversation_quality(["Hello?"], turn_count=1)
        assert breakdown["turn_count"] == 0  # <4 turns = 0

    def test_4_turns_gives_3_pts(self):
        responses = ["Response?"] * 4
        score, breakdown = score_conversation_quality(responses, turn_count=4)
        assert breakdown["turn_count"] == 3

    def test_6_turns_gives_6_pts(self):
        responses = ["Response?"] * 6
        score, breakdown = score_conversation_quality(responses, turn_count=6)
        assert breakdown["turn_count"] == 6

    def test_8_turns_gives_8_pts(self):
        responses = ["Response?"] * 8
        score, breakdown = score_conversation_quality(responses, turn_count=8)
        assert breakdown["turn_count"] == 8

    def test_red_flag_detection(self):
        responses = [
            "This seems urgent and suspicious. Why do you need my OTP?",
            "You're asking me to verify my account - this looks like a scam.",
            "The link you sent appears to be phishing. I won't click it.",
        ]
        score, breakdown = score_conversation_quality(responses, turn_count=8)
        assert breakdown["red_flags"] >= 5, f"Should detect many red flags: {breakdown}"

    def test_elicitation_scoring(self):
        responses = [
            "Can you give me your phone number?",
            "What is your account number?",
            "Where should I send the payment? What's your UPI ID?",
            "Tell me your email address so I can contact you.",
            "How can I reach you? Your contact number please.",
        ]
        score, breakdown = score_conversation_quality(responses, turn_count=8)
        assert breakdown["elicitation"] >= 4.5, f"Should score high on elicitation: {breakdown}"


# ===================================================================
#  Engagement Quality (10 pts)
# ===================================================================

class TestEngagementQuality:
    def test_perfect_engagement(self):
        output = {
            "engagementDurationSeconds": 300,
            "totalMessagesExchanged": 20,
        }
        assert score_engagement_quality(output) == 10

    def test_zero_engagement(self):
        assert score_engagement_quality({}) == 0

    def test_duration_only(self):
        output = {"engagementDurationSeconds": 200, "totalMessagesExchanged": 0}
        score = score_engagement_quality(output)
        # duration>0: +1, >60: +2, >180: +1 = 4
        assert score == 4

    def test_messages_only(self):
        output = {"engagementDurationSeconds": 0, "totalMessagesExchanged": 12}
        score = score_engagement_quality(output)
        # messages>0: +2, >=5: +3, >=10: +1 = 6
        assert score == 6

    def test_nested_metrics(self):
        output = {
            "engagementMetrics": {
                "engagementDurationSeconds": 100,
                "totalMessagesExchanged": 6,
            }
        }
        score = score_engagement_quality(output)
        # duration>0: +1, >60: +2, messages>0: +2, >=5: +3 = 8
        assert score == 8

    def test_duration_tiers(self):
        # Exactly at boundary
        assert score_engagement_quality({"engagementDurationSeconds": 1, "totalMessagesExchanged": 0}) == 1
        assert score_engagement_quality({"engagementDurationSeconds": 61, "totalMessagesExchanged": 0}) == 3
        assert score_engagement_quality({"engagementDurationSeconds": 181, "totalMessagesExchanged": 0}) == 4


# ===================================================================
#  Response Structure (10 pts)
# ===================================================================

class TestResponseStructure:
    def test_perfect_structure(self, perfect_bank_fraud_output):
        score, missing_req, missing_opt = score_response_structure(perfect_bank_fraud_output)
        assert score == 10
        assert len(missing_req) == 0

    def test_minimal_structure(self):
        output = {"sessionId": "x", "scamDetected": True, "extractedIntelligence": {}}
        score, missing_req, missing_opt = score_response_structure(output)
        # Required: 3*2 = 6. Optional all missing: 0. Total = 6
        assert score == 6
        assert len(missing_req) == 0

    def test_empty_output(self):
        score, missing_req, missing_opt = score_response_structure({})
        # All 3 required missing: 3 * (-1) = -3 → clamped to 0
        assert score == 0
        assert len(missing_req) == 3

    def test_partial_optional(self):
        output = {
            "sessionId": "x",
            "scamDetected": True,
            "extractedIntelligence": {"bankAccounts": []},
            "agentNotes": "Some notes",
        }
        score, missing_req, missing_opt = score_response_structure(output)
        # Required: 6, Optional: agentNotes = 1
        assert score == 7


# ===================================================================
#  Full Scenario Scoring
# ===================================================================

class TestFullScenarioScoring:
    def test_perfect_bank_fraud(self, perfect_bank_fraud_output, good_agent_responses):
        breakdown = score_scenario(
            final_output=perfect_bank_fraud_output,
            fake_data=BANK_FRAUD_SCENARIO["fakeData"],
            agent_responses=good_agent_responses,
            turn_count=10,
        )
        assert breakdown.scam_detection == 20
        assert breakdown.intelligence_extraction == 30.0
        assert breakdown.engagement_quality == 10
        assert breakdown.total >= 85.0, f"Expected ≥85, got {breakdown.total}"

    def test_perfect_phishing(self, perfect_phishing_output, good_agent_responses):
        breakdown = score_scenario(
            final_output=perfect_phishing_output,
            fake_data=PHISHING_SCENARIO["fakeData"],
            agent_responses=good_agent_responses,
            turn_count=10,
        )
        assert breakdown.scam_detection == 20
        assert breakdown.intelligence_extraction == 30.0
        assert breakdown.total >= 85.0

    def test_minimal_output_scores_low(self, minimal_output):
        breakdown = score_scenario(
            final_output=minimal_output,
            fake_data=BANK_FRAUD_SCENARIO["fakeData"],
        )
        assert breakdown.total <= 10.0, f"Minimal output should score ≤10, got {breakdown.total}"

    def test_score_breakdown_to_dict(self, perfect_bank_fraud_output, good_agent_responses):
        breakdown = score_scenario(
            final_output=perfect_bank_fraud_output,
            fake_data=BANK_FRAUD_SCENARIO["fakeData"],
            agent_responses=good_agent_responses,
            turn_count=10,
        )
        d = breakdown.to_dict()
        assert "scamDetection" in d
        assert "intelligenceExtraction" in d
        assert "conversationQuality" in d
        assert "engagementQuality" in d
        assert "responseStructure" in d
        assert "total" in d
        assert "conversationQualityBreakdown" in d


# ===================================================================
#  Weighted Final Score
# ===================================================================

class TestWeightedFinalScore:
    def test_equal_weights(self):
        b1 = ScoreBreakdown(scam_detection=20, intelligence_extraction=30,
                            conversation_quality=30, engagement_quality=10,
                            response_structure=10)
        b2 = ScoreBreakdown(scam_detection=20, intelligence_extraction=20,
                            conversation_quality=20, engagement_quality=8,
                            response_structure=8)
        # 100 * 0.5 + 76 * 0.5 = 88
        score = weighted_final_score([(b1, 0.5), (b2, 0.5)])
        assert abs(score - 88.0) < 0.01

    def test_hackathon_weights(self):
        """Test with 35/35/30 weights like hackathon."""
        b1 = ScoreBreakdown(scam_detection=20, intelligence_extraction=30,
                            conversation_quality=25, engagement_quality=10,
                            response_structure=10)  # 95
        b2 = ScoreBreakdown(scam_detection=20, intelligence_extraction=30,
                            conversation_quality=25, engagement_quality=10,
                            response_structure=10)  # 95
        b3 = ScoreBreakdown(scam_detection=20, intelligence_extraction=15,
                            conversation_quality=20, engagement_quality=8,
                            response_structure=8)   # 71
        # 95*0.35 + 95*0.35 + 71*0.30 = 33.25 + 33.25 + 21.3 = 87.8
        score = weighted_final_score([(b1, 0.35), (b2, 0.35), (b3, 0.30)])
        assert abs(score - 87.8) < 0.1

    def test_all_perfect(self):
        perfect = ScoreBreakdown(
            scam_detection=20,
            intelligence_extraction=30,
            conversation_quality=30,
            engagement_quality=10,
            response_structure=10,
        )
        score = weighted_final_score([(perfect, 0.35), (perfect, 0.35), (perfect, 0.30)])
        assert score == 100.0


# ===================================================================
#  Score Target Tests — What we NEED to achieve to win
# ===================================================================

class TestScoreTargets:
    """
    These tests define the score targets we need to hit for winning.
    They serve as regression benchmarks as we improve the system.
    """

    def test_minimum_viable_score(self, perfect_bank_fraud_output, perfect_upi_fraud_output, perfect_phishing_output, good_agent_responses):
        """We need weighted score ≥ 80 to be competitive."""
        scores = []
        for output, fake_data in [
            (perfect_bank_fraud_output, BANK_FRAUD_SCENARIO["fakeData"]),
            (perfect_upi_fraud_output, UPI_FRAUD_SCENARIO["fakeData"]),
            (perfect_phishing_output, PHISHING_SCENARIO["fakeData"]),
        ]:
            b = score_scenario(
                final_output=output,
                fake_data=fake_data,
                agent_responses=good_agent_responses,
                turn_count=10,
            )
            scores.append(b)

        ws = weighted_final_score(list(zip(scores, STANDARD_WEIGHTS)))
        assert ws >= 80.0, f"Weighted score {ws:.1f} below 80 target"

    def test_winning_score_target(self, perfect_bank_fraud_output, perfect_upi_fraud_output, perfect_phishing_output, good_agent_responses):
        """To win, we need weighted score ≥ 90."""
        scores = []
        for output, fake_data in [
            (perfect_bank_fraud_output, BANK_FRAUD_SCENARIO["fakeData"]),
            (perfect_upi_fraud_output, UPI_FRAUD_SCENARIO["fakeData"]),
            (perfect_phishing_output, PHISHING_SCENARIO["fakeData"]),
        ]:
            b = score_scenario(
                final_output=output,
                fake_data=fake_data,
                agent_responses=good_agent_responses,
                turn_count=10,
            )
            scores.append(b)

        ws = weighted_final_score(list(zip(scores, STANDARD_WEIGHTS)))
        assert ws >= 90.0, f"Weighted score {ws:.1f} below 90 winning target"
