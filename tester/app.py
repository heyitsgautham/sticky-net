"""Honeypot Tester – FastAPI application.

Provides a REST API and a simple web UI to run automated evaluation sessions
against any deployed honeypot endpoint.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from src.conversation import ConversationRunner
from src.evaluator import Evaluator, ScoreBreakdown, calculate_final_score
from src.scammer_agent import ScammerAgent
from src.scenarios import (
    DEFAULT_SUITE,
    EXTENDED_SUITE,
    SCENARIO_REGISTRY,
    FakeData,
    Scenario,
)

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Honeypot Tester",
    description="Automated scammer simulator that evaluates honeypot API endpoints",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (replace with Redis for production)
_jobs: dict[str, dict] = {}

# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────


class RunSuiteRequest(BaseModel):
    target_url: str = Field(..., description="Full URL of the honeypot endpoint")
    api_key: str | None = Field(None, description="API key sent as x-api-key header")
    scenario_ids: list[str] = Field(
        default_factory=lambda: list(DEFAULT_SUITE),
        description="Scenario IDs to run (default: all 3 built-in scenarios)",
    )
    code_quality_score: float = Field(
        default=0.0, ge=0, le=10,
        description="Manual code quality score out of 10",
    )
    mode: str = Field(
        default="official",
        description="'official' = 3 scenarios at rubric weights, 'extended' = 10 scenarios at 10% each",
    )


class RunSingleRequest(BaseModel):
    target_url: str
    api_key: str | None = None
    scenario_id: str = Field(..., description="Scenario ID to run")


class CustomScenarioRequest(BaseModel):
    target_url: str
    api_key: str | None = None
    name: str
    scam_type: str
    weight: float = Field(default=100.0, ge=0, le=100)
    initial_message: str
    max_turns: int = Field(default=10, ge=1, le=20)
    persona_context: str
    metadata: dict[str, str] = Field(
        default_factory=lambda: {"channel": "SMS", "language": "English", "locale": "IN"}
    )
    # Fake data
    phone_numbers: list[str] = Field(default_factory=list)
    bank_accounts: list[str] = Field(default_factory=list)
    upi_ids: list[str] = Field(default_factory=list)
    phishing_links: list[str] = Field(default_factory=list)
    email_addresses: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    policy_numbers: list[str] = Field(default_factory=list)
    order_numbers: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_scammer_agent() -> ScammerAgent:
    return ScammerAgent(
        project=os.environ.get("GOOGLE_CLOUD_PROJECT", "sticky-net-485205"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        model=os.environ.get("SCAMMER_MODEL", "gemini-2.5-flash"),
        use_vertexai=os.environ.get("USE_VERTEXAI", "true").lower() == "true",
    )


def _get_runner(target_url: str, api_key: str | None) -> ConversationRunner:
    return ConversationRunner(
        target_url=target_url,
        api_key=api_key,
        scammer_agent=_get_scammer_agent(),
        request_timeout=float(os.environ.get("REQUEST_TIMEOUT", "30")),
    )


def _score_to_dict(breakdown: ScoreBreakdown) -> dict:
    return {
        "total": round(breakdown.total, 2),
        "scam_detection": round(breakdown.scam_detection, 2),
        "intelligence": round(breakdown.intelligence, 2),
        "conversation_quality": round(breakdown.conversation_quality, 2),
        "engagement_quality": round(breakdown.engagement_quality, 2),
        "response_structure": round(breakdown.response_structure, 2),
        "details": {
            "scam_detected": breakdown.scam_detected,
            "extracted_items": breakdown.extracted_items,
            "missed_items": breakdown.missed_items,
            "turn_count": breakdown.turn_count,
            "questions_asked": breakdown.questions_asked,
            "relevant_questions": breakdown.relevant_questions,
            "red_flags_found": breakdown.red_flags_found,
            "elicitation_attempts": breakdown.elicitation_attempts,
            "engagement_duration_seconds": breakdown.engagement_duration_seconds,
            "total_messages": breakdown.total_messages,
            "intelligence_detail": breakdown.intelligence_detail,
            "structure_issues": breakdown.structure_issues,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Background task runner
# ─────────────────────────────────────────────────────────────────────────────

async def _run_suite_background(
    job_id: str,
    target_url: str,
    api_key: str | None,
    scenarios: list[Scenario],
    code_quality_score: float,
) -> None:
    """Run all scenarios sequentially and populate the job result."""
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.utcnow().isoformat()

    evaluator = Evaluator()
    results: list[tuple[Scenario, ScoreBreakdown]] = []
    session_logs: list[dict] = []

    async def turn_callback(turn: int, sender: str, text: str) -> None:
        _jobs[job_id]["current_turn"] = turn
        _jobs[job_id]["last_sender"] = sender
        _jobs[job_id]["last_text"] = text[:120]

    try:
        runner = _get_runner(target_url, api_key)

        for idx, scenario in enumerate(scenarios):
            logger.info("[Job %s] Running scenario %d/%d: %s", job_id, idx + 1, len(scenarios), scenario.name)
            _jobs[job_id]["current_scenario"] = scenario.name
            _jobs[job_id]["current_scenario_idx"] = idx
            _jobs[job_id]["current_max_turns"] = scenario.max_turns
            _jobs[job_id]["current_turn"] = 0
            _jobs[job_id]["progress"] = f"{idx}/{len(scenarios)}"

            session_id = str(uuid.uuid4())

            try:
                history, final_output, elapsed = await runner.run(
                    scenario=scenario,
                    session_id=session_id,
                    on_turn=turn_callback,
                )
                score = evaluator.score(scenario, history, final_output, elapsed)
                results.append((scenario, score))

                session_logs.append({
                    "scenario_id": scenario.id,
                    "scenario_name": scenario.name,
                    "scam_type": scenario.scam_type,
                    "weight": scenario.weight,
                    "session_id": session_id,
                    "score": _score_to_dict(score),
                    "conversation_history": history,
                    "final_output": final_output,
                    "elapsed_seconds": round(elapsed, 2),
                })
            except Exception as exc:
                logger.error("[Job %s] Scenario %s failed: %s", job_id, scenario.id, exc)
                session_logs.append({
                    "scenario_id": scenario.id,
                    "scenario_name": scenario.name,
                    "scam_type": scenario.scam_type,
                    "weight": scenario.weight,
                    "session_id": session_id,
                    "error": str(exc),
                    "score": None,
                })

        final = calculate_final_score(results, code_quality_score)
        _jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "progress": f"{len(scenarios)}/{len(scenarios)}",
            "current_scenario": None,
            "current_turn": 0,
            "final_score": final,
            "session_logs": session_logs,
        })
        logger.info("[Job %s] Completed – final score: %s", job_id, final["final_score"])

    except Exception as exc:
        logger.exception("[Job %s] Suite runner crashed: %s", job_id, exc)
        _jobs[job_id].update({
            "status": "failed",
            "error": str(exc),
            "completed_at": datetime.utcnow().isoformat(),
        })


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

# index.html loads app.css and app.js from here.
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """Serve the web UI."""
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/run/auto")
async def run_auto(req: RunSuiteRequest) -> dict:
    """Start a full evaluation suite.

    mode='official'  → 3 scenarios, rubric-exact weights (35/35/30)
    mode='extended'  → all 10 scenarios, equal 10% weights each
    """
    import copy
    if req.mode == "extended":
        raw = [SCENARIO_REGISTRY[sid] for sid in EXTENDED_SUITE]
        # Override weight to 10% each so they sum to 100%
        scenario_list = [
            copy.replace(s, weight=10.0) if hasattr(copy, "replace") else
            Scenario(**{**s.__dict__, "weight": 10.0})
            for s in raw
        ]
    else:
        # Official: exact rubric simulation — bank 35%, upi 35%, phishing 30%
        scenario_list = [SCENARIO_REGISTRY[sid] for sid in DEFAULT_SUITE]

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "queued",
        "job_id": job_id,
        "target_url": req.target_url,
        "mode": req.mode,
        "scenario_count": len(scenario_list),
        "scenarios": [s.name for s in scenario_list],
        "progress": f"0/{len(scenario_list)}",
        "created_at": datetime.utcnow().isoformat(),
        "current_scenario": None,
        "current_turn": 0,
        "current_max_turns": 0,
        "final_score": None,
        "session_logs": [],
    }

    asyncio.create_task(
        _run_suite_background(
            job_id=job_id,
            target_url=req.target_url,
            api_key=req.api_key,
            scenarios=scenario_list,
            code_quality_score=req.code_quality_score,
        )
    )

    return {"job_id": job_id, "status": "queued"}


@app.get("/api/scenarios")
async def list_scenarios() -> dict:
    """List all available built-in scenarios and suite definitions."""
    return {
        "scenarios": [
            {
                "id": s.id,
                "name": s.name,
                "scam_type": s.scam_type,
                "weight": s.weight,
                "max_turns": s.max_turns,
                "fake_data_count": s.fake_data.total_fields(),
                "initial_message_preview": s.initial_message[:100] + "…",
            }
            for s in SCENARIO_REGISTRY.values()
        ],
        "official_suite": DEFAULT_SUITE,
        "extended_suite": EXTENDED_SUITE,
    }


@app.post("/api/run/suite")
async def run_suite(req: RunSuiteRequest) -> dict:
    """Start a full evaluation suite (async – returns job ID)."""
    scenario_list = []
    for sid in req.scenario_ids:
        if sid not in SCENARIO_REGISTRY:
            raise HTTPException(400, f"Unknown scenario ID: {sid}")
        scenario_list.append(SCENARIO_REGISTRY[sid])

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "queued",
        "job_id": job_id,
        "target_url": req.target_url,
        "scenario_count": len(scenario_list),
        "progress": f"0/{len(scenario_list)}",
        "created_at": datetime.utcnow().isoformat(),
        "current_scenario": None,
        "final_score": None,
        "session_logs": [],
    }

    asyncio.create_task(
        _run_suite_background(
            job_id=job_id,
            target_url=req.target_url,
            api_key=req.api_key,
            scenarios=scenario_list,
            code_quality_score=req.code_quality_score,
        )
    )

    return {"job_id": job_id, "status": "queued"}


@app.post("/api/run/single")
async def run_single(req: RunSingleRequest) -> dict:
    """Run a single scenario synchronously (blocks until complete)."""
    if req.scenario_id not in SCENARIO_REGISTRY:
        raise HTTPException(400, f"Unknown scenario ID: {req.scenario_id}")

    scenario = SCENARIO_REGISTRY[req.scenario_id]
    runner = _get_runner(req.target_url, req.api_key)
    evaluator = Evaluator()
    session_id = str(uuid.uuid4())

    history, final_output, elapsed = await runner.run(scenario=scenario, session_id=session_id)
    score = evaluator.score(scenario, history, final_output, elapsed)

    return {
        "session_id": session_id,
        "scenario": scenario.name,
        "score": _score_to_dict(score),
        "conversation_history": history,
        "final_output": final_output,
        "elapsed_seconds": round(elapsed, 2),
    }


@app.post("/api/run/custom")
async def run_custom(req: CustomScenarioRequest) -> dict:
    """Run a fully custom scenario defined in the request."""
    scenario = Scenario(
        id=f"custom_{uuid.uuid4().hex[:8]}",
        name=req.name,
        scam_type=req.scam_type,
        weight=req.weight,
        initial_message=req.initial_message,
        max_turns=req.max_turns,
        metadata=req.metadata,
        persona_context=req.persona_context,
        fake_data=FakeData(
            phone_numbers=req.phone_numbers,
            bank_accounts=req.bank_accounts,
            upi_ids=req.upi_ids,
            phishing_links=req.phishing_links,
            email_addresses=req.email_addresses,
            case_ids=req.case_ids,
            policy_numbers=req.policy_numbers,
            order_numbers=req.order_numbers,
        ),
    )

    runner = _get_runner(req.target_url, req.api_key)
    evaluator = Evaluator()
    session_id = str(uuid.uuid4())

    history, final_output, elapsed = await runner.run(scenario=scenario, session_id=session_id)
    score = evaluator.score(scenario, history, final_output, elapsed)

    return {
        "session_id": session_id,
        "scenario": scenario.name,
        "score": _score_to_dict(score),
        "conversation_history": history,
        "final_output": final_output,
        "elapsed_seconds": round(elapsed, 2),
    }


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    """Poll job status and results."""
    if job_id not in _jobs:
        raise HTTPException(404, f"Job {job_id} not found")
    return _jobs[job_id]


@app.get("/api/jobs")
async def list_jobs() -> dict:
    """List all jobs (summary only)."""
    return {
        "jobs": [
            {
                "job_id": j["job_id"],
                "status": j["status"],
                "target_url": j["target_url"],
                "created_at": j["created_at"],
                "final_score": j.get("final_score", {}).get("final_score"),
            }
            for j in _jobs.values()
        ]
    }


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str) -> dict:
    """Remove a job from memory."""
    if job_id not in _jobs:
        raise HTTPException(404, f"Job {job_id} not found")
    del _jobs[job_id]
    return {"deleted": job_id}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}
