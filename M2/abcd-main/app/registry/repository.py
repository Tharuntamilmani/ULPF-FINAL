import os
import glob
import logging
import yaml
from typing import Dict, List, Optional
from packaging.version import parse as parse_version
from app.registry.models import ParserDefinition, ParserStatus

logger = logging.getLogger(__name__)


class ParserRepository:
    """
    Tenant-partitioned storage & persistence repository for parser definitions.
    Supports filesystem YAML declarative loading, semantic versioning, and strict tenant isolation.
    """

    def __init__(self, parsers_dir: Optional[str] = None):
        # Storage partitioned as: tenant_id -> parser_id -> version -> ParserDefinition
        self._parsers: Dict[str, Dict[str, Dict[str, ParserDefinition]]] = {}
        self.parsers_dir = parsers_dir

    def load_from_directory(self, directory_path: str) -> None:
        """Recursively loads and validates declarative YAML parser definitions from directory."""
        from app.studio.validation import ParserValidator

        if not os.path.exists(directory_path):
            return

        yaml_files = glob.glob(
            os.path.join(directory_path, "**/*.yaml"), recursive=True
        ) + glob.glob(os.path.join(directory_path, "**/*.yml"), recursive=True)

        for filepath in yaml_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                    if not content or "parser" not in content:
                        continue

                    p_meta = content["parser"]
                    p_match = content.get("match", {})
                    p_patterns = content.get("patterns", [])
                    p_fields = content.get("fields", {})

                    config_dict = {
                        "id": p_meta.get("id"),
                        "name": p_meta.get("name", p_meta.get("id")),
                        "tenant_id": p_meta.get("tenant_id", "global"),
                        "vendor": p_match.get(
                            "vendor", p_meta.get("vendor", "Generic")
                        ),
                        "product": p_match.get(
                            "product", p_meta.get("product", "Generic")
                        ),
                        "formats": p_match.get(
                            "formats", [p_meta.get("format", "syslog")]
                        ),
                        "version": str(p_meta.get("version", "1.0.0")),
                        "mapping_version": str(p_meta.get("mapping_version", "1.0.0")),
                        "priority": p_meta.get("priority", 100),
                        "status": p_meta.get("status", "active"),
                        "patterns": p_patterns,
                        "fields": p_fields,
                        "created_by": p_meta.get("created_by", "system"),
                    }

                    # Startup Validation
                    is_valid, errors = ParserValidator.validate_parser_config(
                        config_dict
                    )
                    if not is_valid:
                        logger.error(
                            f"Quarantining invalid parser YAML {filepath}: {'; '.join(errors)}"
                        )
                        continue

                    definition = ParserDefinition(**config_dict)
                    self.save(definition)
            except Exception as e:
                logger.warning(f"Failed to load parser file {filepath}: {e}")

    def save(self, parser: ParserDefinition) -> None:
        tenant_id = parser.tenant_id or "global"
        if tenant_id not in self._parsers:
            self._parsers[tenant_id] = {}
        if parser.id not in self._parsers[tenant_id]:
            self._parsers[tenant_id][parser.id] = {}
        self._parsers[tenant_id][parser.id][parser.version] = parser

    def get(
        self, parser_id: str, version: Optional[str] = None, tenant_id: str = "global"
    ) -> Optional[ParserDefinition]:
        """
        Retrieves parser definition. Searches tenant-specific storage first, falling back to global baseline.
        Does NOT allow cross-tenant inspection.
        """
        # Try tenant-specific store first
        if (
            tenant_id
            and tenant_id in self._parsers
            and parser_id in self._parsers[tenant_id]
        ):
            versions = self._parsers[tenant_id][parser_id]
            if version:
                return versions.get(version)
            return self._get_highest_active_version(versions)

        # Fallback to global store
        if "global" in self._parsers and parser_id in self._parsers["global"]:
            versions = self._parsers["global"][parser_id]
            if version:
                return versions.get(version)
            return self._get_highest_active_version(versions)

        return None

    def _get_highest_active_version(
        self, versions: Dict[str, ParserDefinition]
    ) -> Optional[ParserDefinition]:
        """Returns the highest semantic version that is currently ACTIVE."""
        try:
            sorted_versions = sorted(versions.keys(), key=parse_version, reverse=True)
        except Exception:
            sorted_versions = sorted(versions.keys(), reverse=True)

        for v in sorted_versions:
            if versions[v].status == ParserStatus.ACTIVE:
                return versions[v]
        return versions[sorted_versions[0]] if sorted_versions else None

    def list_for_tenant(
        self,
        tenant_id: str = "global",
        include_global: bool = True,
        vendor: Optional[str] = None,
        format_type: Optional[str] = None,
    ) -> List[ParserDefinition]:
        """
        Lists active parsers accessible to the specified tenant.
        Includes tenant-specific parsers, overlaid on global baseline parsers.
        Excludes other tenants completely.
        """
        seen_ids = set()
        res = []

        # 1. Tenant-specific parsers
        if tenant_id and tenant_id != "global" and tenant_id in self._parsers:
            for p_id in self._parsers[tenant_id]:
                active_p = self.get(p_id, tenant_id=tenant_id)
                if active_p and active_p.status == ParserStatus.ACTIVE:
                    if self._matches_filter(active_p, vendor, format_type):
                        res.append(active_p)
                        seen_ids.add(p_id)

        # 2. Global baseline parsers
        if include_global and "global" in self._parsers:
            for p_id in self._parsers["global"]:
                if p_id not in seen_ids:
                    active_p = self.get(p_id, tenant_id="global")
                    if active_p and active_p.status == ParserStatus.ACTIVE:
                        if self._matches_filter(active_p, vendor, format_type):
                            res.append(active_p)

        return sorted(res, key=lambda x: x.priority)

    def _matches_filter(
        self,
        parser: ParserDefinition,
        vendor: Optional[str],
        format_type: Optional[str],
    ) -> bool:
        if vendor and parser.vendor.lower() != vendor.lower():
            return False
        if format_type and format_type.lower() not in [
            f.lower() for f in parser.formats
        ]:
            return False
        return True

    def list_all(
        self,
        vendor: Optional[str] = None,
        format_type: Optional[str] = None,
        tenant_id: str = "global",
    ) -> List[ParserDefinition]:
        """Backward-compatible method returning parsers accessible to tenant_id."""
        return self.list_for_tenant(
            tenant_id=tenant_id,
            include_global=True,
            vendor=vendor,
            format_type=format_type,
        )

    def list_versions(
        self, parser_id: str, tenant_id: str = "global"
    ) -> List[ParserDefinition]:
        """Lists semantic versions of a parser scoped to tenant or global."""
        versions_dict = {}
        if tenant_id in self._parsers and parser_id in self._parsers[tenant_id]:
            versions_dict = self._parsers[tenant_id][parser_id]
        elif "global" in self._parsers and parser_id in self._parsers["global"]:
            versions_dict = self._parsers["global"][parser_id]

        try:
            return sorted(
                versions_dict.values(),
                key=lambda x: parse_version(x.version),
                reverse=True,
            )
        except Exception:
            return sorted(versions_dict.values(), key=lambda x: x.version, reverse=True)
