import re
from typing import Dict, Any
from app.engine.base import BaseParser
from app.engine.kv import parse_kv_string

LEEF_PREFIX_REGEX = re.compile(
    r"^(?:.*?\s)?LEEF:(?P<version>1\.0|2\.0)\|(?P<vendor>[^|]*)\|(?P<product>[^|]*)\|(?P<dev_version>[^|]*)\|(?P<event_id>[^|]*)\|(?:(?P<remainder>.*))?$",
    re.DOTALL,
)


def parse_leef_string(payload: str) -> Dict[str, Any]:
    match = LEEF_PREFIX_REGEX.match(payload.strip())
    if not match:
        raise ValueError("Invalid LEEF payload header format")

    groups = match.groupdict()
    version = groups["version"]
    fields = {
        "leef_version": version,
        "vendor": groups["vendor"],
        "product": groups["product"],
        "device_version": groups["dev_version"],
        "event_id": groups["event_id"],
    }

    remainder = groups.get("remainder", "")
    if not remainder:
        return fields

    delimiter = "\t" if version == "2.0" else " "
    ext_text = remainder

    # If LEEF 2.0 explicitly specifies custom delimiter e.g. LEEF:2.0|...|EventID|^|Extension
    if version == "2.0" and len(remainder) > 2 and remainder[1] == "|":
        delimiter = remainder[0]
        ext_text = remainder[2:]

    # Parse key-values from extension
    if delimiter == "\t" or delimiter == " ":
        ext_fields = parse_kv_string(ext_text)
    else:
        # Custom delimiter separated kv pairs
        ext_fields = {}
        for item in ext_text.split(delimiter):
            if "=" in item:
                k, v = item.split("=", 1)
                ext_fields[k.strip()] = v.strip()

    fields.update(ext_fields)
    return fields


class LEEFParser(BaseParser):
    parser_id = "parser-leef"
    name = "Log Event Extended Format (LEEF) Parser"
    version = "1.0.0"
    vendor = "Generic"
    product = "LEEF"
    format = "leef"
    priority = 50

    def can_parse(self, event: Dict[str, Any]) -> bool:
        payload = event.get("payload", "")
        return "LEEF:" in payload

    def parse(self, event: Dict[str, Any]) -> Dict[str, Any]:
        payload = event.get("payload", "")
        return parse_leef_string(payload)
