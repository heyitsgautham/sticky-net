"""Checks that the local scoring helpers reproduce the GUVI rubric exactly."""

from scoring_helpers import (
    BANK_FRAUD_SCENARIO,
    PHISHING_SCENARIO,
    UPI_FRAUD_SCENARIO,
    score_engagement_quality,
    score_intelligence_extraction,
    score_response_structure,
    score_scam_detection,
    weighted_final_score,
)

# ============================================================================
# EVALUATOR SCORING ENGINE SELF-TESTS
# ============================================================================


class TestScoringEngineAccuracy:
    """Verify our scoring engine matches the GUVI evaluator exactly."""

    # -- Scam Detection (20 pts) --

    def test_scam_detected_true_gives_20(self):
        assert score_scam_detection({"scamDetected": True}) == 20

    def test_scam_detected_false_gives_0(self):
        assert score_scam_detection({"scamDetected": False}) == 0

    def test_scam_detected_missing_gives_0(self):
        assert score_scam_detection({}) == 0

    # -- Intelligence Extraction (40 pts) --

    def test_intel_all_3_bank_fraud_items_gives_30(self):
        output = {
            "extractedIntelligence": {
                "bankAccounts": ["1234567890123456"],
                "upiIds": ["scammer.fraud@fakebank"],
                "phoneNumbers": ["+91-9876543210"],
            }
        }
        score = score_intelligence_extraction(output, BANK_FRAUD_SCENARIO["fakeData"])
        assert score == 30

    def test_intel_partial_bank_fraud_gives_partial_score(self):
        """Only phone extracted → 10 pts."""
        output = {
            "extractedIntelligence": {
                "phoneNumbers": ["+91-9876543210"],
                "bankAccounts": [],
                "upiIds": [],
            }
        }
        score = score_intelligence_extraction(output, BANK_FRAUD_SCENARIO["fakeData"])
        assert score == 10

    def test_intel_none_extracted_gives_0(self):
        output = {"extractedIntelligence": {}}
        score = score_intelligence_extraction(output, BANK_FRAUD_SCENARIO["fakeData"])
        assert score == 0

    def test_intel_max_is_40(self):
        """Even with 5 fakeData items (future scenario), max is 40."""
        fake_data = {
            "bankAccount": "123",
            "upiId": "a@b",
            "phoneNumber": "999",
            "phishingLink": "http://x",
            "emailAddress": "x@y",
        }
        output = {
            "extractedIntelligence": {
                "bankAccounts": ["123"],
                "upiIds": ["a@b"],
                "phoneNumbers": ["999"],
                "phishingLinks": ["http://x"],
                "emailAddresses": ["x@y"],
            }
        }
        score = score_intelligence_extraction(output, fake_data)
        assert score == 40  # 5×10=50, capped at 40

    def test_intel_phishing_with_email(self):
        """Phishing scenario: phishingLink + emailAddress = 20 pts."""
        output = {
            "extractedIntelligence": {
                "phishingLinks": ["http://amaz0n-deals.fake-site.com/claim?id=12345"],
                "emailAddresses": ["offers@fake-amazon-deals.com"],
            }
        }
        score = score_intelligence_extraction(output, PHISHING_SCENARIO["fakeData"])
        assert score == 20

    def test_intel_phishing_without_email_gives_10(self):
        """Phishing scenario: only link extracted → 10 pts (missing email = -10)."""
        output = {
            "extractedIntelligence": {
                "phishingLinks": ["http://amaz0n-deals.fake-site.com/claim?id=12345"],
            }
        }
        score = score_intelligence_extraction(output, PHISHING_SCENARIO["fakeData"])
        assert score == 10

    def test_intel_upi_fraud_2_items_gives_20(self):
        """UPI fraud: upiId + phoneNumber = 20 pts."""
        output = {
            "extractedIntelligence": {
                "upiIds": ["cashback.scam@fakeupi"],
                "phoneNumbers": ["+91-8765432109"],
            }
        }
        score = score_intelligence_extraction(output, UPI_FRAUD_SCENARIO["fakeData"])
        assert score == 20

    def test_intel_substring_match_works(self):
        """Evaluator uses 'any(fake_value in str(v))' — substring match."""
        fake_data = {"phoneNumber": "+91-9876543210"}
        output = {
            "extractedIntelligence": {
                # Stored without +91- prefix
                "phoneNumbers": ["9876543210"],
            }
        }
        # "+91-9876543210" in "9876543210" → False (longer string not in shorter)
        # But "9876543210" may match via substring
        score = score_intelligence_extraction(output, fake_data)
        # This actually FAILS because "+91-9876543210" is not IN "9876543210"
        # The fake_value "+91-9876543210" is checked against each extracted value
        assert score == 0, (
            "Substring match is one-directional: fake_value in str(extracted). "
            "Must store phone numbers in same format as fakeData for match."
        )

    def test_intel_match_requires_fakedata_format(self):
        """
        CRITICAL: Evaluator checks if fake_value is substring of extracted value.
        If fakeData has '+91-9876543210', we must store it with +91- prefix!
        """
        fake_data = {"phoneNumber": "+91-9876543210"}

        # Store in same format as fakeData
        output_correct = {
            "extractedIntelligence": {
                "phoneNumbers": ["+91-9876543210"],
            }
        }
        assert score_intelligence_extraction(output_correct, fake_data) == 10

        # Also works if extracted value CONTAINS the fake value
        output_superset = {
            "extractedIntelligence": {
                "phoneNumbers": ["Call +91-9876543210 now"],
            }
        }
        assert score_intelligence_extraction(output_superset, fake_data) == 10

    # -- Engagement Quality (20 pts) --

    def test_engagement_full_marks(self):
        output = {
            "engagementMetrics": {
                "engagementDurationSeconds": 120,
                "totalMessagesExchanged": 10,
            }
        }
        assert score_engagement_quality(output) == 20

    def test_engagement_duration_zero_loses_10(self):
        output = {
            "engagementMetrics": {
                "engagementDurationSeconds": 0,
                "totalMessagesExchanged": 10,
            }
        }
        score = score_engagement_quality(output)
        assert score == 10, "duration=0 loses both duration checks (-10)"

    def test_engagement_duration_30_gets_5(self):
        """Duration > 0 but <= 60 → only first check passes (+5)."""
        output = {
            "engagementMetrics": {
                "engagementDurationSeconds": 30,
                "totalMessagesExchanged": 1,
            }
        }
        score = score_engagement_quality(output)
        # duration>0 → +5, duration<=60 → 0, messages>0 → +5, messages<5 → 0
        assert score == 10

    def test_engagement_no_metrics_gives_0(self):
        """Missing engagementMetrics → 0 pts."""
        output = {}
        assert score_engagement_quality(output) == 0

    def test_engagement_messages_less_than_5(self):
        """Messages < 5 → only first check passes."""
        output = {
            "engagementMetrics": {
                "engagementDurationSeconds": 0,
                "totalMessagesExchanged": 3,
            }
        }
        score = score_engagement_quality(output)
        assert score == 5  # messages>0 only

    # -- Response Structure (20 pts) --

    def test_structure_full_marks(self):
        output = {
            "status": "success",
            "scamDetected": True,
            "extractedIntelligence": {"bankAccounts": []},
            "engagementMetrics": {"engagementDurationSeconds": 1},
            "agentNotes": "Some notes",
        }
        assert score_response_structure(output) == 20.0

    def test_structure_missing_status_loses_5(self):
        output = {
            "scamDetected": True,
            "extractedIntelligence": {},
            "engagementMetrics": {"engagementDurationSeconds": 1},
            "agentNotes": "Notes",
        }
        score = score_response_structure(output)
        assert score == 15.0

    def test_structure_missing_engagement_metrics_loses_2_5(self):
        output = {
            "status": "success",
            "scamDetected": True,
            "extractedIntelligence": {},
            "agentNotes": "Notes",
        }
        score = score_response_structure(output)
        assert score == 17.5

    def test_structure_empty_agent_notes_loses_2_5(self):
        output = {
            "status": "success",
            "scamDetected": True,
            "extractedIntelligence": {},
            "engagementMetrics": {"engagementDurationSeconds": 1},
            "agentNotes": "",  # empty string is falsy
        }
        score = score_response_structure(output)
        assert score == 17.5

    def test_structure_only_scam_detected_gives_5(self):
        output = {"scamDetected": True}
        assert score_response_structure(output) == 5.0

    # -- Weighted Final Score --

    def test_weighted_score_calculation(self):
        """Example from EVAL_SYS.md: bank_fraud 85, upi_fraud 90, phishing 75."""
        scores = [
            {"total": 85},
            {"total": 90},
            {"total": 75},
        ]
        weights = [0.35, 0.35, 0.30]
        final = weighted_final_score(scores, weights)
        expected = 85 * 0.35 + 90 * 0.35 + 75 * 0.30  # 29.75 + 31.5 + 22.5 = 83.75
        assert abs(final - expected) < 0.01

    def test_all_perfect_gives_100(self):
        """If every scenario scores 100/100, weighted final = 100."""
        scores = [{"total": 100}] * 3
        weights = [0.35, 0.35, 0.30]
        final = weighted_final_score(scores, weights)
        assert abs(final - 100.0) < 0.01
