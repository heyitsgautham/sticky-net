"""Scam detection module with pure AI classification."""

from src.detection.detector import ScamDetector, DetectionResult
from src.detection.classifier import ScamClassifier, ClassificationResult, ScamType

__all__ = [
    "ScamDetector",
    "DetectionResult",
    "ScamClassifier",
    "ClassificationResult",
    "ScamType",
]
