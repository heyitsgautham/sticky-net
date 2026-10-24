"""Scam detection module with pure AI classification."""

from src.detection.classifier import ClassificationResult, ScamClassifier, ScamType
from src.detection.detector import DetectionResult, ScamDetector

__all__ = [
    "ScamDetector",
    "DetectionResult",
    "ScamClassifier",
    "ClassificationResult",
    "ScamType",
]
