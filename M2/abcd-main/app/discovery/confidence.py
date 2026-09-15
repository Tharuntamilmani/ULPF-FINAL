from typing import Dict, Any


class DiscoveryConfidenceCalculator:
    """Calculates confidence score for unknown event structure discovery."""

    @staticmethod
    def calculate_confidence(
        format_type: str, detected_fields: Dict[str, Any], suggestions: Dict[str, str]
    ) -> float:
        if not detected_fields:
            return 0.10

        field_count = len(detected_fields)
        suggested_count = len(suggestions)

        base_score = 0.50 if format_type != "plain_text" else 0.20
        field_score = min(0.30, field_count * 0.05)
        suggestion_score = min(0.20, suggested_count * 0.05)

        total = round(base_score + field_score + suggestion_score, 2)
        return min(0.99, total)
