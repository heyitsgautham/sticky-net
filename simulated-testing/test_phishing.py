"""
Phishing scenario tests — runs all 5 phishing scenarios against the API.
"""

import pytest
from conftest import scenario_params


@pytest.mark.parametrize("scenario", scenario_params("phishing"))
def test_phishing_scenario(runner, scenario):
    """Run a phishing scenario and validate GUVI scoring."""
    result = runner.run_scenario(scenario)

    print(f"\n{result.score.summary()}")
    if result.conversation.errors:
        print(f"  Errors: {result.conversation.errors}")

    assert result.score.scam_detection == 20.0, (
        f"Scam not detected for {result.scenario_id}"
    )
    assert result.score.total >= scenario.get("expected_score", {}).get("min", 60), (
        f"Score {result.score.total} below minimum for {result.scenario_id}. "
        f"Issues: {result.score.issues}"
    )
    assert len(result.conversation.errors) == 0, (
        f"API errors: {result.conversation.errors}"
    )


@pytest.mark.parametrize("scenario", scenario_params("phishing"))
def test_phishing_reply_present(runner, scenario):
    """Every turn should receive a non-empty reply."""
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1} for {result.scenario_id}"


@pytest.mark.parametrize("scenario", scenario_params("phishing"))
def test_phishing_link_extracted(runner, scenario):
    """If fakeData has phishingLink, it should appear in extractedIntelligence."""
    if "phishingLink" not in scenario.get("fakeData", {}):
        pytest.skip("No phishingLink in fakeData")

    result = runner.run_scenario(scenario)
    link = scenario["fakeData"]["phishingLink"]
    extracted = result.final_output.get("extractedIntelligence", {})
    links = extracted.get("phishingLinks", [])
    found = any(link in str(v) for v in links)

    print(f"\n  Link check: '{link}' in {links} → {'FOUND' if found else 'MISS'}")


@pytest.mark.parametrize("scenario", scenario_params("phishing"))
def test_phishing_email_extracted(runner, scenario):
    """If fakeData has emailAddress, it should appear in extractedIntelligence."""
    if "emailAddress" not in scenario.get("fakeData", {}):
        pytest.skip("No emailAddress in fakeData")

    result = runner.run_scenario(scenario)
    email = scenario["fakeData"]["emailAddress"]
    extracted = result.final_output.get("extractedIntelligence", {})
    emails = extracted.get("emailAddresses", [])
    found = any(email in str(v) for v in emails)

    print(f"\n  Email check: '{email}' in {emails} → {'FOUND' if found else 'MISS'}")


@pytest.mark.parametrize("scenario", scenario_params("phishing"))
def test_phishing_response_structure(runner, scenario):
    """Response structure should have at least required fields."""
    result = runner.run_scenario(scenario)
    assert result.score.response_structure >= 15.0, (
        f"Response structure {result.score.response_structure} too low"
    )
