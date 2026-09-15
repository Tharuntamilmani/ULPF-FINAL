"""SSRF Protection and Network Guardrails for ULPF M4."""

import ipaddress
import socket
from urllib.parse import urlparse

from app.errors.exceptions import SSRFViolationError

# Blocked IP networks
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),  # Current network
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # Private RFC1918
    ipaddress.ip_network("172.16.0.0/12"),  # Private RFC1918
    ipaddress.ip_network("192.168.0.0/16"),  # Private RFC1918
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / Cloud Metadata
    ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),  # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("198.18.0.0/15"),  # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved for future use
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
    # IPv6
    ipaddress.ip_network("::/128"),  # Unspecified
    ipaddress.ip_network("::1/128"),  # Loopback
    ipaddress.ip_network("fc00::/7"),  # Unique local
    ipaddress.ip_network("fe80::/10"),  # Link-local
    ipaddress.ip_network("ff00::/8"),  # Multicast
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
}


class SSRFGuard:
    """Validates URLs and endpoints to prevent Server-Side Request Forgery."""

    def __init__(
        self,
        allowed_domains: set[str] | None = None,
        allow_http: bool = False,
    ) -> None:
        self.allowed_domains = {d.lower() for d in (allowed_domains or set())}
        self.allow_http = allow_http

    def is_ip_blocked(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if an IP address belongs to any blocked/private/reserved range."""
        return any(ip in net for net in BLOCKED_NETWORKS)

    def validate_url(self, url: str) -> str:
        """Validate target URL against scheme, domain allowlist, and IP address boundaries.

        Raises SSRFViolationError on any violation.
        """
        if not url or not url.strip():
            raise SSRFViolationError("URL cannot be empty")

        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        if scheme not in ("http", "https"):
            raise SSRFViolationError(f"Unsupported URL scheme: {scheme}")

        if scheme == "http" and not self.allow_http:
            raise SSRFViolationError("Insecure HTTP scheme is disallowed; HTTPS required")

        hostname = parsed.hostname
        if not hostname:
            raise SSRFViolationError("URL is missing a valid hostname")

        hostname_lower = hostname.lower().strip()

        # Check explicit blocked hostnames
        if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".internal"):
            raise SSRFViolationError(f"Target hostname is blocked by SSRF policy: {hostname}")

        # Check domain allowlist if configured
        if self.allowed_domains:
            matched = False
            for allowed in self.allowed_domains:
                if hostname_lower == allowed or hostname_lower.endswith("." + allowed):
                    matched = True
                    break
            if not matched:
                raise SSRFViolationError(
                    f"Target hostname '{hostname}' is not in allowed domain list"
                )

        # Resolve IP addresses and verify against blocked ranges
        try:
            # Check if hostname itself is already an IP address
            direct_ip = ipaddress.ip_address(hostname_lower)
            if self.is_ip_blocked(direct_ip):
                raise SSRFViolationError(f"Target IP {direct_ip} is in a blocked/private range")
            return url
        except ValueError:
            # Hostname is not an IP string, proceed to DNS resolution
            pass

        try:
            addr_info = socket.getaddrinfo(hostname_lower, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                if self.is_ip_blocked(ip_obj):
                    raise SSRFViolationError(
                        f"Resolved IP {ip_obj} for host '{hostname}' is in a blocked/private range"
                    )
        except socket.gaierror as e:
            raise SSRFViolationError(f"DNS resolution failed for hostname '{hostname}': {e}") from e

        return url
