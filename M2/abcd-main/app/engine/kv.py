import re
from typing import Dict, Any
from app.engine.base import BaseParser

# Regex to match key=value, key="quoted value", key='quoted value'
KV_REGEX = re.compile(
    r'(?P<key>[a-zA-Z0-9_\.\-]+)=(?P<quote>["\']?)(?P<val>.*?)(?<!\\)\2(?=\s+[$a-zA-Z0-9_\.\-]+=|[,;\s]|$)',
    re.DOTALL,
)


def parse_kv_string(text: str) -> Dict[str, Any]:
    fields = {}
    for match in KV_REGEX.finditer(text):
        key = match.group("key")
        val = match.group("val")
        # Strip unescaped quotes if present
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        elif val.startswith("'") and val.endswith("'"):
            val = val[1:-1]

        # Unescape quotes
        val = val.replace('\\"', '"').replace("\\'", "'")

        # Type conversion helper
        if val.isdigit():
            val = int(val)
        elif val.lower() == "true":
            val = True
        elif val.lower() == "false":
            val = False

        fields[key] = val
    return fields


class GenericKVParser(BaseParser):
    parser_id = "parser-generic-kv"
    name = "Generic Key-Value Parser"
    version = "1.0.0"
    vendor = "Generic"
    product = "Key-Value"
    format = "kv"
    priority = 20

    def can_parse(self, event: Dict[str, Any]) -> bool:
        payload = event.get("payload", "")
        return "=" in payload and len(parse_kv_string(payload)) >= 2

    def parse(self, event: Dict[str, Any]) -> Dict[str, Any]:
        payload = event.get("payload", "")
        return parse_kv_string(payload)
