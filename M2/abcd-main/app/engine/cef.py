import re
from typing import Dict, Any
from app.engine.base import BaseParser
from app.engine.kv import parse_kv_string

CEF_PREFIX_REGEX = re.compile(
    r"^(?:.*?\s)?CEF:(?P<version>\d+)\|(?P<vendor>[^|]*)\|(?P<product>[^|]*)\|(?P<dev_version>[^|]*)\|(?P<signature_id>[^|]*)\|(?P<name>[^|]*)\|(?P<severity>[^|]*)\|(?:(?P<extension>.*))?$",
    re.DOTALL,
)


def parse_cef_string(payload: str) -> Dict[str, Any]:
    match = CEF_PREFIX_REGEX.match(payload.strip())
    if not match:
        raise ValueError("Invalid CEF payload header format")

    groups = match.groupdict()
    fields = {
        "cef_version": int(groups["version"]),
        "device_vendor": groups["vendor"],
        "device_product": groups["product"],
        "device_version": groups["dev_version"],
        "signature_id": groups["signature_id"],
        "name": groups["name"],
        "severity": groups["severity"],
    }

    ext_text = groups.get("extension")
    if ext_text:
        ext_fields = parse_kv_string(ext_text)
        fields.update(ext_fields)

    return fields


class CEFParser(BaseParser):
    parser_id = "parser-cef"
    name = "Common Event Format (CEF) Parser"
    version = "1.0.0"
    vendor = "Generic"
    product = "CEF"
    format = "cef"
    priority = 50

    def can_parse(self, event: Dict[str, Any]) -> bool:
        payload = event.get("payload", "")
        return "CEF:" in payload

    def parse(self, event: Dict[str, Any]) -> Dict[str, Any]:
        payload = event.get("payload", "")
        return parse_cef_string(payload)
