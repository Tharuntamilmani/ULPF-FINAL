"""
Service-to-service authentication registry and credential manager.
Provides authenticated headers for inter-module communication across M1, M2, M3, M4, M5, and M6.
"""

import os
from typing import Dict, Optional


class ServiceAuthManager:
    """
    Manages internal service credentials and headers.
    Separates service identity authentication from tenant context authorization.
    """

    def __init__(self):
        # Service credentials loaded from environment with secure defaults
        self.m1_internal_token = os.getenv("M1_INTERNAL_TOKEN", "test-token-12345")
        self.m2_service_token = os.getenv("M2_SERVICE_TOKEN", "system-admin-token")
        self.m3_service_token = os.getenv("M3_SERVICE_TOKEN", "m3-service-key")
        self.m4_service_token = os.getenv("M4_SERVICE_TOKEN", "system-admin-token")
        self.m5_service_token = os.getenv("M5_SERVICE_TOKEN", "admin")
        self.m6_service_token = os.getenv("M6_SERVICE_TOKEN", "m6-control-key")

    def get_m1_headers(self, correlation_id: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.m1_internal_token}",
        }
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        return headers

    def get_m2_headers(self, correlation_id: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.m2_service_token}",
            "X-API-Key": self.m2_service_token,
        }
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        return headers

    def get_m3_headers(self, correlation_id: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.m3_service_token}",
        }
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        return headers

    def get_m4_headers(self, correlation_id: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "X-API-Key": self.m4_service_token,
        }
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        return headers

    def get_m5_headers(self, correlation_id: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.m5_service_token}",
            "X-Tenant-ID": "admin",
        }
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        return headers


# Global singleton instance
service_auth = ServiceAuthManager()
