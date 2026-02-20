"""
Unit tests for the GUVI scoring engine — validates the scoring logic itself.

These tests do NOT call the API. They test the scoring functions directly
to ensure our local scoring engine matches GUVI's evaluation exactly.
"""

import pytest

from guvi_scoring_engine import (
    FAKE_DATA_KEY_MAPPING,
    ScoreBreakdown,
    score_engagement_quality,
    score_intelligence_extraction,
    score_response_structure,
    score_scam_detection,
    score_scenario,
    weighted_final_score,
)


# ======================================================================
# Scam Detection (20 pts)
# ======================================================================
class TestScamDetection:
    """Tests for score_scam_detection — 20 pts if scamDetected=True."""

    def test_scam_detected_true(self):
        assert score_scam_detection({"scamDetected": True}) == 20.0

    def test_scam_detected_false(self):
        assert score_scam_detection({"scamDetected": False}) == 0.0

    def test_scam_detected_missing(self):
        assert score_scam_detection({}) == 0.0

    def test_scam_detected_none(self):
        assert score_scam_detection({"scamDetected": None}) == 0.0

    def test_scam_detected_string_true(self):
        # GUVI uses Python truthiness — "true" string is truthy
        assert score_scam_detection({"scamDetected": "true"}) == 20.0

    def test_scam_detected_zero(self):
        assert score_scam_detection({"scamDetected": 0}) == 0.0

    def test_scam_detected_one(self):
        assert score_scam_detection({"scamDetected": 1}) == 20.0

    def test_issues_tracked_when_false(self):
        bd = ScoreBreakdown()
        score_scam_detection({"scamDetected": False}, breakdown=bd)
        assert len(bd.issues) == 1
        assert "scamDetected" in bd.issues[0]


# ======================================================================
# Intelligence Extraction (40 pts)
# ======================================================================
class TestIntelligenceExtraction:
    """Tests for score_intelligence_extraction — 10 pts per fakeData match."""

    def test_all_three_extracted(self):
        fake_data = {
            "bankAccount": "1234567890123456",
            "upiId": "scammer@fakebank",
            "phoneNumber": "+91-9876543210",
        }
        final = {
            "extractedIntelligence": {
                "bankAccounts": ["1234567890123456"],
                "upiIds": ["scammer@fakebank"],
                "phoneNumbers": ["+91-9876543210"],
            }
        }
        assert score_intelligence_extraction(final, fake_data) == 30.0

    def test_none_extracted(self):
        fake_data = {"bankAccount": "1234567890123456"}
        final = {"extractedIntelligence": {"bankAccounts": []}}
        assert score_intelligence_extraction(final, fake_data) == 0.0

    def test_partial_extraction(self):
        fake_data = {
            "bankAccount": "1234567890123456",
            "upiId": "scammer@fakebank",
        }
        final = {
            "extractedIntelligence": {
                "bankAccounts": ["1234567890123456"],
                "upiIds": [],
            }
        }
        assert score_intelligence_extraction(final, fake_data) == 10.0

    def test_capped_at_40(self):
        """Even with 5 fakeData items, max is 40 pts."""
        fake_data = {
            "bankAccount": "1111",
            "upiId": "a@b",
            "phoneNumber": "1234",
            "phishingLink": "http://x",
            "emailAddress": "e@e",
        }
        final = {
            "extractedIntelligence": {
                "bankAccounts": ["1111"],
                "upiIds": ["a@b"],
                "phoneNumbers": ["1234"],
                "phishingLinks": ["http://x"],
                "emailAddresses": ["e@e"],
            }
        }
        assert score_intelligence_extraction(final, fake_data) == 40.0

    def test_substring_match(self):
        """GUVI uses `fake_value in str(v)` — substring match."""
        fake_data = {"phoneNumber": "9876543210"}
        final = {
            "extractedIntelligence": {
                "phoneNumbers": ["+91-9876543210"],  # contains "9876543210"
            }
        }
        assert score_intelligence_extraction(final, fake_data) == 10.0

    def test_substring_match_direction(self):
        """Match direction: fake_value IN extracted_value (not reverse)."""
        fake_data = {"phoneNumber": "+91-9876543210"}
        final = {
            "extractedIntelligence": {
                "phoneNumbers": ["9876543210"],  # does NOT contain "+91-"
            }
        }
        # "+91-9876543210" NOT IN "9876543210" → 0 pts
        assert score_intelligence_extraction(final, fake_data) == 0.0

    def test_key_mapping_bank(self):
        assert FAKE_DATA_KEY_MAPPING["bankAccount"] == "bankAccounts"

    def test_key_mapping_upi(self):
        assert FAKE_DATA_KEY_MAPPING["upiId"] == "upiIds"

    def test_key_mapping_phone(self):
        assert FAKE_DATA_KEY_MAPPING["phoneNumber"] == "phoneNumbers"

    def test_key_mapping_link(self):
        assert FAKE_DATA_KEY_MAPPING["phishingLink"] == "phishingLinks"

    def test_key_mapping_email(self):
        assert FAKE_DATA_KEY_MAPPING["emailAddress"] == "emailAddresses"

    def test_missing_intelligence_key(self):
        """If extractedIntelligence is completely missing, score 0."""
        assert score_intelligence_extraction({}, {"bankAccount": "123"}) == 0.0

    def test_string_value_match(self):
        """If extracted value is a string rather than list."""
        fake_data = {"upiId": "test@upi"}
        final = {
            "extractedIntelligence": {
                "upiIds": "test@upi",  # string, not list
            }
        }
        assert score_intelligence_extraction(final, fake_data) == 10.0

    def test_multiple_values_one_match(self):
        """One of multiple extracted values matches."""
        fake_data = {"bankAccount": "1234567890"}
        final = {
            "extractedIntelligence": {
                "bankAccounts": ["9999999999", "1234567890", "5555555555"],
            }
        }
        assert score_intelligence_extraction(final, fake_data) == 10.0

    def test_issues_tracked_on_miss(self):
        bd = ScoreBreakdown()
        fake_data = {"bankAccount": "123", "upiId": "x@y"}
        final = {"extractedIntelligence": {"bankAccounts": ["456"], "upiIds": []}}
        score_intelligence_extraction(final, fake_data, breakdown=bd)
        assert len(bd.issues) == 2

    def test_empty_fake_data(self):
        """No fakeData → 0 pts (non-scam scenario)."""
        assert score_intelligence_extraction({"extractedIntelligence": {}}, {}) == 0.0


# ======================================================================
# Engagement Quality (20 pts)
# ======================================================================
class TestEngagementQuality:
    """Tests for score_engagement_quality."""

    def test_perfect_engagement(self):
        final = {
            "engagementMetrics": {
                "engagementDurationSeconds": 120,
                "totalMessagesExchanged": 10,
            }
        }
        assert score_engagement_quality(final) == 20.0

    def test_zero_engagement(self):
        assert score_engagement_quality({}) == 0.0

    def test_duration_only_small(self):
        final = {
            "engagementMetrics": {
                "engagementDurationSeconds": 30,
                "totalMessagesExchanged": 0,
            }
        }
        assert score_engagement_quality(final) == 5.0  # duration > 0 only

    def test_duration_over_60(self):
        final = {
            "engagementMetrics": {
                "engagementDurationSeconds": 61,
                "totalMessagesExchanged": 0,
            }
        }
        assert score_engagement_quality(final) == 10.0  # >0 and >60

    def test_messages_under_5(self):
        final = {
            "engagementMetrics": {
                "engagementDurationSeconds": 0,
                "totalMessagesExchanged": 3,
            }
        }
        assert score_engagement_quality(final) == 5.0  # messages > 0 only

    def test_messages_exactly_5(self):
        final = {
            "engagementMetrics": {
                "engagementDurationSeconds": 0,
                "totalMessagesExchanged": 5,
            }
        }
        assert score_engagement_quality(final) == 10.0  # >0 and >=5

    def test_duration_exactly_60(self):
        """Boundary: duration=60 → only >0 bonus, NOT >60 bonus."""
        final = {
            "engagementMetrics": {
                "engagementDurationSeconds": 60,
                "totalMessagesExchanged": 0,
            }
        }
        assert score_engagement_quality(final) == 5.0

    def test_all_issues_tracked(self):
        bd = ScoreBreakdown()
        score_engagement_quality({}, breakdown=bd)
        assert len(bd.issues) == 4  # all 4 conditions fail


# ======================================================================
# Response Structure (20 pts)
# ======================================================================
class TestResponseStructure:
    """Tests for score_response_structure."""

    def test_perfect_structure(self):
        final = {
            "status": "success",
            "scamDetected": True,
            "extractedIntelligence": {"bankAccounts": []},
            "engagementMetrics": {"engagementDurationSeconds": 10},
            "agentNotes": "Some notes",
        }
        assert score_response_structure(final) == 20.0

    def test_required_only(self):
        final = {
            "status": "success",
            "scamDetected": True,
            "extractedIntelligence": {},
        }
        assert score_response_structure(final) == 15.0

    def test_missing_all(self):
        assert score_response_structure({}) == 0.0

    def test_optional_empty_string(self):
        """Empty agentNotes → no bonus (falsy)."""
        final = {
            "status": "success",
            "scamDetected": True,
            "extractedIntelligence": {},
            "agentNotes": "",
        }
        assert score_response_structure(final) == 15.0

    def test_optional_none(self):
        """None agentNotes → no bonus."""
        final = {
            "status": "success",
            "scamDetected": True,
            "extractedIntelligence": {},
            "agentNotes": None,
        }
        assert score_response_structure(final) == 15.0

    def test_engagement_metrics_present(self):
        final = {
            "status": "success",
            "scamDetected": True,
            "extractedIntelligence": {},
            "engagementMetrics": {"engagementDurationSeconds": 100},
        }
        assert score_response_structure(final) == 17.5

    def test_issues_tracked(self):
        bd = ScoreBreakdown()
        score_response_structure({}, breakdown=bd)
        assert len(bd.issues) == 5  # 3 required + 2 optional


# ======================================================================
# Full Scenario Scoring
# ======================================================================
class TestScenarioScoring:
    """Tests for score_scenario — full 100-point evaluation."""

    def test_perfect_score(self):
        """All conditions met → 100/100."""
        final = {
            "status": "success",
            "scamDetected": True,
            "extractedIntelligence": {
                "bankAccounts": ["1234567890123456"],
                "upiIds": ["scammer@fakebank"],
                "phoneNumbers": ["+91-9876543210"],
                "phishingLinks": ["http://malicious.example.com"],
            },
            "engagementMetrics": {
                "engagementDurationSeconds": 120,
                "totalMessagesExchanged": 10,
            },
            "agentNotes": "Scammer used urgency tactics",
        }
        fake_data = {
            "bankAccount": "1234567890123456",
            "upiId": "scammer@fakebank",
            "phoneNumber": "+91-9876543210",
            "phishingLink": "http://malicious.example.com",
        }
        bd = score_scenario(final, fake_data, "test_perfect")
        assert bd.total == 100.0
        assert len(bd.issues) == 0

    def test_zero_score(self):
        """Nothing correct → 0/100."""
        bd = score_scenario({}, {}, "test_zero")
        assert bd.total == 0.0

    def test_detection_only(self):
        """Scam detected but nothing else → 20/100."""
        final = {"scamDetected": True}
        bd = score_scenario(final, {}, "test_detection")
        assert bd.scam_detection == 20.0
        assert bd.intelligence_extraction == 0.0

    def test_score_breakdown_summary(self):
        """ScoreBreakdown.summary() returns formatted string."""
        bd = ScoreBreakdown(scenario_id="test", scam_detection=20, issues=["issue1"])
        summary = bd.summary()
        assert "test" in summary
        assert "issue1" in summary

    def test_realistic_bank_fraud(self):
        """Realistic bank fraud scenario with partial extraction."""
        final = {
            "status": "success",
            "scamDetected": True,
            "extractedIntelligence": {
                "bankAccounts": ["1234567890123456"],
                "upiIds": [],
                "phoneNumbers": ["+91-9876543210"],
            },
            "engagementMetrics": {
                "engagementDurationSeconds": 90,
                "totalMessagesExchanged": 8,
            },
            "agentNotes": "Detected banking fraud",
        }
        fake_data = {
            "bankAccount": "1234567890123456",
            "upiId": "scammer@fakebank",
            "phoneNumber": "+91-9876543210",
        }
        bd = score_scenario(final, fake_data, "realistic_bank")
        assert bd.scam_detection == 20.0
        assert bd.intelligence_extraction == 20.0  # 2 of 3 matched
        assert bd.engagement_quality == 20.0  # all conditions met
        assert bd.response_structure == 20.0  # all fields present
        assert bd.total == 80.0

    def test_phishing_with_email_mapping(self):
        """Verify emailAddress → emailAddresses mapping works."""
        final = {
            "status": "success",
            "scamDetected": True,
            "extractedIntelligence": {
                "phishingLinks": ["http://fake.com"],
                "emailAddresses": ["test@fake.com"],
            },
            "engagementMetrics": {
                "engagementDurationSeconds": 120,
                "totalMessagesExchanged": 6,
            },
            "agentNotes": "Phishing detected",
        }
        fake_data = {
            "phishingLink": "http://fake.com",
            "emailAddress": "test@fake.com",
        }
        bd = score_scenario(final, fake_data, "phishing")
        assert bd.intelligence_extraction == 20.0


# ======================================================================
# Weighted Final Score
# ======================================================================
class TestWeightedScoring:
    """Tests for weighted_final_score across scenarios."""

    def test_equal_weights(self):
        bd1 = ScoreBreakdown(scam_detection=20, intelligence_extraction=40,
                             engagement_quality=20, response_structure=20)
        bd2 = ScoreBreakdown(scam_detection=20, intelligence_extraction=20,
                             engagement_quality=20, response_structure=20)
        result = weighted_final_score([bd1, bd2], [0.5, 0.5])
        assert result == 90.0

    def test_skewed_weights(self):
        bd1 = ScoreBreakdown(scam_detection=20, intelligence_extraction=40,
                             engagement_quality=20, response_structure=20)
        bd2 = ScoreBreakdown(scam_detection=0)
        result = weighted_final_score([bd1, bd2], [0.9, 0.1])
        assert result == pytest.approx(90.0)

    def test_three_scenarios_guvi_weights(self):
        """Replicate GUVI 35/35/30 weighting."""
        bd1 = ScoreBreakdown(scam_detection=20, intelligence_extraction=30,
                             engagement_quality=20, response_structure=20)  # 90
        bd2 = ScoreBreakdown(scam_detection=20, intelligence_extraction=40,
                             engagement_quality=20, response_structure=20)  # 100
        bd3 = ScoreBreakdown(scam_detection=20, intelligence_extraction=20,
                             engagement_quality=15, response_structure=20)  # 75
        result = weighted_final_score([bd1, bd2, bd3], [0.35, 0.35, 0.30])
        expected = 90 * 0.35 + 100 * 0.35 + 75 * 0.30
        assert result == pytest.approx(expected)

    def test_single_scenario(self):
        bd = ScoreBreakdown(scam_detection=20, intelligence_extraction=30,
                            engagement_quality=15, response_structure=17.5)
        result = weighted_final_score([bd], [1.0])
        assert result == pytest.approx(82.5)

    def test_mismatched_lengths_raises(self):
        with pytest.raises(AssertionError):
            weighted_final_score(
                [ScoreBreakdown(), ScoreBreakdown()],
                [0.5],
            )
