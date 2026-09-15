import re
from typing import Dict, Any, List, Tuple
from packaging.version import parse as parse_version, InvalidVersion
from app.engine.regex import is_safe_regex
from app.engine.grok import grok_to_regex, COMMON_PATTERNS

PARSER_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")
SUPPORTED_FORMATS = {"syslog", "json", "kv", "cef", "leef", "csv", "xml", "plain_text"}


class ParserValidator:
    """Universal validator for parser definitions across startup, API, studio, and runtime."""

    @staticmethod
    def validate_parser_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        # 1. Validate ID
        parser_id = config.get("id")
        if not parser_id:
            errors.append("Parser configuration missing required field: 'id'")
        elif not isinstance(parser_id, str) or not PARSER_ID_REGEX.match(parser_id):
            errors.append(
                f"Invalid parser ID format: '{parser_id}'. Must be 3-64 alphanumeric, dash, or underscore characters"
            )

        # 2. Validate Version
        version = config.get("version", "1.0.0")
        try:
            parse_version(version)
        except (InvalidVersion, TypeError):
            errors.append(f"Invalid semantic version: '{version}'")

        # 3. Validate Name
        name = config.get("name")
        if not name or not isinstance(name, str):
            errors.append(
                "Parser configuration missing or invalid required field: 'name'"
            )

        # 4. Validate Formats
        formats = config.get("formats")
        if formats is None:
            formats = ["syslog"]

        if not isinstance(formats, list) or len(formats) == 0:
            errors.append(
                "Parser configuration must specify at least one supported format in 'formats'"
            )
        else:
            for fmt in formats:
                if not isinstance(fmt, str) or fmt.lower() not in SUPPORTED_FORMATS:
                    errors.append(
                        f"Unsupported format '{fmt}'. Supported: {sorted(SUPPORTED_FORMATS)}"
                    )

        # 5. Validate Resource Limits
        max_payload_bytes = config.get("max_payload_bytes", 100_000)
        if not isinstance(max_payload_bytes, int) or max_payload_bytes <= 0:
            errors.append(
                f"Invalid max_payload_bytes: {max_payload_bytes}. Must be a positive integer"
            )

        # 6. Validate Patterns & ReDoS screening
        patterns = config.get("patterns", [])
        custom_patterns = config.get("custom_patterns", {})
        combined_macros = dict(COMMON_PATTERNS)
        if isinstance(custom_patterns, dict):
            combined_macros.update(custom_patterns)

        for i, pat in enumerate(patterns):
            if not isinstance(pat, str):
                errors.append(f"Pattern at index {i} must be a string")
                continue

            # Check raw pattern for ReDoS
            if not is_safe_regex(pat):
                errors.append(f"Pattern index {i} violates ReDoS safety check: '{pat}'")

            # Try transpiling if it contains Grok expressions
            try:
                transpiled = grok_to_regex(pat, combined_macros)
                if not is_safe_regex(transpiled):
                    errors.append(
                        f"Transpiled pattern index {i} violates ReDoS safety check: '{transpiled}'"
                    )
                re.compile(transpiled)
            except Exception as e:
                errors.append(f"Pattern index {i} failed regex compilation: {str(e)}")

        # 7. Validate Tenant ID
        tenant_id = config.get("tenant_id", "global")
        if tenant_id and not isinstance(tenant_id, str):
            errors.append(f"Invalid tenant_id: '{tenant_id}'")

        is_valid = len(errors) == 0
        return is_valid, errors

    @classmethod
    def validate_and_raise(cls, config: Dict[str, Any]) -> None:
        is_valid, errors = cls.validate_parser_config(config)
        if not is_valid:
            raise ValueError(f"Parser validation failed: {'; '.join(errors)}")
