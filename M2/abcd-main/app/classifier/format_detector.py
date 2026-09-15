import json
import csv
import io
from app.classifier.signatures import (
    JSON_PREFIX,
    SYSLOG_PRI,
    SYSLOG_BSD,
    SYSLOG_ISO,
    CEF_SIGNATURE,
    LEEF_SIGNATURE,
    XML_PREFIX,
    KEY_VALUE_PATTERN,
)


class FormatDetector:
    """Stage 1 — Cheap deterministic format detection."""

    @staticmethod
    def detect_format(payload: str) -> str:
        if not payload or not payload.strip():
            return "plain_text"

        stripped = payload.strip()

        # Check CEF
        if CEF_SIGNATURE.search(stripped):
            return "cef"

        # Check LEEF
        if LEEF_SIGNATURE.search(stripped):
            return "leef"

        # Check JSON
        if JSON_PREFIX.match(stripped):
            try:
                json.loads(stripped)
                return "json"
            except Exception:
                pass

        # Check XML
        if XML_PREFIX.match(stripped):
            return "xml"

        # Check Syslog RFC5424 / RFC3164 / BSD / ISO
        if (
            SYSLOG_PRI.match(stripped)
            or SYSLOG_BSD.match(stripped)
            or SYSLOG_ISO.match(stripped)
        ):
            return "syslog"

        # Check Key=Value (must have at least 2 distinct k=v pairs)
        kv_matches = KEY_VALUE_PATTERN.findall(stripped)
        if len(kv_matches) >= 2:
            return "kv"

        # Check CSV (must contain commas and multiple fields)
        if "," in stripped and "\n" not in stripped:
            try:
                reader = csv.reader(io.StringIO(stripped))
                row = next(reader)
                if len(row) >= 5:
                    return "csv"
            except Exception:
                pass

        return "plain_text"
