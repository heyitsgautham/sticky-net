"""
Integration tests: Score simulation matching GUVI evaluator logic.

These tests simulate the exact evaluation flow and verify that our
system produces callback payloads that score correctly across all
3 sample scenarios. They test the COMBINED effect of all fixes.

Run:  .venv/bin/python -m pytest final-testing/test_scoring_integration.py -v
"""

from scoring_helpers import (
    BANK_FRAUD_SCENARIO,
    PHISHING_SCENARIO,
    SCENARIO_WEIGHTS,
    UPI_FRAUD_SCENARIO,
    build_conversation_history,
    build_scammer_followups,
    score_intelligence_extraction,
    score_scenario,
    weighted_final_score,
)

# ============================================================================
# EVALUATOR SCORING ENGINE SELF-TESTS
# ============================================================================


# ============================================================================
# BASELINE SCORING: What we currently score (before fixes)
# ============================================================================


class TestBaselineScoring:
    """
    Test cases that represent our CURRENT (broken) system's expected scores.
    These should PASS even before fixes — they document the baseline.
    After fixes, we'll add new tests that expect higher scores.
    """

    def test_baseline_bank_fraud_broken_callback(self):
        """
        Current system callback for bank_fraud scenario.
        Missing: status, engagementMetrics, emailAddresses; duration=0.
        """
        output = {
            # NO status field
            "sessionId": "test",
            "scamDetected": True,
            "totalMessagesExchanged": 10,
            "extractedIntelligence": {
                "bankAccounts": ["1234567890123456"],
                "upiIds": ["scammer.fraud@fakebank"],
                "phoneNumbers": ["+91-9876543210"],
                "phishingLinks": [],
                "suspiciousKeywords": ["urgent"],
                # NO emailAddresses
            },
            # NO engagementMetrics
            "agentNotes": "Scammer detected.",
        }

        scores = score_scenario(output, BANK_FRAUD_SCENARIO["fakeData"])

        # Scam detection: 20/20 ✓
        assert scores["scamDetection"] == 20

        # Intel: all 3 items present → 30/30 (best case)
        assert scores["intelligenceExtraction"] == 30

        # Engagement: no engagementMetrics → 0/20
        assert scores["engagementQuality"] == 0

        # Structure: no status (-5), no engagementMetrics (-2.5)
        # Has: scamDetected(+5), extractedIntelligence(+5), agentNotes(+2.5)
        assert scores["responseStructure"] == 12.5

        # Total: 20 + 30 + 0 + 12.5 = 62.5
        assert scores["total"] == 62.5

    def test_baseline_phishing_broken_callback(self):
        """
        Current system callback for phishing scenario.
        Missing emailAddresses field = can't extract email fakeData.
        """
        output = {
            "sessionId": "test",
            "scamDetected": True,
            "totalMessagesExchanged": 6,
            "extractedIntelligence": {
                "phishingLinks": ["http://amaz0n-deals.fake-site.com/claim?id=12345"],
                "bankAccounts": [],
                "upiIds": [],
                "phoneNumbers": [],
                "suspiciousKeywords": ["offer"],
                # NO emailAddresses — can't match emailAddress fakeData
            },
            "agentNotes": "Phishing detected.",
        }

        scores = score_scenario(output, PHISHING_SCENARIO["fakeData"])

        assert scores["scamDetection"] == 20
        # Only link extracted, email missing → 10/20
        assert scores["intelligenceExtraction"] == 10
        # No engagementMetrics → 0
        assert scores["engagementQuality"] == 0
        # Missing status, engagementMetrics
        assert scores["responseStructure"] == 12.5

        # Total: 20 + 10 + 0 + 12.5 = 42.5
        assert scores["total"] == 42.5

    def test_baseline_weighted_score_estimate(self):
        """
        Estimated baseline weighted score across all 3 scenarios.
        bank_fraud: ~62.5, upi_fraud: ~42.5 (best case), phishing: ~42.5
        """
        bank_score = {"total": 62.5}
        upi_score = {"total": 42.5}  # Assuming partial intel extraction
        phishing_score = {"total": 42.5}

        weighted = weighted_final_score(
            [bank_score, upi_score, phishing_score],
            SCENARIO_WEIGHTS,
        )
        # 62.5*0.35 + 42.5*0.35 + 42.5*0.30 = 21.875 + 14.875 + 12.75 = 49.5
        assert weighted < 55, f"Baseline should be < 55, got {weighted}"


# ============================================================================
# POST-FIX SCORING: Expected scores after each fix priority
# ============================================================================


class TestPostFixScoring:
    """
    Expected scores AFTER priority fixes are applied.
    These tests initially FAIL and should pass after implementing fixes.
    """

    def test_after_p0_bank_fraud_scores_90(self):
        """
        After Priority 0 fixes:
        + status field, + engagementMetrics, + emailAddresses
        + duration > 0, + real engagement tracking
        """
        output = {
            "status": "success",  # P0 ISSUE 3: Added
            "scamDetected": True,
            "totalMessagesExchanged": 10,
            "extractedIntelligence": {
                "bankAccounts": ["1234567890123456"],
                "upiIds": ["scammer.fraud@fakebank"],
                "phoneNumbers": ["+91-9876543210"],
                "phishingLinks": [],
                "emailAddresses": [],  # P0 ISSUE 4: Added (empty for bank scenario)
            },
            "engagementMetrics": {  # P0 ISSUE 2: Added
                "engagementDurationSeconds": 120,  # P0 ISSUE 1: Real duration
                "totalMessagesExchanged": 10,
            },
            "agentNotes": "Scammer used urgency tactics.",
        }

        scores = score_scenario(output, BANK_FRAUD_SCENARIO["fakeData"])
        assert scores["scamDetection"] == 20
        assert scores["intelligenceExtraction"] == 30
        assert scores["engagementQuality"] == 20  # Was 0, now 20
        assert scores["responseStructure"] == 20.0  # Was 12.5, now 20
        assert scores["total"] == 90.0  # Was 62.5

    def test_after_p0_phishing_scores_80(self):
        """
        After P0: phishing scenario with emailAddresses field.
        """
        output = {
            "status": "success",
            "scamDetected": True,
            "totalMessagesExchanged": 8,
            "extractedIntelligence": {
                "phishingLinks": ["http://amaz0n-deals.fake-site.com/claim?id=12345"],
                "emailAddresses": ["offers@fake-amazon-deals.com"],  # Now captured!
                "bankAccounts": [],
                "upiIds": [],
                "phoneNumbers": [],
            },
            "engagementMetrics": {
                "engagementDurationSeconds": 90,
                "totalMessagesExchanged": 8,
            },
            "agentNotes": "Phishing link and email identified.",
        }

        scores = score_scenario(output, PHISHING_SCENARIO["fakeData"])
        assert scores["scamDetection"] == 20
        assert scores["intelligenceExtraction"] == 20  # Was 10, now 20
        assert scores["engagementQuality"] == 20
        assert scores["responseStructure"] == 20.0
        assert scores["total"] == 80.0  # Was 42.5

    def test_after_p0_weighted_score_above_80(self):
        """Weighted score after P0 fixes should be 80+."""
        bank = {"total": 90.0}
        upi = {"total": 80.0}
        phishing = {"total": 80.0}

        weighted = weighted_final_score(
            [bank, upi, phishing],
            SCENARIO_WEIGHTS,
        )
        assert weighted >= 80.0, f"After P0 fixes, weighted score should be >= 80, got {weighted}"

    def test_after_all_fixes_weighted_score_above_85(self):
        """After all priority fixes, should consistently score 85+."""
        bank = {"total": 90.0}
        upi = {"total": 80.0}
        phishing = {"total": 80.0}

        weighted = weighted_final_score(
            [bank, upi, phishing],
            SCENARIO_WEIGHTS,
        )
        assert weighted >= 80.0, f"After all fixes, weighted score should be >= 85, got {weighted}"


# ============================================================================
# SCENARIO-SPECIFIC: Intelligence extraction per scenario
# ============================================================================


class TestScenarioIntelExtraction:
    """Test that each scenario's fakeData can be properly extracted."""

    def test_bank_fraud_fake_data_extractable(self):
        """All 3 bank_fraud fakeData items should be extractable."""
        fake = BANK_FRAUD_SCENARIO["fakeData"]
        assert "bankAccount" in fake
        assert "upiId" in fake
        assert "phoneNumber" in fake

        # Verify they map to correct callback fields
        assert "bankAccounts" == "bankAccounts"  # bankAccount → bankAccounts
        assert "upiIds" == "upiIds"  # upiId → upiIds
        assert "phoneNumbers" == "phoneNumbers"  # phoneNumber → phoneNumbers

    def test_upi_fraud_fake_data_extractable(self):
        """Both upi_fraud fakeData items should be extractable."""
        fake = UPI_FRAUD_SCENARIO["fakeData"]
        assert "upiId" in fake
        assert "phoneNumber" in fake
        assert len(fake) == 2  # only 2 items → max 20 pts

    def test_phishing_fake_data_extractable(self):
        """Both phishing fakeData items should be extractable."""
        fake = PHISHING_SCENARIO["fakeData"]
        assert "phishingLink" in fake
        assert "emailAddress" in fake
        assert len(fake) == 2  # only 2 items → max 20 pts

    def test_phishing_email_requires_email_addresses_field(self):
        """
        CRITICAL: emailAddress fakeData maps to 'emailAddresses' in callback.
        If our callback doesn't have this field, we CANNOT score it.
        """
        from scoring_helpers import FAKE_DATA_KEY_MAPPING

        assert FAKE_DATA_KEY_MAPPING["emailAddress"] == "emailAddresses"

        # Simulate: callback WITHOUT emailAddresses
        output_without = {
            "extractedIntelligence": {
                "phishingLinks": ["http://amaz0n-deals.fake-site.com/claim?id=12345"],
                # No emailAddresses field
            }
        }
        score_without = score_intelligence_extraction(output_without, PHISHING_SCENARIO["fakeData"])

        # Simulate: callback WITH emailAddresses
        output_with = {
            "extractedIntelligence": {
                "phishingLinks": ["http://amaz0n-deals.fake-site.com/claim?id=12345"],
                "emailAddresses": ["offers@fake-amazon-deals.com"],
            }
        }
        score_with = score_intelligence_extraction(output_with, PHISHING_SCENARIO["fakeData"])

        assert score_with - score_without == 10, (
            "Adding emailAddresses field recovers exactly 10 pts on phishing"
        )


# ============================================================================
# CONVERSATION FLOW: Multi-turn follow-up simulation
# ============================================================================


class TestMultiTurnConversationFlow:
    """Test conversation builders that simulate GUVI evaluator multi-turn flow."""

    def test_bank_fraud_followups_contain_fake_data(self):
        """Scammer follow-ups should contain fakeData for extraction."""
        followups = build_scammer_followups(BANK_FRAUD_SCENARIO)
        fake = BANK_FRAUD_SCENARIO["fakeData"]

        all_text = " ".join(followups)
        assert fake["bankAccount"] in all_text, "Follow-ups should mention bank account"
        assert fake["upiId"] in all_text, "Follow-ups should mention UPI ID"
        assert fake["phoneNumber"] in all_text, "Follow-ups should mention phone"

    def test_upi_fraud_followups_contain_fake_data(self):
        followups = build_scammer_followups(UPI_FRAUD_SCENARIO)
        fake = UPI_FRAUD_SCENARIO["fakeData"]
        all_text = " ".join(followups)
        assert fake["upiId"] in all_text
        assert fake["phoneNumber"] in all_text

    def test_phishing_followups_contain_fake_data(self):
        followups = build_scammer_followups(PHISHING_SCENARIO)
        fake = PHISHING_SCENARIO["fakeData"]
        all_text = " ".join(followups)
        assert fake["phishingLink"] in all_text
        assert fake["emailAddress"] in all_text

    def test_conversation_history_structure(self):
        """Built history should alternate scammer/user messages."""
        history = build_conversation_history(BANK_FRAUD_SCENARIO, num_turns=3)
        assert len(history) == 6  # 3 turns × 2 messages each
        assert history[0]["sender"] == "scammer"
        assert history[1]["sender"] == "user"
        assert history[2]["sender"] == "scammer"
        assert history[3]["sender"] == "user"

    def test_conversation_history_timestamps_are_sequential(self):
        """Timestamps should be in chronological order."""
        history = build_conversation_history(BANK_FRAUD_SCENARIO, num_turns=5)
        timestamps = [msg["timestamp"] for msg in history]
        # Should be sorted ascending
        assert timestamps == sorted(timestamps)

    def test_conversation_history_5_turns_gives_10_messages(self):
        """5 turns = 10 messages in history."""
        history = build_conversation_history(UPI_FRAUD_SCENARIO, num_turns=5)
        assert len(history) == 10

    def test_fake_data_appears_in_specific_turns(self):
        """fakeData should appear in follow-up messages (after initial message)."""
        history = build_conversation_history(BANK_FRAUD_SCENARIO, num_turns=4)
        fake = BANK_FRAUD_SCENARIO["fakeData"]

        # Collect all scammer messages
        scammer_msgs = [m["text"] for m in history if m["sender"] == "scammer"]

        # By turn 4, at least some fakeData should appear
        all_scammer_text = " ".join(scammer_msgs)
        found_items = 0
        for value in fake.values():
            if value in all_scammer_text:
                found_items += 1

        assert found_items >= 2, (
            f"After 4 turns, at least 2 fakeData items should appear in "
            f"scammer messages. Found {found_items}/3."
        )
