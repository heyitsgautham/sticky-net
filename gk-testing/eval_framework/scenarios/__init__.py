"""
Evaluation Scenarios — Test scenarios that mirror the GUVI hackathon format.

Each scenario contains:
  - scenarioId, name, scamType, weight
  - initialMessage: first scammer message
  - metadata: channel, language, locale
  - maxTurns: max conversation exchanges (up to 10)
  - fakeData: planted intelligence the honeypot should extract
  - turns: scripted scammer follow-ups with embedded fake data

Scenarios cover the same categories the hackathon evaluates:
  - Bank fraud, UPI fraud, Phishing
  - Plus edge cases: tech support, job scam, mixed language
"""

from __future__ import annotations

from eval_framework.scenarios.extended import INSURANCE_SCAM_SCENARIO, TECH_SUPPORT_SCENARIO
from eval_framework.scenarios.standard import (
    BANK_FRAUD_SCENARIO,
    PHISHING_SCENARIO,
    UPI_FRAUD_SCENARIO,
)

# Standard 3-scenario suite (matches hackathon format: bank + UPI + phishing)
STANDARD_SCENARIOS = [
    BANK_FRAUD_SCENARIO,
    UPI_FRAUD_SCENARIO,
    PHISHING_SCENARIO,
]
STANDARD_WEIGHTS = [0.35, 0.35, 0.30]

# Extended 5-scenario suite for thorough testing
EXTENDED_SCENARIOS = [
    BANK_FRAUD_SCENARIO,
    UPI_FRAUD_SCENARIO,
    PHISHING_SCENARIO,
    TECH_SUPPORT_SCENARIO,
    INSURANCE_SCAM_SCENARIO,
]
EXTENDED_WEIGHTS = [0.25, 0.25, 0.20, 0.15, 0.15]

ALL_SCENARIOS = {
    "bank_fraud_01": BANK_FRAUD_SCENARIO,
    "upi_fraud_01": UPI_FRAUD_SCENARIO,
    "phishing_01": PHISHING_SCENARIO,
    "tech_support_01": TECH_SUPPORT_SCENARIO,
    "insurance_01": INSURANCE_SCAM_SCENARIO,
}


def get_scenario(scenario_id: str) -> dict:
    """Get a scenario by ID."""
    if scenario_id not in ALL_SCENARIOS:
        raise ValueError(
            f"Unknown scenario '{scenario_id}'. "
            f"Available: {list(ALL_SCENARIOS.keys())}"
        )
    return ALL_SCENARIOS[scenario_id]


def get_scenario_suite(name: str = "standard") -> tuple[list[dict], list[float]]:
    """
    Get a named suite of scenarios with weights.
    
    Args:
        name: "standard" (3 scenarios) or "extended" (5 scenarios)
    
    Returns:
        (scenarios_list, weights_list) where weights sum to 1.0
    """
    if name == "standard":
        return STANDARD_SCENARIOS, STANDARD_WEIGHTS
    elif name == "extended":
        return EXTENDED_SCENARIOS, EXTENDED_WEIGHTS
    else:
        raise ValueError(f"Unknown suite '{name}'. Available: standard, extended")
