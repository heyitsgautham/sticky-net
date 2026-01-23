"""Scam detection module with hybrid regex + AI approach."""

from src.detection.detector import ScamDetector, DetectionResult
from src.detection.classifier import ScamClassifier, ClassificationResult
from src.detection.patterns import (
    ScamCategory,
    Pattern,
    PatternMatch,
    PreFilterResult,
    pre_filter,
    match_all_patterns,
)

__all__ = [
    "ScamDetector",
    "DetectionResult",
    "ScamClassifier",
    "ClassificationResult",
    "ScamCategory",
    "Pattern",
    "PatternMatch",
    "PreFilterResult",
    "pre_filter",
    "match_all_patterns",
]
