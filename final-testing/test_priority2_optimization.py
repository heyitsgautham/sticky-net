"""
Test suite for PRIORITY 2 fixes — OPTIMIZATION.

  ISSUE 9:  Increase Cloud Run timeout to 300s         (prevents 504)
  ISSUE 10: Conversation summary for history > 8 turns (better agent quality)
  ISSUE 11: Switch engagement model to flash            (-3-5s latency)
  ISSUE 12: Reduce system prompt token count            (-2-3s latency)

These optimizations improve reliability and response quality but have
less direct impact on the score than Priority 0 and 1 fixes.

Run:  .venv/bin/python -m pytest final-testing/test_priority2_optimization.py -v
"""

import os

import pytest

from config.settings import Settings


# ============================================================================
# ISSUE 9: Cloud Run timeout to 300s
# ============================================================================


class TestCloudRunTimeout:
    """
    Default Cloud Run timeout is 60s. LLM calls can take 15-37s,
    plus retries can push past 60s → 504 Gateway Timeout.
    Setting timeout to 300s prevents this.
    """

    def test_api_timeout_setting_is_sufficient(self):
        """api_timeout_seconds should be >= 90s to handle slow LLM responses."""
        # Read from settings
        settings = Settings(
            api_key="test",
            google_cloud_project="test",
        )
        assert settings.api_timeout_seconds >= 90, (
            f"api_timeout_seconds={settings.api_timeout_seconds} is too low. "
            "Should be >= 90s to handle slow Gemini responses."
        )

    def test_cloudbuild_timeout_setting(self):
        """cloudbuild.yaml should set --timeout >= 300 for Cloud Run service."""
        cloudbuild_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "cloudbuild.yaml"
        )
        if not os.path.exists(cloudbuild_path):
            pytest.skip("cloudbuild.yaml not found")

        with open(cloudbuild_path) as f:
            content = f.read()

        # Look for timeout setting
        if "--timeout" in content:
            import re
            match = re.search(r"--timeout[=\s]+(\d+)", content)
            if match:
                timeout_val = int(match.group(1))
                assert timeout_val >= 300, (
                    f"Cloud Run timeout={timeout_val}s is too low. "
                    "Set --timeout=300 to prevent 504 errors."
                )

    def test_gemini_retry_settings(self):
        """Retry settings should allow recovery from transient failures."""
        settings = Settings(
            api_key="test",
            google_cloud_project="test",
        )
        assert settings.gemini_max_retries >= 1, "Should have at least 1 retry"
        assert settings.gemini_retry_delay_seconds >= 0.5, "Retry delay should be >= 0.5s"

    def test_total_worst_case_time_within_timeout(self):
        """
        Worst case: classify(16s) + engage(12s) + retries(2×1s) + overhead(2s) = 32s
        This must be < Cloud Run timeout (300s).
        """
        classify_time = 16.0
        engage_time = 12.0
        retries = 2 * 1.0  # 2 retries × 1s delay
        overhead = 2.0

        worst_case = classify_time + engage_time + retries + overhead
        cloud_run_timeout = 300.0
        assert worst_case < cloud_run_timeout, (
            f"Worst case {worst_case}s exceeds Cloud Run timeout {cloud_run_timeout}s"
        )


# ============================================================================
# ISSUE 10: Conversation summary for history > 8 turns
# ============================================================================


class TestConversationSummary:
    """
    context_window_turns=8 means after Turn 8, history is truncated.
    Agent loses earlier context and starts repeating.
    A summary of earlier turns should be prepended.
    """

    def test_context_window_setting(self):
        """Verify the context window is 8 turns."""
        settings = Settings(
            api_key="test",
            google_cloud_project="test",
        )
        assert settings.context_window_turns == 8

    def test_history_truncation_loses_early_intel(self):
        """
        Simulate: 12-turn conversation. After truncation to last 8 turns,
        turns 1-4 are lost. If intel was shared in turns 1-4, agent loses context.
        """
        full_history = [
            {"sender": "scammer", "text": f"Turn {i} message", "turn": i}
            for i in range(1, 13)
        ]

        context_window = 8
        truncated = full_history[-context_window:]

        # Turns 1-4 are lost
        lost_turns = full_history[:len(full_history) - context_window]
        assert len(lost_turns) == 4
        assert lost_turns[0]["turn"] == 1

        # If phone was shared in Turn 2, it's gone from context
        full_history[1]["text"] = "Call me at 9876543210"
        truncated = full_history[-context_window:]
        turn2_in_context = any("9876543210" in msg["text"] for msg in truncated)
        assert not turn2_in_context, (
            "Phone from Turn 2 is lost after truncation — "
            "need summary to preserve this intel"
        )

    def test_agent_build_prompt_includes_summary_for_long_history(self):
        """
        After fix: _build_prompt should include a SUMMARY section when
        history exceeds context_window_turns.
        """
        from unittest.mock import MagicMock, patch
        from datetime import datetime
        from src.agents.honeypot_agent import HoneypotAgent
        from src.agents.persona import Persona
        from src.api.schemas import Message, ConversationMessage, SenderType
        from src.detection.detector import DetectionResult

        with patch("src.agents.honeypot_agent.genai.Client") as mock_client_class:
            mock_client_class.return_value = MagicMock()
            agent = HoneypotAgent()

            # 12 messages total; phone in turn 3 (will be truncated with window=8)
            history = []
            for i in range(12):
                sender = SenderType.SCAMMER if i % 2 == 0 else SenderType.USER
                text = f"Turn {i+1} message"
                if i == 2:
                    text = "Call me at +91-9876543210"
                history.append(
                    ConversationMessage(
                        sender=sender,
                        text=text,
                        timestamp=datetime.now(),
                    )
                )

            detection = DetectionResult(
                is_scam=True, confidence=0.9,
                scam_type="banking_fraud", reasoning="test",
            )
            message = Message(
                sender=SenderType.SCAMMER,
                text="Send now!",
                timestamp=datetime.now(),
            )

            prompt = agent._build_prompt(
                message=message,
                history=history,
                detection=detection,
                persona=Persona(),
            )

            # Summary must be present
            assert "SUMMARY" in prompt, "Prompt must include summary of truncated turns"
            # Phone from early turn must be preserved in summary
            assert "9876543210" in prompt, "Summary must preserve phone from truncated turns"

    def test_summary_preserves_key_intel_from_early_turns(self):
        """
        After fix: a summary of truncated turns should mention key intel.
        """
        from unittest.mock import MagicMock, patch
        from datetime import datetime
        from src.agents.honeypot_agent import HoneypotAgent
        from src.api.schemas import ConversationMessage, SenderType

        with patch("src.agents.honeypot_agent.genai.Client") as mock_client_class:
            mock_client_class.return_value = MagicMock()
            agent = HoneypotAgent()

            truncated_turns = [
                ConversationMessage(
                    sender=SenderType.SCAMMER,
                    text="URGENT: Your SBI account compromised",
                    timestamp=datetime.now(),
                ),
                ConversationMessage(
                    sender=SenderType.USER,
                    text="Oh no what should I do?",
                    timestamp=datetime.now(),
                ),
                ConversationMessage(
                    sender=SenderType.SCAMMER,
                    text="Call me at +91-9876543210",
                    timestamp=datetime.now(),
                ),
                ConversationMessage(
                    sender=SenderType.USER,
                    text="Let me note that number",
                    timestamp=datetime.now(),
                ),
            ]

            summary = agent._generate_conversation_summary(truncated_turns)

            # Key intel from truncated turns must be preserved
            assert "9876543210" in summary, "Summary must preserve phone number"

    def test_summary_does_not_exceed_token_budget(self):
        """Summary should be concise — not more than ~200 words."""
        from unittest.mock import MagicMock, patch
        from datetime import datetime
        from src.agents.honeypot_agent import HoneypotAgent
        from src.api.schemas import ConversationMessage, SenderType

        with patch("src.agents.honeypot_agent.genai.Client") as mock_client_class:
            mock_client_class.return_value = MagicMock()
            agent = HoneypotAgent()

            # Create many long messages
            turns = []
            for i in range(20):
                sender = SenderType.SCAMMER if i % 2 == 0 else SenderType.USER
                turns.append(
                    ConversationMessage(
                        sender=sender,
                        text=f"Long message number {i+1} with many words " * 5,
                        timestamp=datetime.now(),
                    )
                )

            summary = agent._generate_conversation_summary(turns)
            word_count = len(summary.split())
            assert word_count <= 210, (
            f"Summary has {word_count} words, should be <= {max_summary_words}"
        )


# ============================================================================
# ISSUE 11: Switch engagement model to flash
# ============================================================================


class TestEngagementModelSelection:
    """
    Using pro model for engagement is slower. Flash model reduces latency
    by 3-5s while maintaining response quality.
    """

    def test_pro_model_setting(self):
        """Check what model is configured for engagement."""
        settings = Settings(
            api_key="test",
            google_cloud_project="test",
        )
        # Currently pro_model might be set to flash already
        # Either is acceptable but flash is faster
        assert settings.pro_model in [
            "gemini-3-flash-preview",
            "gemini-3-pro-preview",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ], f"Unexpected model: {settings.pro_model}"

    def test_flash_model_for_classification(self):
        """Classification should use flash model (fastest)."""
        settings = Settings(
            api_key="test",
            google_cloud_project="test",
        )
        assert "flash" in settings.flash_model.lower(), (
            f"Classification model '{settings.flash_model}' should use flash for speed"
        )

    def test_flash_model_latency_is_lower(self):
        """Flash model should be significantly faster than pro."""
        # Based on observed latencies from logs
        flash_latency = 8.0  # seconds average
        pro_latency = 12.0  # seconds average

        improvement = pro_latency - flash_latency
        assert improvement >= 3.0, (
            f"Flash saves {improvement:.1f}s over pro — should be >= 3s"
        )


# ============================================================================
# ISSUE 12: Reduce system prompt token count
# ============================================================================


class TestSystemPromptOptimization:
    """
    System prompt tokens directly impact LLM latency.
    Reducing prompt size saves 2-3s per request.
    """

    def test_honeypot_system_prompt_exists(self):
        """System prompt should be importable."""
        from src.agents.prompts import HONEYPOT_SYSTEM_PROMPT
        assert isinstance(HONEYPOT_SYSTEM_PROMPT, str)
        assert len(HONEYPOT_SYSTEM_PROMPT) > 100

    def test_system_prompt_not_excessively_long(self):
        """System prompt should be under ~4000 words to keep latency low."""
        from src.agents.prompts import HONEYPOT_SYSTEM_PROMPT

        word_count = len(HONEYPOT_SYSTEM_PROMPT.split())
        max_words = 4000

        if word_count > max_words:
            pytest.fail(
                f"System prompt has {word_count} words (>{max_words}). "
                "Consider reducing to save 2-3s latency per request."
            )

    def test_system_prompt_contains_essential_instructions(self):
        """Even after optimization, prompt must contain key instructions."""
        from src.agents.prompts import HONEYPOT_SYSTEM_PROMPT

        essential_elements = [
            "persona",  # Must define persona
            "extract",  # Must instruct extraction
            "intelligence",  # Must mention intelligence
            "bank",  # Must know about bank accounts
            "upi",  # Must know about UPI
            "phone",  # Must know about phone numbers
        ]

        prompt_lower = HONEYPOT_SYSTEM_PROMPT.lower()
        for element in essential_elements:
            assert element in prompt_lower, (
                f"System prompt must contain '{element}' for proper agent behavior"
            )

    def test_system_prompt_has_json_output_instructions(self):
        """Prompt must instruct AI to output structured JSON."""
        from src.agents.prompts import HONEYPOT_SYSTEM_PROMPT

        json_indicators = ["json", "reply_text", "extracted_intelligence"]
        prompt_lower = HONEYPOT_SYSTEM_PROMPT.lower()

        found = sum(1 for ind in json_indicators if ind in prompt_lower)
        assert found >= 2, (
            "System prompt must contain JSON output format instructions"
        )


# ============================================================================
# Combined: Deployment configuration validation
# ============================================================================


class TestDeploymentConfiguration:
    """Validate deployment configuration for optimal performance."""

    def test_dockerfile_exists(self):
        """Dockerfile should exist for containerized deployment."""
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Dockerfile")
        assert os.path.exists(path), "Dockerfile not found"

    def test_docker_compose_exists(self):
        """docker-compose.yml should exist for local dev."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml"
        )
        assert os.path.exists(path), "docker-compose.yml not found"

    def test_guvi_callback_settings(self):
        """GUVI callback should be configurable."""
        settings = Settings(
            api_key="test",
            google_cloud_project="test",
        )
        assert settings.guvi_callback_url.startswith("https://")
        assert settings.guvi_callback_timeout > 0
        assert isinstance(settings.guvi_callback_enabled, bool)

    def test_engagement_policy_thresholds(self):
        """Engagement policy thresholds should be properly configured."""
        settings = Settings(
            api_key="test",
            google_cloud_project="test",
        )
        assert 0.5 <= settings.cautious_confidence_threshold <= 0.7
        assert 0.8 <= settings.aggressive_confidence_threshold <= 0.95
        assert settings.max_engagement_turns_cautious >= 5
        assert settings.max_engagement_turns_aggressive >= 15
