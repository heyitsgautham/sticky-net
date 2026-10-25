"""Tests for the engagement policy that picks cautious or aggressive mode."""

from src.agents.policy import EngagementMode, EngagementPolicy, EngagementState


class TestEngagementPolicy:
    """Tests for EngagementPolicy class."""

    def test_get_engagement_mode_aggressive(self):
        """Should return AGGRESSIVE for high confidence."""
        policy = EngagementPolicy()
        mode = policy.get_engagement_mode(0.90)
        assert mode == EngagementMode.AGGRESSIVE

    def test_get_engagement_mode_cautious(self):
        """Should return CAUTIOUS for medium confidence."""
        policy = EngagementPolicy()
        mode = policy.get_engagement_mode(0.70)
        assert mode == EngagementMode.CAUTIOUS

    def test_get_engagement_mode_none(self):
        """Should return NONE for low confidence."""
        policy = EngagementPolicy()
        mode = policy.get_engagement_mode(0.40)
        assert mode == EngagementMode.NONE

    def test_should_continue_within_limits(self):
        """Should continue when within limits."""
        policy = EngagementPolicy()
        state = EngagementState(
            mode=EngagementMode.AGGRESSIVE,
            turn_count=5,
            duration_seconds=100,
            intelligence_complete=False,
            scammer_suspicious=False,
            turns_since_new_info=2,
        )
        assert policy.should_continue(state) is True

    def test_should_not_continue_max_turns(self):
        """Should not continue when max turns reached."""
        policy = EngagementPolicy()
        state = EngagementState(
            mode=EngagementMode.CAUTIOUS,
            turn_count=15,  # More than cautious limit of 10
            duration_seconds=100,
            intelligence_complete=False,
            scammer_suspicious=False,
            turns_since_new_info=2,
        )
        assert policy.should_continue(state) is False

    def test_get_exit_reason_max_turns(self):
        """Should return correct exit reason."""
        policy = EngagementPolicy()
        state = EngagementState(
            mode=EngagementMode.CAUTIOUS,
            turn_count=15,
            duration_seconds=100,
            intelligence_complete=False,
            scammer_suspicious=False,
            turns_since_new_info=2,
        )
        reason = policy.get_exit_reason(state)
        assert reason is not None
        assert "turns" in reason.lower()

    def test_high_value_intelligence_complete_bank_and_phone(self):
        """Should NOT exit at turn 5 — MIN_TURNS_BEFORE_EXIT is 10 (never exit voluntarily)."""
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=["12345678901234"],
            phone_numbers=["9876543210"],
            beneficiary_names=["RAHUL KUMAR"],
            current_turn=5,
        )
        assert result is False  # Never exit early — evaluator controls end

    def test_high_value_intelligence_complete_at_turn_10(self):
        """Should detect high-value intel with bank account and phone at turn 10."""
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=["12345678901234"],
            phone_numbers=["9876543210"],
            beneficiary_names=["RAHUL KUMAR"],
            current_turn=10,
        )
        assert result is True

    def test_high_value_intelligence_complete_upi_and_phone(self):
        """Should NOT exit at turn 5 even with UPI and phone — MIN_TURNS is 10."""
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=[],
            phone_numbers=["9876543210"],
            upi_ids=["scammer@ybl"],
            beneficiary_names=["RAHUL KUMAR"],
            current_turn=5,
        )
        assert result is False  # Never exit early — evaluator controls end

    def test_high_value_intelligence_complete_upi_at_turn_10(self):
        """Should detect high-value intel with UPI and phone at turn 10."""
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=[],
            phone_numbers=["9876543210"],
            upi_ids=["scammer@ybl"],
            beneficiary_names=["RAHUL KUMAR"],
            current_turn=10,
        )
        assert result is True

    def test_high_value_intelligence_incomplete_no_phone(self):
        """Should return False if no phone number."""
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=["12345678901234"],
            phone_numbers=[],
            upi_ids=["scammer@ybl"],
            beneficiary_names=["RAHUL KUMAR"],
        )
        assert result is False

    def test_high_value_intelligence_incomplete_no_bank_or_upi(self):
        """Should return False if no bank account or UPI."""
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=[],
            phone_numbers=["9876543210"],
            upi_ids=[],
            beneficiary_names=["RAHUL KUMAR"],
        )
        assert result is False

    def test_high_value_intelligence_incomplete_empty(self):
        """Should return False if everything is empty."""
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=[],
            phone_numbers=[],
        )
        assert result is False

    def test_high_value_intelligence_incomplete_no_beneficiary(self):
        """Should return False if no beneficiary name (CRITICAL - mule name required)."""
        # Even with UPI and phone, we need the beneficiary name to identify the mule
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=[],
            phone_numbers=["9876543210"],
            upi_ids=["scammer@ybl"],
            beneficiary_names=[],  # Missing!
        )
        assert result is False

    def test_get_missing_intelligence_returns_beneficiary(self):
        """Should identify missing beneficiary name when UPI/phone present."""
        missing = EngagementPolicy.get_missing_intelligence(
            bank_accounts=[],
            phone_numbers=["9876543210"],
            upi_ids=["scammer@ybl"],
            beneficiary_names=[],
        )
        assert "beneficiary_name" in missing
        assert "payment_details" not in missing  # UPI is present
        assert "phone_number" not in missing  # Phone is present

    def test_get_missing_intelligence_complete(self):
        """Should return only email_address when all other intelligence is present."""
        missing = EngagementPolicy.get_missing_intelligence(
            bank_accounts=["12345678901234"],
            phone_numbers=["9876543210"],
            upi_ids=["scammer@ybl"],
            beneficiary_names=["RAHUL KUMAR"],
        )
        assert missing == ["email_address"]
