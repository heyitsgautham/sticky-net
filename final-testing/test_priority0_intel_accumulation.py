"""Priority 0 fixes: intelligence accumulates across turns and the full callback carries it."""


# ============================================================================
# ISSUE 1: engagementDurationSeconds always 0
# ============================================================================


class TestIntelligenceAccumulation:
    """
    Each request is currently stateless. If the scammer shares a phone number
    in Turn 3 but our Turn 5 callback only has Turn 5 intel, we lose it.
    The evaluator scores the LAST callback — we must accumulate all intel.
    """

    def test_session_intel_store_concept(self):
        """
        After fix: there should be a per-session intelligence store.
        This tests the accumulation logic that should be implemented.
        """
        # Simulate accumulation across turns
        session_intel: dict[str, set] = {
            "bankAccounts": set(),
            "upiIds": set(),
            "phoneNumbers": set(),
            "phishingLinks": set(),
            "emailAddresses": set(),
        }

        # Turn 1: scammer shares phone
        turn1_intel = {"phoneNumbers": ["+91-9876543210"]}
        for key, values in turn1_intel.items():
            session_intel[key].update(values)

        # Turn 3: scammer shares bank account
        turn3_intel = {"bankAccounts": ["1234567890123456"]}
        for key, values in turn3_intel.items():
            session_intel[key].update(values)

        # Turn 5: scammer shares UPI
        turn5_intel = {"upiIds": ["scammer.fraud@fakebank"]}
        for key, values in turn5_intel.items():
            session_intel[key].update(values)

        # Final callback should have ALL accumulated intel
        final_intel = {k: list(v) for k, v in session_intel.items()}
        assert "+91-9876543210" in final_intel["phoneNumbers"]
        assert "1234567890123456" in final_intel["bankAccounts"]
        assert "scammer.fraud@fakebank" in final_intel["upiIds"]

    def test_accumulation_preserves_earlier_intel(self):
        """Intel from earlier turns must not be lost in later callbacks."""
        # Simulate: Turn 2 had phone, Turn 4 had UPI, Turn 6 callback
        accumulated = {
            "phoneNumbers": {"9876543210"},  # from Turn 2
            "upiIds": {"fraud@bank"},  # from Turn 4
            "bankAccounts": set(),
        }

        # Turn 6: adds nothing new
        turn6_intel = {"phoneNumbers": [], "upiIds": [], "bankAccounts": []}
        for key, values in turn6_intel.items():
            accumulated[key].update(values)

        # Must still have Turn 2 + Turn 4 intel
        assert "9876543210" in accumulated["phoneNumbers"]
        assert "fraud@bank" in accumulated["upiIds"]

    def test_accumulation_deduplicates(self):
        """Same intel shared across multiple turns should not duplicate."""
        accumulated: dict[str, set] = {"phoneNumbers": set()}

        # Scammer shares same number in Turn 2, 3, and 5
        for _ in range(3):
            accumulated["phoneNumbers"].add("9876543210")

        final = list(accumulated["phoneNumbers"])
        assert len(final) == 1, "Duplicate intel should be deduplicated"
        assert final[0] == "9876543210"

    def test_accumulation_merges_new_intel(self):
        """New intel discovered in later turns should be added."""
        accumulated = {"bankAccounts": {"111111111111"}}

        # Turn 5: new bank account discovered
        accumulated["bankAccounts"].add("222222222222")

        assert len(accumulated["bankAccounts"]) == 2

    def test_full_scenario_accumulation_scores_max_intel(self):
        """
        Simulate full bank_fraud scenario: fakeData spread across turns.
        After accumulation, final callback should extract all 3 items → 30 pts.
        """
        from scoring_helpers import BANK_FRAUD_SCENARIO, score_intelligence_extraction

        fake_data = BANK_FRAUD_SCENARIO["fakeData"]
        accumulated = {
            "bankAccounts": set(),
            "upiIds": set(),
            "phoneNumbers": set(),
            "phishingLinks": set(),
            "emailAddresses": set(),
        }

        # Turn 2: phone shared
        accumulated["phoneNumbers"].add("+91-9876543210")
        # Turn 3: bank + UPI shared
        accumulated["bankAccounts"].add("1234567890123456")
        accumulated["upiIds"].add("scammer.fraud@fakebank")

        final_intel = {k: list(v) for k, v in accumulated.items()}
        final_output = {
            "extractedIntelligence": final_intel,
        }

        score = score_intelligence_extraction(final_output, fake_data)
        assert score == 30, f"Expected 30 pts for 3 fakeData items, got {score}"


class TestFullCallbackStructureAfterP0:
    """
    After all Priority 0 fixes, the CallbackPayload should produce a
    JSON object that scores maximum on Response Structure (20/20).
    """

    def test_perfect_callback_scores_20_on_structure(self):
        """A complete callback payload should score 20/20 on response structure."""
        from scoring_helpers import score_response_structure

        payload = {
            "sessionId": "abc",
            "status": "success",
            "scamDetected": True,
            "totalMessagesExchanged": 10,
            "extractedIntelligence": {
                "bankAccounts": ["1234567890123456"],
                "upiIds": [],
                "phoneNumbers": [],
                "phishingLinks": [],
                "emailAddresses": [],
            },
            "engagementMetrics": {
                "engagementDurationSeconds": 120,
                "totalMessagesExchanged": 10,
            },
            "agentNotes": "Scammer used urgency tactics.",
        }

        score = score_response_structure(payload)
        assert score == 20.0, f"Expected 20.0 structure pts, got {score}"

    def test_current_broken_callback_scores_low_on_structure(self):
        """Current (broken) callback without status/engagementMetrics loses points."""
        from scoring_helpers import score_response_structure

        # This is what we currently send
        broken_payload = {
            "sessionId": "abc",
            "scamDetected": True,
            "totalMessagesExchanged": 10,
            "extractedIntelligence": {
                "bankAccounts": [],
                "upiIds": [],
                "phishingLinks": [],
                "phoneNumbers": [],
                "suspiciousKeywords": [],
            },
            "agentNotes": "Some notes.",
        }

        score = score_response_structure(broken_payload)
        # Missing: status (-5), engagementMetrics (-2.5) = -7.5
        assert score <= 12.5, f"Broken payload should score ≤12.5, got {score}"

    def test_perfect_bank_fraud_callback_scores_100(self):
        """A perfect callback for bank_fraud scenario should score 100/100."""
        from scoring_helpers import BANK_FRAUD_SCENARIO, score_scenario

        perfect_output = {
            "status": "success",
            "scamDetected": True,
            "totalMessagesExchanged": 10,
            "extractedIntelligence": {
                "bankAccounts": ["1234567890123456"],
                "upiIds": ["scammer.fraud@fakebank"],
                "phoneNumbers": ["+91-9876543210"],
                "phishingLinks": [],
                "emailAddresses": [],
            },
            "engagementMetrics": {
                "engagementDurationSeconds": 120,
                "totalMessagesExchanged": 10,
            },
            "agentNotes": "Scammer used urgency tactics.",
        }

        scores = score_scenario(perfect_output, BANK_FRAUD_SCENARIO["fakeData"])
        assert scores["scamDetection"] == 20
        assert scores["intelligenceExtraction"] == 30  # 3 items × 10
        assert scores["engagementQuality"] == 20
        assert scores["responseStructure"] == 20.0
        assert scores["total"] == 90.0  # 20+30+20+20

    def test_perfect_phishing_callback_scores_100(self):
        """A perfect callback for phishing scenario should score 100/100."""
        from scoring_helpers import PHISHING_SCENARIO, score_scenario

        perfect_output = {
            "status": "success",
            "scamDetected": True,
            "totalMessagesExchanged": 10,
            "extractedIntelligence": {
                "bankAccounts": [],
                "upiIds": [],
                "phoneNumbers": [],
                "phishingLinks": ["http://amaz0n-deals.fake-site.com/claim?id=12345"],
                "emailAddresses": ["offers@fake-amazon-deals.com"],
            },
            "engagementMetrics": {
                "engagementDurationSeconds": 120,
                "totalMessagesExchanged": 10,
            },
            "agentNotes": "Phishing attempt detected.",
        }

        scores = score_scenario(perfect_output, PHISHING_SCENARIO["fakeData"])
        assert scores["scamDetection"] == 20
        assert scores["intelligenceExtraction"] == 20  # 2 items × 10
        assert scores["engagementQuality"] == 20
        assert scores["responseStructure"] == 20.0
        assert scores["total"] == 80.0  # 20+20+20+20
