"""Security tests for SSRF protection and network guardrails."""

import pytest

from app.errors.exceptions import SSRFViolationError
from app.security.ssrf_guard import SSRFGuard


def test_ssrf_blocks_localhost() -> None:
    """Ensure localhost and 127.0.0.1 are blocked."""
    guard = SSRFGuard()
    with pytest.raises(SSRFViolationError, match="blocked by SSRF policy|blocked/private range"):
        guard.validate_url("https://localhost/lookup")
    with pytest.raises(SSRFViolationError, match="blocked/private range"):
        guard.validate_url("https://127.0.0.1/lookup")


def test_ssrf_blocks_ipv6_loopback() -> None:
    """Ensure [::1] loopback is blocked."""
    guard = SSRFGuard()
    with pytest.raises(SSRFViolationError, match="blocked/private range"):
        guard.validate_url("https://[::1]/lookup")


def test_ssrf_blocks_rfc1918_private_ips() -> None:
    """Ensure RFC1918 private subnets are blocked."""
    guard = SSRFGuard()
    # 10.0.0.0/8
    with pytest.raises(SSRFViolationError, match="blocked/private range"):
        guard.validate_url("https://10.0.50.1/api")
    # 172.16.0.0/12
    with pytest.raises(SSRFViolationError, match="blocked/private range"):
        guard.validate_url("https://172.20.10.5/api")
    # 192.168.0.0/16
    with pytest.raises(SSRFViolationError, match="blocked/private range"):
        guard.validate_url("https://192.168.1.1/api")


def test_ssrf_blocks_cloud_metadata_endpoints() -> None:
    """Ensure AWS/GCP/Azure link-local metadata endpoints are strictly blocked."""
    guard = SSRFGuard()
    # AWS / Azure / GCP link-local IP
    with pytest.raises(SSRFViolationError, match="blocked/private range"):
        guard.validate_url("https://169.254.169.254/latest/meta-data")
    # GCP hostname
    with pytest.raises(SSRFViolationError, match="blocked by SSRF policy"):
        guard.validate_url("https://metadata.google.internal/computeMetadata/v1")


def test_ssrf_blocks_carrier_grade_nat() -> None:
    """Ensure RFC6598 carrier grade NAT (100.64.0.0/10) is blocked."""
    guard = SSRFGuard()
    with pytest.raises(SSRFViolationError, match="blocked/private range"):
        guard.validate_url("https://100.64.1.1/api")


def test_ssrf_blocks_non_http_schemes() -> None:
    """Ensure non-HTTP schemes like file://, gopher://, ftp:// are rejected."""
    guard = SSRFGuard()
    with pytest.raises(SSRFViolationError, match="Unsupported URL scheme"):
        guard.validate_url("file:///etc/passwd")
    with pytest.raises(SSRFViolationError, match="Unsupported URL scheme"):
        guard.validate_url("gopher://127.0.0.1:70")
    with pytest.raises(SSRFViolationError, match="Unsupported URL scheme"):
        guard.validate_url("ftp://ftp.example.com")


def test_ssrf_rejects_plain_http_unless_explicitly_allowed() -> None:
    """Ensure plain HTTP is rejected by default."""
    guard = SSRFGuard(allow_http=False)
    with pytest.raises(SSRFViolationError, match="Insecure HTTP scheme is disallowed"):
        guard.validate_url("http://api.example.com")


def test_ssrf_enforces_domain_allowlist() -> None:
    """Ensure requests to unlisted domains are blocked when allowlist is active."""
    guard = SSRFGuard(allowed_domains={"trusted-api.com", "partner.org"})
    with pytest.raises(SSRFViolationError, match="not in allowed domain list"):
        guard.validate_url("https://untrusted-attacker.com/v1/enrich")


def test_ssrf_empty_or_malformed_urls() -> None:
    """Ensure empty or malformed URLs raise SSRFViolationError."""
    guard = SSRFGuard()
    with pytest.raises(SSRFViolationError, match="URL cannot be empty"):
        guard.validate_url("")
    with pytest.raises(SSRFViolationError, match="missing a valid hostname"):
        guard.validate_url("https:///path-only")
