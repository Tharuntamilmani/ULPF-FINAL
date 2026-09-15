"""Deterministic Local Threat Intelligence Provider for ULPF M4."""

from typing import Any

from app.contracts.canonical_event import CanonicalEvent
from app.models.common import EnrichmentStatus
from app.providers.base import EnrichmentContext, EnrichmentProvider, ProviderOutput

# Deterministic IOC indicator database
INDICATOR_DATABASE: dict[str, dict[str, Any]] = {
    "198.51.100.99": {
        "indicator": "198.51.100.99",
        "type": "ipv4",
        "verdict": "malicious",
        "threat_types": ["c2", "botnet"],
        "severity": "high",
        "confidence": 0.95,
        "campaign": "CobaltStrike-2026",
        "actor": "APT-Mock-29",
    },
    "203.0.113.55": {
        "indicator": "203.0.113.55",
        "type": "ipv4",
        "verdict": "suspicious",
        "threat_types": ["scanner"],
        "severity": "medium",
        "confidence": 0.75,
        "campaign": "MassScan-Probe",
        "actor": "Unknown",
    },
    "evil-payload.example.com": {
        "indicator": "evil-payload.example.com",
        "type": "domain",
        "verdict": "malicious",
        "threat_types": ["malware_distribution"],
        "severity": "critical",
        "confidence": 0.98,
        "campaign": "Emotet-Resurgence",
        "actor": "TA542",
    },
    "phishing-login.example.org": {
        "indicator": "phishing-login.example.org",
        "type": "domain",
        "verdict": "malicious",
        "threat_types": ["credential_harvesting"],
        "severity": "high",
        "confidence": 0.90,
        "campaign": "O365-Phish",
        "actor": "Unknown",
    },
}


class LocalThreatIntelProvider(EnrichmentProvider):
    """Enriches canonical events with threat intelligence indicator intelligence."""

    def __init__(
        self,
        provider_id: str = "threat-intel-local",
        provider_version: str = "1.0.0",
        priority: int = 10,
        timeout_seconds: float = 0.5,
        custom_indicators: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            provider_id=provider_id,
            provider_version=provider_version,
            target_namespace="threat_intel",
            priority=priority,
            timeout_seconds=timeout_seconds,
            is_tenant_sensitive=False,
        )
        self._indicators = (
            custom_indicators if custom_indicators is not None else INDICATOR_DATABASE
        )

    def can_enrich(self, event: CanonicalEvent, context: EnrichmentContext) -> bool:
        return bool(
            (event.destination and (event.destination.ip or event.destination.domain))
            or (event.source and event.source.ip)
        )

    def enrich(self, event: CanonicalEvent, context: EnrichmentContext) -> ProviderOutput:
        # Collect candidate indicators
        candidates: list[str] = []
        if event.destination and event.destination.domain:
            candidates.append(event.destination.domain.lower().strip())
        if event.destination and event.destination.ip:
            candidates.append(event.destination.ip.strip())
        if event.source and event.source.ip:
            candidates.append(event.source.ip.strip())

        matched_indicators: list[dict[str, Any]] = []
        overall_verdict = "clean"
        max_confidence = 0.0

        for cand in candidates:
            if cand in self._indicators:
                record = self._indicators[cand]
                matched_indicators.append(record)
                if record.get("verdict") == "malicious":
                    overall_verdict = "malicious"
                elif record.get("verdict") == "suspicious" and overall_verdict != "malicious":
                    overall_verdict = "suspicious"

                conf = float(record.get("confidence", 0.5))
                if conf > max_confidence:
                    max_confidence = conf

        if matched_indicators:
            return ProviderOutput(
                status=EnrichmentStatus.SUCCESS,
                data={
                    "verdict": overall_verdict,
                    "matched_count": len(matched_indicators),
                    "indicators": matched_indicators,
                },
                confidence=max_confidence,
                source_reference=f"ti-feed://v{self.provider_version}",
            )

        return ProviderOutput(
            status=EnrichmentStatus.NOT_FOUND,
            confidence=0.0,
            error_message="No matching threat indicators detected",
        )
