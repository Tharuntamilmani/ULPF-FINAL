import re
from typing import Dict, Any
from app.engine.kv import parse_kv_string
from app.engine.json_parser import parse_json, flatten_dict
from app.engine.cef import parse_cef_string
from app.engine.leef import parse_leef_string


class FieldDetector:
    """Extracts candidate structured fields from unknown log payloads."""

    def detect_fields(self, payload: str, format_type: str = "kv") -> Dict[str, Any]:
        if not payload:
            return {}

        stripped = payload.strip()

        # 1. JSON candidate
        if format_type == "json" or stripped.startswith("{"):
            try:
                data = parse_json(stripped)
                if isinstance(data, dict):
                    return flatten_dict(data)
            except Exception:
                pass

        # 2. CEF candidate
        if format_type == "cef" or "CEF:" in stripped:
            try:
                return parse_cef_string(stripped)
            except Exception:
                pass

        # 3. LEEF candidate
        if format_type == "leef" or "LEEF:" in stripped:
            try:
                return parse_leef_string(stripped)
            except Exception:
                pass

        # 4. Key-Value candidate
        kv_fields = parse_kv_string(stripped)
        if kv_fields:
            return kv_fields

        # 5. Regex delimiter / colon key-value fallback (e.g., "key: value, key2: value2")
        colon_fields = {}
        matches = re.findall(
            r'([a-zA-Z0-9_\.\-]+)\s*[:=]\s*("[^"]*"|\'[^\']*\'|[^\s,;]+)', stripped
        )
        for k, v in matches:
            v_clean = v.strip("\"'")
            colon_fields[k] = int(v_clean) if v_clean.isdigit() else v_clean

        if colon_fields:
            return colon_fields

        # 6. Unstructured text token breakdown
        tokens = stripped.split()
        return {f"token_{i}": tok for i, tok in enumerate(tokens[:10])}
