"""
Other scam type tests — job, lottery, investment, government, delivery,
romance, and tech support scam scenarios.
"""

import pytest
from conftest import scenario_params


# ======================================================================
# Job Scam (3 scenarios)
# ======================================================================
@pytest.mark.parametrize("scenario", scenario_params("job_scam"))
def test_job_scam_scenario(runner, scenario):
    """Run a job scam scenario and validate GUVI scoring."""
    result = runner.run_scenario(scenario)

    print(f"\n{result.score.summary()}")

    assert result.score.scam_detection == 20.0, (
        f"Scam not detected for {result.scenario_id}"
    )
    assert result.score.total >= scenario.get("expected_score", {}).get("min", 50), (
        f"Score {result.score.total} below minimum for {result.scenario_id}. "
        f"Issues: {result.score.issues}"
    )
    assert len(result.conversation.errors) == 0


@pytest.mark.parametrize("scenario", scenario_params("job_scam"))
def test_job_scam_reply_present(runner, scenario):
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1}"


# ======================================================================
# Lottery Scam (3 scenarios)
# ======================================================================
@pytest.mark.parametrize("scenario", scenario_params("lottery_scam"))
def test_lottery_scam_scenario(runner, scenario):
    """Run a lottery scam scenario and validate GUVI scoring."""
    result = runner.run_scenario(scenario)

    print(f"\n{result.score.summary()}")

    assert result.score.scam_detection == 20.0, (
        f"Scam not detected for {result.scenario_id}"
    )
    assert result.score.total >= scenario.get("expected_score", {}).get("min", 50), (
        f"Score {result.score.total} below minimum. Issues: {result.score.issues}"
    )
    assert len(result.conversation.errors) == 0


@pytest.mark.parametrize("scenario", scenario_params("lottery_scam"))
def test_lottery_scam_reply_present(runner, scenario):
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1}"


# ======================================================================
# Investment Scam (3 scenarios)
# ======================================================================
@pytest.mark.parametrize("scenario", scenario_params("investment_scam"))
def test_investment_scam_scenario(runner, scenario):
    """Run an investment scam scenario and validate GUVI scoring."""
    result = runner.run_scenario(scenario)

    print(f"\n{result.score.summary()}")

    assert result.score.scam_detection == 20.0, (
        f"Scam not detected for {result.scenario_id}"
    )
    assert result.score.total >= scenario.get("expected_score", {}).get("min", 50), (
        f"Score {result.score.total} below minimum. Issues: {result.score.issues}"
    )
    assert len(result.conversation.errors) == 0


@pytest.mark.parametrize("scenario", scenario_params("investment_scam"))
def test_investment_scam_reply_present(runner, scenario):
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1}"


# ======================================================================
# Government Scam (4 scenarios)
# ======================================================================
@pytest.mark.parametrize("scenario", scenario_params("government_scam"))
def test_government_scam_scenario(runner, scenario):
    """Run a government scam scenario and validate GUVI scoring."""
    result = runner.run_scenario(scenario)

    print(f"\n{result.score.summary()}")

    assert result.score.scam_detection == 20.0, (
        f"Scam not detected for {result.scenario_id}"
    )
    assert result.score.total >= scenario.get("expected_score", {}).get("min", 50), (
        f"Score {result.score.total} below minimum. Issues: {result.score.issues}"
    )
    assert len(result.conversation.errors) == 0


@pytest.mark.parametrize("scenario", scenario_params("government_scam"))
def test_government_scam_reply_present(runner, scenario):
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1}"


# ======================================================================
# Delivery Scam (3 scenarios)
# ======================================================================
@pytest.mark.parametrize("scenario", scenario_params("delivery_scam"))
def test_delivery_scam_scenario(runner, scenario):
    """Run a delivery scam scenario and validate GUVI scoring."""
    result = runner.run_scenario(scenario)

    print(f"\n{result.score.summary()}")

    assert result.score.scam_detection == 20.0, (
        f"Scam not detected for {result.scenario_id}"
    )
    assert result.score.total >= scenario.get("expected_score", {}).get("min", 50), (
        f"Score {result.score.total} below minimum. Issues: {result.score.issues}"
    )
    assert len(result.conversation.errors) == 0


@pytest.mark.parametrize("scenario", scenario_params("delivery_scam"))
def test_delivery_scam_reply_present(runner, scenario):
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1}"


# ======================================================================
# Romance Scam (2 scenarios)
# ======================================================================
@pytest.mark.parametrize("scenario", scenario_params("romance_scam"))
def test_romance_scam_scenario(runner, scenario):
    """Run a romance scam scenario and validate GUVI scoring."""
    result = runner.run_scenario(scenario)

    print(f"\n{result.score.summary()}")

    # Romance scams start as legitimate — detection might be delayed
    # So we check overall score rather than strict detection
    assert result.score.total >= scenario.get("expected_score", {}).get("min", 40), (
        f"Score {result.score.total} below minimum. Issues: {result.score.issues}"
    )
    assert len(result.conversation.errors) == 0


@pytest.mark.parametrize("scenario", scenario_params("romance_scam"))
def test_romance_scam_reply_present(runner, scenario):
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1}"


# ======================================================================
# Tech Support Scam (3 scenarios)
# ======================================================================
@pytest.mark.parametrize("scenario", scenario_params("tech_support_scam"))
def test_tech_support_scam_scenario(runner, scenario):
    """Run a tech support scam scenario and validate GUVI scoring."""
    result = runner.run_scenario(scenario)

    print(f"\n{result.score.summary()}")

    assert result.score.scam_detection == 20.0, (
        f"Scam not detected for {result.scenario_id}"
    )
    assert result.score.total >= scenario.get("expected_score", {}).get("min", 50), (
        f"Score {result.score.total} below minimum. Issues: {result.score.issues}"
    )
    assert len(result.conversation.errors) == 0


@pytest.mark.parametrize("scenario", scenario_params("tech_support_scam"))
def test_tech_support_scam_reply_present(runner, scenario):
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1}"
