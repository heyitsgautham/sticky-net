"""Hybrid scam detection: regex pre-filter + AI classification."""

from dataclasses import dataclass, field
from typing import Any

import structlog

from src.api.schemas import ConversationMessage, Metadata
from src.detection.patterns import (
    ScamCategory,
    PatternMatch,
    PreFilterResult,
    match_all_patterns,
    pre_filter,
)
from src.detection.classifier import ScamClassifier, ClassificationResult

logger = structlog.get_logger()


@dataclass
class DetectionResult:
    """Result of hybrid scam detection."""
    is_scam: bool
    confidence: float  # 0.0 to 1.0
    scam_type: str | None = None
    matched_patterns: list[PatternMatch] = field(default_factory=list)
    category_scores: dict[ScamCategory, float] = field(default_factory=dict)
    reasoning: str = ""
    detection_method: str = "hybrid"  # "regex_fast_path" | "ai_classification" | "hybrid"


class ScamDetector:
    """Hybrid scam detector combining regex pre-filter with AI classification."""

    SCAM_THRESHOLD = 0.6
    OBVIOUS_SCAM_CONFIDENCE = 0.95
    OBVIOUS_SAFE_CONFIDENCE = 0.05

    def __init__(self) -> None:
        self.logger = logger.bind(component="ScamDetector")
        self.classifier = ScamClassifier()

    async def analyze(
        self,
        message: str,
        history: list[ConversationMessage] | None = None,
        metadata: Metadata | None = None,
        previous_result: DetectionResult | None = None,
    ) -> DetectionResult:
        """
        Analyze a message using hybrid approach:
        1. Regex pre-filter for fast path (obvious scam/safe)
        2. AI classification for uncertain cases
        3. Combine confidence from patterns and AI
        """
        self.logger.info("Analyzing message", message_length=len(message))

        # Step 1: Regex pre-filter
        pre_filter_result = pre_filter(message)
        pattern_matches = match_all_patterns(message)
        
        if pre_filter_result == PreFilterResult.OBVIOUS_SCAM:
            self.logger.info("Obvious scam detected via regex fast path")
            return self._build_result(
                is_scam=True,
                confidence=self.OBVIOUS_SCAM_CONFIDENCE,
                matches=pattern_matches,
                reasoning="Obvious scam pattern detected (fast path)",
                method="regex_fast_path",
            )
        
        if pre_filter_result == PreFilterResult.OBVIOUS_SAFE:
            self.logger.info("Obvious safe message detected via regex fast path")
            return self._build_result(
                is_scam=False,
                confidence=self.OBVIOUS_SAFE_CONFIDENCE,
                matches=pattern_matches,
                reasoning="Legitimate message pattern detected (fast path)",
                method="regex_fast_path",
            )
        
        # Step 2: AI classification for uncertain
        self.logger.info("Uncertain message, using AI classification")
        
        prev_classification = None
        if previous_result:
            prev_classification = ClassificationResult(
                is_scam=previous_result.is_scam,
                confidence=previous_result.confidence,
                scam_type=previous_result.scam_type,
            )
        
        ai_result = await self.classifier.classify(
            message=message,
            history=history,
            metadata=metadata,
            previous_classification=prev_classification,
        )
        
        # Step 3: Combine confidence
        final_confidence = self._combine_confidence(
            ai_confidence=ai_result.confidence,
            pattern_matches=pattern_matches,
            previous_confidence=previous_result.confidence if previous_result else None,
        )
        
        return self._build_result(
            is_scam=final_confidence >= self.SCAM_THRESHOLD,
            confidence=final_confidence,
            matches=pattern_matches,
            reasoning=ai_result.reasoning,
            method="ai_classification",
            scam_type=ai_result.scam_type,
        )
    
    def _combine_confidence(
        self,
        ai_confidence: float,
        pattern_matches: list[PatternMatch],
        previous_confidence: float | None,
    ) -> float:
        confidence = ai_confidence
        
        # Boost based on pattern matches
        if pattern_matches:
            pattern_boost = min(0.15, len(pattern_matches) * 0.03)
            confidence = min(1.0, confidence + pattern_boost)
        
        # KEY: Confidence can only INCREASE (prevents false negative oscillation)
        if previous_confidence is not None:
            confidence = max(confidence, previous_confidence)
        
        return confidence
    
    def _build_result(
        self,
        is_scam: bool,
        confidence: float,
        matches: list[PatternMatch],
        reasoning: str,
        method: str,
        scam_type: str | None = None,
    ) -> DetectionResult:
        category_scores = self._calculate_category_scores(matches)
        return DetectionResult(
            is_scam=is_scam,
            confidence=confidence,
            scam_type=scam_type,
            matched_patterns=matches,
            category_scores=category_scores,
            reasoning=reasoning,
            detection_method=method,
        )
    
    def _calculate_category_scores(
        self, matches: list[PatternMatch]
    ) -> dict[ScamCategory, float]:
        scores: dict[ScamCategory, list[float]] = {cat: [] for cat in ScamCategory}
        for match in matches:
            scores[match.category].append(match.weight)
        return {
            cat: min(1.0, sum(weights) / max(1, len(weights)) if weights else 0.0)
            for cat, weights in scores.items()
        }