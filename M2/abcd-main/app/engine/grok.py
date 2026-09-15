import re
import concurrent.futures
from typing import Dict, Any, List, Optional
from app.engine.base import BaseParser
from app.engine.regex import is_safe_regex

# Common Grok pattern library definitions
COMMON_PATTERNS = {
    "USERNAME": r"[a-zA-Z0-9._-]+",
    "USER": r"%{USERNAME}",
    "INT": r"(?:[+-]?(?:[0-9]+))",
    "BASE10NUM": r"(?<![0-9.+-])(?>[+-]?(?:(?:[0-9]+(?:\.[0-9]+)?)|(?:\.[0-9]+)))",
    "NUMBER": r"(?:%{BASE10NUM})",
    "POSINT": r"\b(?:[1-9][0-9]*)\b",
    "WORD": r"\b\w+\b",
    "WORD_OR_EMPTY": r"\w*",
    "NOTSPACE": r"\S+",
    "SPACE": r"\s*",
    "DATA": r".*?",
    "GREEDYDATA": r".*",
    "IPV4": r"(?<![0-9])(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?![0-9])",
    "IPV6": r"((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))",
    "IP": r"(?:%{IPV4}|%{IPV6})",
    "SYSLOGTIMESTAMP": r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(?:(?:[0-9])|(?:[0-9][0-9]))\s+(?:(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9])",
    "PROG": r"[\w\._/%-]+",
    "SYSLOGBASE": r"^(?:<(?P<syslog_pri>\d{1,3})>)?(?P<timestamp>%{SYSLOGTIMESTAMP})\s+(?P<logsource>%{NOTSPACE})\s+(?P<program>%{PROG})(?:\[(?P<pid>%{POSINT})\])?:\s*",
    "CISCO_ASA_HEADER": r"%{SYSLOGBASE}%ASA-(?P<facility>\d+)-(?P<message_id>\d+):\s*",
}

try:
    import pygrok  # noqa: F401

    PYGROK_AVAILABLE = True
except ImportError:
    PYGROK_AVAILABLE = False


def grok_to_regex(
    grok_pattern: str, custom_patterns: Optional[Dict[str, str]] = None
) -> str:
    """Converts a Grok pattern string like '%{IP:srcip}' to standard named-group regex."""
    patterns = dict(COMMON_PATTERNS)
    if custom_patterns:
        patterns.update(custom_patterns)

    # Iteratively expand pattern references up to 5 levels deep
    res = grok_pattern
    for _ in range(5):

        def replancer(match):
            name = match.group(1)
            field = match.group(2)
            sub_pat = patterns.get(name, r"\S+")
            if field:
                return f"(?P<{field}>{sub_pat})"
            else:
                return f"(?:{sub_pat})"

        res_next = re.sub(r"%\{([A-Z0-9_]+)(?::([A-Za-z0-9_]+))?\}", replancer, res)
        if res_next == res:
            break
        res = res_next

    return res


class GrokParser(BaseParser):
    """
    Grok pattern parsing engine with ReDoS safeguards, bounded execution, and payload limits.
    """

    parser_id = "parser-grok"
    name = "Grok Pattern Parser"
    version = "1.0.0"

    def __init__(
        self,
        parser_id: str,
        name: str,
        version: str,
        patterns: List[str],
        custom_patterns: Optional[Dict[str, str]] = None,
        fields_map: Optional[Dict[str, str]] = None,
        max_payload_bytes: int = 100_000,
        timeout_seconds: float = 0.5,
    ):
        self.parser_id = parser_id
        self.name = name
        self.version = version
        self.fields_map = fields_map or {}
        self.max_payload_bytes = max_payload_bytes
        self.timeout_seconds = timeout_seconds
        self.compiled_regexes: List[re.Pattern] = []

        combined_patterns = dict(COMMON_PATTERNS)
        if custom_patterns:
            combined_patterns.update(custom_patterns)

        for pat in patterns:
            if not is_safe_regex(pat):
                raise ValueError(
                    f"Potentially unsafe ReDoS regex pattern detected in Grok definition: {pat}"
                )
            regex_str = grok_to_regex(pat, combined_patterns)
            if not is_safe_regex(regex_str):
                raise ValueError(
                    f"Transpiled Grok regex is potentially vulnerable to ReDoS: {regex_str}"
                )
            self.compiled_regexes.append(re.compile(regex_str))

    def can_parse(self, event: Dict[str, Any]) -> bool:
        payload = event.get("payload", "")
        if not payload:
            return False
        # Reject payload if it exceeds maximum allowed size
        if len(payload.encode("utf-8", errors="replace")) > self.max_payload_bytes:
            return False

        for reg in self.compiled_regexes:
            if reg.search(payload):
                return True
        return False

    def _execute_match(self, payload: str) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}
        for reg in self.compiled_regexes:
            match = reg.search(payload)
            if match:
                for k, v in match.groupdict().items():
                    if v is not None:
                        target_key = self.fields_map.get(k, k)
                        if isinstance(v, str) and v.isdigit():
                            extracted[target_key] = int(v)
                        else:
                            extracted[target_key] = v
                break
        return extracted

    def parse(self, event: Dict[str, Any]) -> Dict[str, Any]:
        payload = event.get("payload", "")
        payload_bytes = len(payload.encode("utf-8", errors="replace"))
        if payload_bytes > self.max_payload_bytes:
            raise ValueError(
                f"Payload size {payload_bytes} bytes exceeds maximum allowed {self.max_payload_bytes} bytes"
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._execute_match, payload)
            try:
                return future.result(timeout=self.timeout_seconds)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(
                    f"GrokParser execution exceeded timeout limit of {self.timeout_seconds}s"
                )
