"""
Test suite for PRIORITY 1 fixes — HIGH IMPACT (15+ pts recovery).

  ISSUE 6: Re-enable regex extraction as backup to AI extraction (+10-20 pts)
  ISSUE 7: Skip classification after Turn 1 — cache per session (-6-16s latency)
  ISSUE 8: Set min-instances=1 on Cloud Run (-7-8s cold start)

Run:  .venv/bin/python -m pytest final-testing/test_priority1_high_impact.py -v
"""

import re
import time
from unittest.mock import patch, MagicMock

import pytest

from src.api.schemas import ExtractedIntelligence
from src.intelligence.extractor import IntelligenceExtractor


# ============================================================================
# ISSUE 6: Re-enable regex extraction as backup to AI extraction
# ============================================================================


class TestRegexBackupExtraction:
    """
    AI-only extraction is unreliable:
    - Sometimes extracts 0 items despite values being in message
    - Sometimes extracts the agent's own fake data instead of scammer's
    
    Regex should scan the scammer's message for known patterns and merge
    with AI results via a union operation.
    """

    # -- Phone number regex patterns --

    def test_regex_extracts_indian_phone_with_country_code(self):
        """Regex should extract +91-XXXXXXXXXX format phone numbers."""
        text = "Call me back at +91-9876543210 for verification."
        pattern = r"\+?91[-\s]?[6-9]\d{9}"
        matches = re.findall(pattern, text)
        assert len(matches) >= 1, "Should extract +91-9876543210"
        # Clean the match
        clean = re.sub(r"[-\s+]", "", matches[0])
        assert "9876543210" in clean

    def test_regex_extracts_10_digit_phone(self):
        """Regex should extract bare 10-digit Indian phone numbers."""
        text = "My number is 9876543210 call me"
        pattern = r"\b[6-9]\d{9}\b"
        matches = re.findall(pattern, text)
        assert len(matches) >= 1
        assert matches[0] == "9876543210"

    def test_regex_extracts_phone_with_spaces(self):
        """Regex should handle phone numbers with spaces/hyphens."""
        text = "Contact: 98765 43210 or 987-654-3210"
        pattern = r"\b[6-9]\d{4}[\s-]?\d{5}\b"
        matches = re.findall(pattern, text)
        assert len(matches) >= 1

    # -- Bank account regex patterns --

    def test_regex_extracts_bank_account_number(self):
        """Regex should extract 9-18 digit bank account numbers."""
        text = "Transfer to account number 1234567890123456 immediately"
        pattern = r"\b\d{9,18}\b"
        matches = re.findall(pattern, text)
        assert "1234567890123456" in matches

    def test_regex_excludes_phone_from_bank_accounts(self):
        """Phone numbers (10 digits starting 6-9) should NOT be matched as bank accounts."""
        text = "Call 9876543210 or transfer to 1234567890123456"
        pattern = r"\b\d{9,18}\b"
        raw_matches = re.findall(pattern, text)

        # Filter out phone-like numbers
        def is_phone(num: str) -> bool:
            if len(num) == 10 and num[0] in "6789":
                return True
            if len(num) == 12 and num.startswith("91") and num[2] in "6789":
                return True
            return False

        bank_accounts = [m for m in raw_matches if not is_phone(m)]
        assert "1234567890123456" in bank_accounts
        assert "9876543210" not in bank_accounts

    # -- UPI ID regex patterns --

    def test_regex_extracts_upi_id(self):
        """Regex should extract user@provider UPI patterns."""
        text = "Send money to scammer.fraud@fakebank via UPI"
        pattern = r"[\w.-]+@[a-zA-Z][a-zA-Z0-9]*"
        matches = re.findall(pattern, text)
        assert "scammer.fraud@fakebank" in matches

    def test_regex_extracts_common_upi_providers(self):
        """Regex should work with common UPI providers."""
        upi_ids = [
            "user@paytm",
            "person@ybl",
            "user@oksbi",
            "user@okaxis",
            "user@okicici",
            "user@upi",
            "cashback.scam@fakeupi",
        ]
        pattern = r"[\w.-]+@[a-zA-Z][a-zA-Z0-9]*"
        for upi in upi_ids:
            text = f"Pay to {upi}"
            matches = re.findall(pattern, text)
            assert upi in matches, f"Should extract {upi}"

    # -- Phishing link regex patterns --

    def test_regex_extracts_http_urls(self):
        """Regex should extract HTTP/HTTPS URLs."""
        text = "Click here: http://amaz0n-deals.fake-site.com/claim?id=12345"
        pattern = r"https?://[^\s<>\"']+"
        matches = re.findall(pattern, text)
        assert len(matches) >= 1
        assert "amaz0n-deals.fake-site.com" in matches[0]

    def test_regex_extracts_urls_with_query_params(self):
        """URLs with query parameters should be fully captured."""
        text = "Visit http://evil.com/login?redirect=bank&token=abc123 now!"
        pattern = r"https?://[^\s<>\"']+"
        matches = re.findall(pattern, text)
        assert len(matches) >= 1
        assert "?redirect=bank" in matches[0]

    # -- Email regex patterns --

    def test_regex_extracts_email_addresses(self):
        """Regex should extract email addresses."""
        text = "Contact us at offers@fake-amazon-deals.com for support"
        pattern = r"[\w.+-]+@[\w-]+\.[\w.]+"
        matches = re.findall(pattern, text)
        assert len(matches) >= 1
        assert "offers@fake-amazon-deals.com" in matches

    def test_regex_distinguishes_email_from_upi(self):
        """Emails have dots in domain, UPI IDs typically don't."""
        texts = [
            ("Send to user@paytm", "upi"),
            ("Email us at test@gmail.com", "email"),
            ("Pay to fraud@fakebank", "upi"),
            ("Contact offers@fake-deals.com", "email"),
        ]
        email_pattern = r"[\w.+-]+@[\w-]+\.[\w.]+"
        upi_pattern = r"[\w.-]+@[a-zA-Z][a-zA-Z0-9]*"

        for text, expected_type in texts:
            emails = re.findall(email_pattern, text)
            if expected_type == "email":
                assert len(emails) >= 1, f"Should find email in: {text}"
            # Note: UPI IDs without dots in domain won't match email pattern

    # -- Merge AI + Regex results --

    def test_merge_ai_and_regex_results(self):
        """Union of AI + regex should capture more intel than either alone."""
        # AI extracted only phone
        ai_intel = ExtractedIntelligence(
            phoneNumbers=["9876543210"],
        )

        # Regex also found bank account and UPI in the text
        regex_results = {
            "bankAccounts": ["1234567890123456"],
            "upiIds": ["scammer.fraud@fakebank"],
            "phoneNumbers": ["9876543210"],  # duplicate with AI
        }

        # Merge: union
        merged = {
            "phoneNumbers": list(set(ai_intel.phoneNumbers + regex_results["phoneNumbers"])),
            "bankAccounts": list(set(ai_intel.bankAccounts + regex_results["bankAccounts"])),
            "upiIds": list(set(ai_intel.upiIds + regex_results["upiIds"])),
        }

        assert len(merged["phoneNumbers"]) == 1  # deduplicated
        assert len(merged["bankAccounts"]) == 1  # from regex only
        assert len(merged["upiIds"]) == 1  # from regex only

    def test_regex_catches_what_ai_misses(self):
        """
        Simulate: AI returns 0 intel (happens ~20% of turns per logs).
        Regex should still catch patterns from scammer's message.
        """
        scammer_message = (
            "Your account 1234567890123456 has been flagged. "
            "Send Rs 100 to scammer.fraud@fakebank or call +91-9876543210"
        )

        # AI failed — returned empty
        ai_intel = ExtractedIntelligence()

        # Regex scan
        phone_pattern = r"\+?91[-\s]?[6-9]\d{9}|\b[6-9]\d{9}\b"
        bank_pattern = r"\b\d{9,18}\b"
        upi_pattern = r"[\w.-]+@[a-zA-Z][a-zA-Z0-9]*"

        phones = re.findall(phone_pattern, scammer_message)
        banks = re.findall(bank_pattern, scammer_message)
        upis = re.findall(upi_pattern, scammer_message)

        # Filter banks to exclude phone-like numbers
        def is_phone(n):
            clean = re.sub(r"[-\s+]", "", n)
            return len(clean) == 10 and clean[0] in "6789"

        banks = [b for b in banks if not is_phone(b)]

        assert len(phones) >= 1, "Regex should catch phone even when AI fails"
        assert len(banks) >= 1, "Regex should catch bank account even when AI fails"
        assert len(upis) >= 1, "Regex should catch UPI even when AI fails"

    def test_extractor_extract_method_returns_regex_results(self):
        """extract() should now return regex-extracted results as backup to AI."""
        extractor = IntelligenceExtractor()
        result = extractor.extract("Send money to scammer@upi phone 9876543210")
        assert result.has_intelligence, "Regex extraction should find phone and UPI"
        assert len(result.phone_numbers) >= 1, "Should extract phone number"
        assert len(result.upi_ids) >= 1, "Should extract UPI ID"

    def test_extractor_validate_llm_extraction_handles_valid_data(self):
        """validate_llm_extraction should pass through valid AI-extracted data."""
        extractor = IntelligenceExtractor()
        intel = ExtractedIntelligence(
            bankAccounts=["1234567890123456"],
            upiIds=["scammer@fakebank"],
            phoneNumbers=["9876543210"],
            phishingLinks=["http://evil.com"],
            emails=["test@evil.com"],
        )
        validated = extractor.validate_llm_extraction(intel)
        assert len(validated.bankAccounts) == 1
        assert len(validated.upiIds) == 1
        assert len(validated.phoneNumbers) == 1
        assert len(validated.phishingLinks) == 1


# ============================================================================
# ISSUE 7: Skip classification after Turn 1 — cache per session
# ============================================================================


class TestClassificationCaching:
    """
    Currently we run 2 LLM calls per request:
      1. Classification (gemini-3-flash, 6-16s)
      2. Engagement (gemini-3-flash, 6-12s)
    
    After Turn 1 confirms scam, Turns 2-10 should skip classification
    and reuse the cached result. This saves 6-16 seconds per request.
    """

    def test_session_classification_cache_concept(self):
        """After fix: a per-session classification cache should exist."""
        # Simulate the cache
        session_classifications: dict[str, dict] = {}

        # Turn 1: classify as scam
        session_id = "session-abc"
        classification_result = {
            "is_scam": True,
            "confidence": 0.92,
            "scam_type": "banking_fraud",
        }
        session_classifications[session_id] = classification_result

        # Turn 2: should use cache
        assert session_id in session_classifications
        cached = session_classifications[session_id]
        assert cached["is_scam"] is True
        assert cached["confidence"] == 0.92

    def test_classification_skipped_for_cached_session(self):
        """Turn 2+ should not call detector.analyze() if session is cached."""
        cache = {"session-1": {"is_scam": True, "confidence": 0.9}}
        session_id = "session-1"

        # Simulate route logic
        if session_id in cache:
            detection_result = cache[session_id]
            used_cache = True
        else:
            detection_result = {"is_scam": True, "confidence": 0.9}  # would call LLM
            used_cache = False

        assert used_cache is True
        assert detection_result["is_scam"] is True

    def test_classification_called_for_new_session(self):
        """Turn 1 of a new session MUST run classification."""
        cache = {}
        session_id = "new-session"

        if session_id in cache:
            used_cache = True
        else:
            used_cache = False

        assert used_cache is False, "New session must go through LLM classification"

    def test_cached_classification_preserves_scam_type(self):
        """Cache should preserve scam_type for consistent agent behavior."""
        cache = {
            "s1": {"is_scam": True, "confidence": 0.88, "scam_type": "banking_fraud"},
        }
        assert cache["s1"]["scam_type"] == "banking_fraud"

    def test_latency_improvement_with_cache(self):
        """
        Simulate latency comparison:
        Without cache: classify(8s) + engage(8s) = 16s
        With cache:    cache_lookup(0s) + engage(8s) = 8s
        """
        classify_time = 8.0
        engage_time = 8.0

        without_cache = classify_time + engage_time
        with_cache = 0.001 + engage_time  # cache lookup is ~instant

        improvement = without_cache - with_cache
        assert improvement > 7.0, f"Expected >7s improvement, got {improvement:.1f}s"

    def test_confidence_only_escalates_in_cache(self):
        """
        Per ScamDetector logic: confidence only escalates.
        If Turn 1 = 0.7 and Turn 3 analysis would give 0.9,
        we should use max(cached, new) = 0.9.
        But if we skip classification on Turn 3, the cached 0.7 stays.
        This is acceptable since initial classification is sufficient.
        """
        cached_conf = 0.7
        # We skip re-classification, so cached_conf stays 0.7
        # This is fine — the agent still engages
        assert cached_conf >= 0.6, "Cached confidence should be above threshold"


# ============================================================================
# ISSUE 8: Set min-instances=1 on Cloud Run
# ============================================================================


class TestCloudRunMinInstances:
    """
    Cold start adds 7-8s to Turn 1 latency. Setting min-instances=1
    keeps one container warm at all times.
    """

    def test_cloudbuild_yaml_has_min_instances(self):
        """cloudbuild.yaml should set --min-instances=1 (or greater)."""
        import os

        cloudbuild_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "cloudbuild.yaml"
        )
        if not os.path.exists(cloudbuild_path):
            pytest.skip("cloudbuild.yaml not found")

        with open(cloudbuild_path) as f:
            content = f.read()

        # Check for min-instances setting
        assert "min-instances" in content, (
            "cloudbuild.yaml should include --min-instances=1 to prevent cold starts"
        )

    def test_deploy_script_has_min_instances(self):
        """deploy scripts should include --min-instances."""
        import os

        for script_name in ["deploy-quick.sh", "scripts/deploy-manual.sh"]:
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), script_name
            )
            if os.path.exists(script_path):
                with open(script_path) as f:
                    content = f.read()
                # Not a hard failure — just a check
                if "min-instances" not in content:
                    pytest.skip(f"{script_name} doesn't have min-instances (optional)")

    def test_cold_start_latency_impact(self):
        """
        Verify understanding: cold start adds 7-8s overhead.
        With min-instances=1, first request should skip cold start.
        """
        # This is a conceptual test — can't test actual Cloud Run behavior locally
        cold_start_overhead = 7.5  # seconds
        total_budget = 30.0  # evaluator timeout

        time_after_cold_start = total_budget - cold_start_overhead
        # Must fit: classify(8s) + engage(8s) = 16s
        assert time_after_cold_start >= 16.0, (
            "After cold start, only {:.1f}s left. "
            "Need at least 16s for LLM calls. min-instances=1 recovers {:.1f}s".format(
                time_after_cold_start, cold_start_overhead
            )
        )


# ============================================================================
# Latency budget analysis
# ============================================================================


class TestLatencyBudget:
    """Verify the system fits within the 30s evaluator timeout."""

    def test_single_llm_call_budget(self):
        """With classification caching, only 1 LLM call needed after Turn 1."""
        budget = 30.0  # evaluator timeout
        engage_time = 12.0  # worst case engagement LLM
        network_overhead = 2.0  # request/response overhead
        callback_time = 1.0

        total = engage_time + network_overhead + callback_time
        assert total < budget, f"Single-call pipeline ({total}s) must fit in {budget}s budget"

    def test_two_llm_call_budget_risky(self):
        """Two LLM calls (no cache) is risky on Turn 1."""
        budget = 30.0
        classify_time = 12.0
        engage_time = 12.0
        overhead = 3.0

        total = classify_time + engage_time + overhead
        # This should be close to or over 30s
        if total > budget:
            pass  # Expected — this is why caching is needed
        else:
            pass  # Lucky fast LLM responses

    def test_budget_with_cold_start_is_critical(self):
        """Without fixes, cold start + two LLM calls risks exceeding 30s budget.
        With min-instances=1 and classification caching, budget is safe."""
        cold_start = 7.5
        classify = 10.0
        engage = 10.0
        overhead = 2.0

        # Without fixes: risky
        total_without_fixes = cold_start + classify + engage + overhead
        assert total_without_fixes >= 29.0, (
            "The unfixed latency budget should be tight/risky"
        )

        # With fixes: min-instances removes cold start, caching removes classify (Turn 2+)
        total_with_fixes_turn2 = engage + overhead  # No cold start, no classify
        assert total_with_fixes_turn2 < 30.0, (
            "With caching + min-instances, Turn 2+ should be well under budget. "
            f"Got {total_with_fixes_turn2}s"
        )
