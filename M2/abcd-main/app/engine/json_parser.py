import json
from typing import Dict, Any, List, Tuple
from app.engine.base import BaseParser

try:
    import orjson

    def parse_json(payload: str) -> Dict[str, Any]:
        return orjson.loads(payload)
except ImportError:

    def parse_json(payload: str) -> Dict[str, Any]:
        return json.loads(payload)


def flatten_dict(
    d: Dict[str, Any], parent_key: str = "", sep: str = "."
) -> Dict[str, Any]:
    items: List[Tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


class GenericJSONParser(BaseParser):
    parser_id = "parser-generic-json"
    name = "Generic JSON Parser"
    format = "json"
    version = "1.0.0"
    priority = 1000

    def can_parse(self, event: Dict[str, Any]) -> bool:
        payload = event.get("payload", "").strip()
        if not payload:
            return False

        # If syslog header wraps JSON, find first '{'
        idx = payload.find("{")
        if idx != -1:
            candidate = payload[idx:]
            try:
                data = parse_json(candidate)
                return isinstance(data, dict)
            except Exception:
                pass
        return False

    def parse(self, event: Dict[str, Any]) -> Dict[str, Any]:
        payload = event.get("payload", "").strip()
        idx = payload.find("{")
        if idx != -1:
            candidate = payload[idx:]
            data = parse_json(candidate)
            if isinstance(data, dict):
                return flatten_dict(data)
        return {}
