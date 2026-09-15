"""Configuration Lifecycle Management for ULPF M4."""

from app.config.enrichment_config import EnrichmentConfiguration
from app.errors.exceptions import InvalidConfigurationError
from app.models.common import ConfigLifecycleState


class ConfigurationManager:
    """Manages versioned enrichment configurations and their lifecycle states."""

    def __init__(self) -> None:
        self._configs: dict[str, EnrichmentConfiguration] = {}
        self._active_version: str | None = None

        # Seed default 1.0.0 active configuration
        default_cfg = EnrichmentConfiguration(
            version="1.0.0",
            state=ConfigLifecycleState.ACTIVE,
            description="Initial Default Active Configuration",
        )
        self._configs[default_cfg.version] = default_cfg
        self._active_version = default_cfg.version

    def register_draft(self, config: EnrichmentConfiguration) -> EnrichmentConfiguration:
        """Register a new configuration in DRAFT state."""
        if config.version in self._configs:
            raise InvalidConfigurationError(
                f"Configuration version {config.version} already exists"
            )
        if config.state != ConfigLifecycleState.DRAFT:
            raise InvalidConfigurationError(
                f"New configurations must start in DRAFT state, got {config.state}"
            )
        self._configs[config.version] = config
        return config

    def activate(self, version: str) -> EnrichmentConfiguration:
        """Activate a configuration version. Demotes previous active config to DEPRECATED."""
        if version not in self._configs:
            raise InvalidConfigurationError(f"Configuration version {version} not found")

        target = self._configs[version]
        if target.state not in (ConfigLifecycleState.DRAFT, ConfigLifecycleState.ROLLED_BACK):
            raise InvalidConfigurationError(
                f"Cannot activate configuration currently in state: {target.state}"
            )

        # Deprecate current active if different
        if (
            self._active_version
            and self._active_version in self._configs
            and self._active_version != version
        ):
            curr = self._configs[self._active_version]
            # Configurations are frozen, so model_copy with update
            deprecated_curr = curr.model_copy(update={"state": ConfigLifecycleState.DEPRECATED})
            self._configs[self._active_version] = deprecated_curr

        # Activate target
        activated = target.model_copy(update={"state": ConfigLifecycleState.ACTIVE})
        self._configs[version] = activated
        self._active_version = version
        return activated

    def rollback(self, target_version: str) -> EnrichmentConfiguration:
        """Rollback active configuration to a previously active or deprecated version."""
        if target_version not in self._configs:
            raise InvalidConfigurationError(f"Configuration version {target_version} not found")

        current_active = self.get_active()
        if current_active.version == target_version:
            raise InvalidConfigurationError(
                f"Cannot rollback: version {target_version} is already the active version"
            )

        # Mark current active as ROLLED_BACK
        rolled_back_current = current_active.model_copy(
            update={"state": ConfigLifecycleState.ROLLED_BACK}
        )
        self._configs[current_active.version] = rolled_back_current

        # Reactivate target
        target = self._configs[target_version]
        activated = target.model_copy(update={"state": ConfigLifecycleState.ACTIVE})
        self._configs[target_version] = activated
        self._active_version = target_version
        return activated

    def get_active(self) -> EnrichmentConfiguration:
        """Retrieve the current active configuration."""
        if not self._active_version or self._active_version not in self._configs:
            raise InvalidConfigurationError("No active configuration available")
        return self._configs[self._active_version]

    def get_version(self, version: str) -> EnrichmentConfiguration | None:
        """Retrieve configuration by specific version."""
        return self._configs.get(version)

    def list_configurations(self) -> list[EnrichmentConfiguration]:
        """List all configurations in registry."""
        return list(self._configs.values())
