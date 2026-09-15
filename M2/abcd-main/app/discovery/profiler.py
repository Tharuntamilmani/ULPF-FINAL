from typing import Dict, Any
from app.classifier.format_detector import FormatDetector


class EventProfiler:
    """Profiles raw event payloads to determine generic structure and format metadata."""

    def __init__(self):
        self.format_detector = FormatDetector()

    def profile(self, payload: str) -> Dict[str, Any]:
        fmt = self.format_detector.detect_format(payload)
        length = len(payload)
        lines = payload.count("\n") + 1

        return {
            "format": fmt,
            "payload_length": length,
            "line_count": lines,
            "is_structured": fmt in ["json", "cef", "leef", "kv", "xml", "csv"],
        }
