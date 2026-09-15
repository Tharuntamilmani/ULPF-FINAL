from typing import Dict, Any
from app.registry.models import ParserDefinition, ParserStatus


class MappingBuilder:
    """Builds a registered ParserDefinition from Studio user mapping input."""

    @staticmethod
    def build_definition(
        parser_id: str,
        name: str,
        vendor: str,
        product: str,
        format_type: str,
        detected_fields: Dict[str, Any],
        user_mappings: Dict[str, str],
        version: str = "1.0.0",
        tenant_id: str = "global",
    ) -> ParserDefinition:
        # Build patterns based on format type
        if format_type in ["kv", "json", "cef", "leef"]:
            patterns = []  # Uses built-in standard format engines
        else:
            # Build regex/grok pattern for candidate fields
            patterns = [".*"]

        return ParserDefinition(
            id=parser_id,
            name=name,
            tenant_id=tenant_id,
            vendor=vendor,
            product=product,
            formats=[format_type],
            version=version,
            mapping_version=version,
            priority=100,
            status=ParserStatus.ACTIVE,
            patterns=patterns,
            fields=user_mappings,
            max_payload_bytes=100_000,
            created_by="studio",
        )
