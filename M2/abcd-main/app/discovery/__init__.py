from app.discovery.profiler import EventProfiler
from app.discovery.field_detector import FieldDetector
from app.discovery.suggestion import MappingSuggester
from app.discovery.confidence import DiscoveryConfidenceCalculator


class UnknownSourceDiscoveryEngine:
    """Unified Unknown-Source Discovery Engine for M2."""

    def __init__(self):
        self.profiler = EventProfiler()
        self.field_detector = FieldDetector()
        self.suggester = MappingSuggester()
        self.confidence_calc = DiscoveryConfidenceCalculator()

    def discover(self, payload: str) -> dict:
        profile = self.profiler.profile(payload)
        fmt = profile["format"]
        detected_fields = self.field_detector.detect_fields(payload, fmt)
        suggestions = self.suggester.suggest_mappings(detected_fields)
        confidence = self.confidence_calc.calculate_confidence(
            fmt, detected_fields, suggestions
        )

        return {
            "discovery": {
                "format": fmt,
                "confidence": confidence,
                "is_structured": profile["is_structured"],
            },
            "detected_fields": detected_fields,
            "suggestions": suggestions,
        }


__all__ = [
    "EventProfiler",
    "FieldDetector",
    "MappingSuggester",
    "DiscoveryConfidenceCalculator",
    "UnknownSourceDiscoveryEngine",
]
