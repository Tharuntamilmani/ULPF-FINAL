import re
import concurrent.futures
from typing import Dict, Any, List, Optional
from app.engine.base import BaseParser

# ReDoS Safeguard: Detect nested quantifiers or dangerous patterns e.g. (a+)+ or (a*)*
DANGEROUS_REGEX_PATTERNS = [
    re.compile(r"\((?:[^\)]+[*+])\)[*+]"),
    re.compile(r"\((?:[^\)]+\|[^\)]+)\)[*+]"),
]


def is_safe_regex(pattern: str) -> bool:
    """Check regex pattern against catastrophic backtracking / ReDoS signatures."""
    for dangerous in DANGEROUS_REGEX_PATTERNS:
        if dangerous.search(pattern):
            return False
    return True


class SafeRegexParser(BaseParser):
    """
    Regex-backed Parser with ReDoS safeguards, worker timeout, and payload limits.
    """

    parser_id = "parser-safe-regex"
    name = "Safe Regex Parser"
    version = "1.0.0"

    def __init__(
        self,
        parser_id: str,
        name: str,
        version: str,
        patterns: List[str],
        fields_map: Optional[Dict[str, str]] = None,
        max_payload_bytes: int = 100000,
        timeout_seconds: float = 0.5,
    ):
        self.parser_id = parser_id
        self.name = name
        self.version = version
        self.max_payload_bytes = max_payload_bytes
        self.timeout_seconds = timeout_seconds
        self.fields_map = fields_map or {}

        self.compiled_patterns = []
        for pat in patterns:
            if not is_safe_regex(pat):
                raise ValueError(
                    f"Potentially unsafe ReDoS regex pattern detected: {pat}"
                )
            self.compiled_patterns.append(re.compile(pat, re.DOTALL))

    def can_parse(self, event: Dict[str, Any]) -> bool:
        payload = event.get("payload", "")
        if len(payload.encode("utf-8")) > self.max_payload_bytes:
            return False

        for pat in self.compiled_patterns:
            if pat.search(payload):
                return True
        return False

    def _execute_match(self, payload: str) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}
        for pat in self.compiled_patterns:
            match = pat.search(payload)
            if match:
                groupdict = match.groupdict()
                for k, v in groupdict.items():
                    if v is not None:
                        # Map to field name if specified in fields_map
                        target_key = self.fields_map.get(k, k)
                        # Type conversion
                        if isinstance(v, str) and v.isdigit():
                            extracted[target_key] = int(v)
                        else:
                            extracted[target_key] = v
                break
        return extracted

    def parse(self, event: Dict[str, Any]) -> Dict[str, Any]:
        payload = event.get("payload", "")
        if len(payload.encode("utf-8")) > self.max_payload_bytes:
            raise ValueError(
                f"Payload size exceeds maximum allowed bytes ({self.max_payload_bytes})"
            )

        # Execute match with worker thread timeout protection
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._execute_match, payload)
            try:
                return future.result(timeout=self.timeout_seconds)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(
                    f"Parser execution exceeded timeout limit of {self.timeout_seconds}s"
                )
