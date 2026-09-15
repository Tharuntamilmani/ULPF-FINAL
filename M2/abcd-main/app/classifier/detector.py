from app.models.envelope import RawEventEnvelope
from app.models.parsed_event import ClassificationResult
from app.classifier.format_detector import FormatDetector
from app.classifier.source_detector import SourceDetector


class Classifier:
    """
    Unified 3-stage Format and Source Classifier.
    Stage 1: Cheap deterministic format detection
    Stage 2: Source/vendor detection via heuristics and patterns
    Stage 3: Confidence score math aggregation
    """

    def __init__(self):
        self.format_detector = FormatDetector()
        self.source_detector = SourceDetector()

    def classify(self, envelope_or_payload) -> ClassificationResult:
        if isinstance(envelope_or_payload, RawEventEnvelope):
            payload = envelope_or_payload.payload
        elif isinstance(envelope_or_payload, str):
            payload = envelope_or_payload
        else:
            payload = str(envelope_or_payload)

        # Stage 1
        format_type = self.format_detector.detect_format(payload)
        format_confidence = (
            0.95
            if format_type in ["json", "cef", "leef", "xml"]
            else (0.85 if format_type in ["syslog", "kv", "csv"] else 0.5)
        )

        # Stage 2
        vendor, product, source_confidence = self.source_detector.detect_source(
            payload, format_type
        )

        # Stage 3 - Combined Confidence Math
        if vendor != "Unknown":
            total_confidence = round(
                0.4 * format_confidence + 0.6 * source_confidence, 2
            )
        else:
            total_confidence = round(format_confidence * 0.8, 2)

        return ClassificationResult(
            format=format_type,
            vendor=vendor,
            product=product,
            confidence=total_confidence,
        )
