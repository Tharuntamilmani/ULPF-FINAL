"""Unit tests for configuration schema validation and lifecycle state transitions."""

import pytest

from app.config.enrichment_config import EnrichmentConfiguration
from app.config.lifecycle import ConfigurationManager
from app.errors.exceptions import InvalidConfigurationError
from app.models.common import ConfigLifecycleState


def test_configuration_schema_validation() -> None:
    """Verify semantic version validation in EnrichmentConfiguration."""
    valid_cfg = EnrichmentConfiguration(version="1.2.3")
    assert valid_cfg.version == "1.2.3"

    with pytest.raises(ValueError, match="semantic versioning"):
        EnrichmentConfiguration(version="invalid-version-string")


def test_configuration_lifecycle_transitions() -> None:
    """Test DRAFT -> ACTIVE -> DEPRECATED lifecycle."""
    mgr = ConfigurationManager()
    # Initial default is 1.0.0 (ACTIVE)
    active_initial = mgr.get_active()
    assert active_initial.version == "1.0.0"
    assert active_initial.state == ConfigLifecycleState.ACTIVE

    # Register draft 2.0.0
    draft = EnrichmentConfiguration(
        version="2.0.0",
        state=ConfigLifecycleState.DRAFT,
        description="Version 2",
    )
    mgr.register_draft(draft)
    v2_draft = mgr.get_version("2.0.0")
    assert v2_draft is not None
    assert v2_draft.state == ConfigLifecycleState.DRAFT

    # Activate 2.0.0
    activated = mgr.activate("2.0.0")
    assert activated.state == ConfigLifecycleState.ACTIVE
    assert mgr.get_active().version == "2.0.0"

    # 1.0.0 should now be DEPRECATED
    old_version = mgr.get_version("1.0.0")
    assert old_version is not None
    assert old_version.state == ConfigLifecycleState.DEPRECATED


def test_configuration_rollback() -> None:
    """Test rolling back from a newer active version to an older deprecated version."""
    mgr = ConfigurationManager()
    draft = EnrichmentConfiguration(version="2.0.0", state=ConfigLifecycleState.DRAFT)
    mgr.register_draft(draft)
    mgr.activate("2.0.0")

    # Rollback to 1.0.0
    rolled_back = mgr.rollback("1.0.0")
    assert rolled_back.state == ConfigLifecycleState.ACTIVE
    assert mgr.get_active().version == "1.0.0"

    # 2.0.0 should now be in ROLLED_BACK state
    v2 = mgr.get_version("2.0.0")
    assert v2 is not None
    assert v2.state == ConfigLifecycleState.ROLLED_BACK


def test_configuration_invalid_state_activations() -> None:
    """Prohibit registering non-draft configurations as new drafts."""
    mgr = ConfigurationManager()
    active_as_draft = EnrichmentConfiguration(version="3.0.0", state=ConfigLifecycleState.ACTIVE)
    with pytest.raises(InvalidConfigurationError, match="must start in DRAFT state"):
        mgr.register_draft(active_as_draft)
