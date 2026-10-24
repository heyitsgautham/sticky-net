"""Result records for one evaluation run: per turn, per scenario and overall."""

from __future__ import annotations

from dataclasses import dataclass, field

from eval_framework.scoring import ScoreBreakdown


@dataclass
class TurnResult:
    """Result of a single conversation turn."""
    turn_number: int
    scammer_message: str
    agent_response: str
    response_time_seconds: float
    api_response_raw: dict
    expected_extractions: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class ScenarioResult:
    """Complete result of running one scenario."""
    scenario_id: str
    scenario_name: str
    scam_type: str
    weight: float
    turns: list[TurnResult] = field(default_factory=list)
    final_output: dict = field(default_factory=dict)
    score: ScoreBreakdown | None = None
    agent_responses: list[str] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "scenarioId": self.scenario_id,
            "scenarioName": self.scenario_name,
            "scamType": self.scam_type,
            "weight": self.weight,
            "turnCount": len(self.turns),
            "totalDuration": round(self.total_duration_seconds, 2),
            "score": self.score.to_dict() if self.score else None,
            "turns": [
                {
                    "turn": t.turn_number,
                    "scammerMessage": t.scammer_message,
                    "agentResponse": t.agent_response,
                    "responseTime": t.response_time_seconds,
                    "expectedExtractions": t.expected_extractions,
                    "error": t.error,
                }
                for t in self.turns
            ],
            "error": self.error,
        }


@dataclass
class EvalResult:
    """Complete evaluation result across all scenarios."""
    scenarios: list[ScenarioResult] = field(default_factory=list)
    weighted_score: float = 0.0
    code_quality_score: float = 0.0
    final_score: float = 0.0
    started_at: str = ""
    ended_at: str = ""

    def to_dict(self) -> dict:
        return {
            "weightedScenarioScore": round(self.weighted_score, 2),
            "codeQualityScore": self.code_quality_score,
            "finalScore": round(self.final_score, 2),
            "startedAt": self.started_at,
            "endedAt": self.ended_at,
            "scenarios": [s.to_dict() for s in self.scenarios],
            "scoreFormula": "finalScore = (weightedScenarioScore * 0.9) + codeQualityScore",
        }
