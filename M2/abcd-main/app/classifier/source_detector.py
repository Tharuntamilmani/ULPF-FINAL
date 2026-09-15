import re
from typing import Tuple, List, cast
from app.classifier.signatures import VENDOR_SIGNATURES


class SourceDetector:
    """Stage 2 — Source/Vendor detection using regex patterns, keywords, and headers."""

    @staticmethod
    def detect_source(
        payload: str, format_type: str = "plain_text"
    ) -> Tuple[str, str, float]:
        """
        Returns (vendor, product, vendor_confidence_score).
        """
        if not payload:
            return ("Unknown", "Unknown", 0.0)

        best_vendor: str = "Unknown"
        best_product: str = "Unknown"
        best_score: float = 0.0

        for candidate in VENDOR_SIGNATURES:
            vendor: str = str(candidate["vendor"])
            product: str = str(candidate["product"])
            patterns: List[re.Pattern] = cast(List[re.Pattern], candidate["patterns"])
            keywords: List[str] = cast(List[str], candidate["keywords"])
            score: float = 0.0

            # Test regex patterns (weight = 0.6)
            for pat in patterns:
                if pat.search(payload):
                    score += 0.6
                    break

            # Test keyword matches (weight = 0.4 split among keywords)
            kw_hits = 0
            for kw in keywords:
                if kw in payload:
                    kw_hits += 1

            if keywords:
                kw_score = min(
                    0.4, (kw_hits / len(keywords)) * 0.6 + (0.2 if kw_hits > 0 else 0.0)
                )
                score += kw_score

            if score > best_score:
                best_score = score
                best_vendor = vendor
                best_product = product

        if best_score < 0.25:
            return ("Unknown", "Unknown", 0.0)

        return (best_vendor, best_product, min(1.0, best_score))
