"""Deterministic Local GeoIP and ASN Enrichment Provider for ULPF M4."""

import ipaddress
from typing import Any

from app.contracts.canonical_event import CanonicalEvent
from app.models.common import EnrichmentStatus
from app.providers.base import EnrichmentContext, EnrichmentProvider, ProviderOutput

# Deterministic CIDR-based GeoIP / ASN records
GEOIP_ASN_DATABASE: list[tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, dict[str, Any]]] = [
    (
        ipaddress.ip_network("8.8.8.0/24"),
        {
            "country_code": "US",
            "country_name": "United States",
            "region": "CA",
            "city": "Mountain View",
            "latitude": 37.4223,
            "longitude": -122.0848,
            "asn": {
                "number": 15169,
                "organization": "Google LLC",
            },
        },
    ),
    (
        ipaddress.ip_network("1.1.1.0/24"),
        {
            "country_code": "AU",
            "country_name": "Australia",
            "region": "QLD",
            "city": "South Brisbane",
            "latitude": -27.4766,
            "longitude": 153.0166,
            "asn": {
                "number": 13335,
                "organization": "Cloudflare Inc",
            },
        },
    ),
    (
        ipaddress.ip_network("93.184.216.0/24"),
        {
            "country_code": "US",
            "country_name": "United States",
            "region": "MA",
            "city": "Norwell",
            "latitude": 42.1508,
            "longitude": -70.7928,
            "asn": {
                "number": 15133,
                "organization": "Edgecast Inc",
            },
        },
    ),
    (
        ipaddress.ip_network("185.199.108.0/22"),
        {
            "country_code": "US",
            "country_name": "United States",
            "region": "CA",
            "city": "San Francisco",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "asn": {
                "number": 36459,
                "organization": "GitHub Inc",
            },
        },
    ),
    (
        ipaddress.ip_network("198.51.100.0/24"),
        {
            "country_code": "CH",
            "country_name": "Switzerland",
            "region": "GE",
            "city": "Geneva",
            "latitude": 46.2044,
            "longitude": 6.1432,
            "asn": {
                "number": 64496,
                "organization": "Example Autonomous System",
            },
        },
    ),
]


class LocalGeoIPProvider(EnrichmentProvider):
    """Enriches canonical events with geographic and autonomous system (ASN) metadata."""

    def __init__(
        self,
        provider_id: str = "geoip-local-db",
        provider_version: str = "1.0.0",
        priority: int = 30,
        timeout_seconds: float = 0.5,
    ) -> None:
        super().__init__(
            provider_id=provider_id,
            provider_version=provider_version,
            target_namespace="geo",
            priority=priority,
            timeout_seconds=timeout_seconds,
            is_tenant_sensitive=False,  # Public geoip is tenant-neutral
        )

    def can_enrich(self, event: CanonicalEvent, context: EnrichmentContext) -> bool:
        return bool(
            (event.source and event.source.ip) or (event.destination and event.destination.ip)
        )

    def enrich(self, event: CanonicalEvent, context: EnrichmentContext) -> ProviderOutput:
        # Check source IP first, fallback to destination IP
        ip_str = None
        if event.source and event.source.ip:
            ip_str = event.source.ip
        elif event.destination and event.destination.ip:
            ip_str = event.destination.ip

        if not ip_str:
            return ProviderOutput(
                status=EnrichmentStatus.SKIPPED,
                error_message="No IP available for GeoIP lookup",
            )

        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return ProviderOutput(
                status=EnrichmentStatus.FAILED,
                error_message=f"Invalid IP address format: {ip_str}",
                error_type="InvalidIPAddress",
            )

        # Handle private / loopback addresses cleanly
        if ip_obj.is_private or ip_obj.is_loopback:
            return ProviderOutput(
                status=EnrichmentStatus.SUCCESS,
                data={
                    "country_code": "PRIVATE",
                    "country_name": "Private Network",
                    "region": "LAN",
                    "city": "Internal",
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "asn": {
                        "number": 0,
                        "organization": "Private Network",
                    },
                },
                confidence=1.0,
                source_reference="iana://rfc1918",
            )

        # Match against CIDR database
        for net, data in GEOIP_ASN_DATABASE:
            if ip_obj in net:
                return ProviderOutput(
                    status=EnrichmentStatus.SUCCESS,
                    data=dict(data),
                    confidence=0.92,
                    source_reference=f"geoip-db://v{self.provider_version}/{net}",
                )

        return ProviderOutput(
            status=EnrichmentStatus.NOT_FOUND,
            confidence=0.0,
            error_message=f"IP {ip_str} not found in GeoIP database",
        )
