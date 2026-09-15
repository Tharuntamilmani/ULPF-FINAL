from typing import Optional, List, Dict, Any, Tuple
from app.registry.models import ParserDefinition, ParserStatus
from app.registry.repository import ParserRepository
from app.classifier.detector import ClassificationResult
from app.engine.base import BaseParser
from app.engine.json_parser import GenericJSONParser
from app.engine.kv import GenericKVParser
from app.engine.cef import CEFParser
from app.engine.leef import LEEFParser
from app.engine.grok import GrokParser


class ParserRegistryService:
    """
    Parser Registry Service managing parser lifecycles, semantic versioning,
    deterministic resolution hierarchy, tenant scoping, and parser building.
    """

    def __init__(self, repository: Optional[ParserRepository] = None):
        self.repository = repository or ParserRepository()
        self._built_in_parsers: List[BaseParser] = [
            CEFParser(),
            LEEFParser(),
            GenericJSONParser(),
            GenericKVParser(),
        ]

    def register_parser(
        self,
        definition: ParserDefinition,
        caller_tenant_id: str = "global",
        is_system: bool = False,
    ) -> ParserDefinition:
        """Validates and registers a new parser definition with strict tenant boundary enforcement."""
        # Tenant boundary check: only system callers can create global baseline parsers
        if not is_system and caller_tenant_id != "global":
            if definition.tenant_id == "global":
                raise ValueError(
                    "Non-system callers cannot register global baseline parsers"
                )
            if definition.tenant_id != caller_tenant_id:
                raise ValueError(
                    f"Forbidden: Cannot register parser for tenant '{definition.tenant_id}' with caller tenant '{caller_tenant_id}'"
                )

        # Universal validation check
        from app.studio.validation import ParserValidator

        ParserValidator.validate_and_raise(definition.model_dump())

        # Test compilation before saving
        _ = self.build_executable_parser(definition)

        definition.status = ParserStatus.ACTIVE
        self.repository.save(definition)
        return definition

    def disable_parser(
        self, parser_id: str, version: Optional[str] = None, tenant_id: str = "global"
    ) -> bool:
        parser = self.repository.get(parser_id, version, tenant_id=tenant_id)
        if parser:
            parser.status = ParserStatus.DISABLED
            self.repository.save(parser)
            return True
        return False

    def enable_parser(
        self, parser_id: str, version: Optional[str] = None, tenant_id: str = "global"
    ) -> bool:
        parser = self.repository.get(parser_id, version, tenant_id=tenant_id)
        if parser:
            parser.status = ParserStatus.ACTIVE
            self.repository.save(parser)
            return True
        return False

    def rollback_parser(
        self, parser_id: str, target_version: str, tenant_id: str = "global"
    ) -> Optional[ParserDefinition]:
        versions = self.repository.list_versions(parser_id, tenant_id=tenant_id)
        target = None
        for v in versions:
            if v.version == target_version:
                target = v
                break

        if not target:
            return None

        for v in versions:
            v.status = (
                ParserStatus.DISABLED
                if v.version != target_version
                else ParserStatus.ACTIVE
            )
            self.repository.save(v)

        return target

    def build_executable_parser(self, definition: ParserDefinition) -> BaseParser:
        """Instantiates an executable BaseParser with resource limits from declarative definition."""
        return GrokParser(
            parser_id=definition.id,
            name=definition.name,
            version=definition.version,
            patterns=definition.patterns,
            custom_patterns=definition.custom_patterns,
            fields_map=definition.fields,
            max_payload_bytes=definition.max_payload_bytes,
        )

    def find_parser(
        self,
        classification: ClassificationResult,
        envelope_dict: Dict[str, Any],
        tenant_id: str = "global",
    ) -> Tuple[Optional[BaseParser], Optional[ParserDefinition]]:
        """
        Deterministic 4-step parser resolution hierarchy:
        1. Exact tenant-specific vendor/product/format parser
        2. Appropriate global baseline vendor/product parser
        3. Explicitly generic parser for detected format (built-in or global generic)
        4. Explicit UNPARSED result (None, None)
        """
        target_vendor = (classification.vendor or "").strip().lower()
        target_product = (classification.product or "").strip().lower()
        target_format = (classification.format or "").strip().lower()

        # Step 1: Search exact tenant-specific vendor/product matching or format extension parsers
        if tenant_id and tenant_id != "global":
            tenant_parsers = self.repository.list_for_tenant(
                tenant_id=tenant_id, include_global=False
            )
            for defn in tenant_parsers:
                if defn.status != ParserStatus.ACTIVE:
                    continue
                v_match = (defn.vendor.lower() == target_vendor) or (
                    target_vendor in ("", "unknown")
                )
                p_match = (
                    defn.product.lower() == target_product or defn.product == "Generic"
                ) or (target_product in ("", "unknown"))
                f_match = (target_format in [f.lower() for f in defn.formats]) or (
                    "syslog" in [f.lower() for f in defn.formats]
                )

                if v_match and p_match and f_match:
                    try:
                        executable = self.build_executable_parser(defn)
                        if executable.can_parse(envelope_dict):
                            return executable, defn
                    except Exception:
                        continue

        # Step 2: Search exact global baseline vendor & product matching registered parsers
        if target_vendor and target_vendor != "unknown":
            global_parsers = self.repository.list_for_tenant(
                tenant_id="global", include_global=True
            )
            for defn in global_parsers:
                if defn.status != ParserStatus.ACTIVE:
                    continue
                v_match = defn.vendor.lower() == target_vendor
                p_match = (
                    defn.product.lower() == target_product or defn.product == "Generic"
                )
                f_match = target_format in [f.lower() for f in defn.formats]

                if v_match and p_match and f_match:
                    try:
                        executable = self.build_executable_parser(defn)
                        if executable.can_parse(envelope_dict):
                            return executable, defn
                    except Exception:
                        continue

        # Step 3: Explicitly generic parsers (never pick arbitrary vendor-specific parsers)
        # 3a. Check registered global generic parsers
        registered = self.repository.list_for_tenant(
            tenant_id=tenant_id, include_global=True
        )
        for defn in registered:
            if defn.status != ParserStatus.ACTIVE:
                continue
            if defn.vendor.lower() == "generic" and target_format in [
                f.lower() for f in defn.formats
            ]:
                try:
                    executable = self.build_executable_parser(defn)
                    if executable.can_parse(envelope_dict):
                        return executable, defn
                except Exception:
                    continue

        # 3b. Check built-in generic protocol parsers (CEF, LEEF, JSON, KV)
        for parser in self._built_in_parsers:
            if parser.format.lower() == target_format or parser.can_parse(
                envelope_dict
            ):
                built_in_defn = ParserDefinition(
                    id=parser.parser_id,
                    name=parser.name,
                    tenant_id="global",
                    vendor=classification.vendor or "Generic",
                    product=classification.product or "Generic",
                    formats=[parser.format],
                    version=parser.version,
                    mapping_version="1.0.0",
                    priority=parser.priority,
                    status=ParserStatus.ACTIVE,
                    max_payload_bytes=100_000,
                    created_by="system",
                )
                return parser, built_in_defn

        # Step 4: Explicit UNPARSED
        return None, None
