"""Unit tests for parser lifecycle state machine."""

from __future__ import annotations

import pytest

from backend.app.core.exceptions import InvalidStateTransition
from backend.app.models.parser import PARSER_TRANSITIONS, ParserStatus


class TestParserTransitions:
    """Test the PARSER_TRANSITIONS map exhaustively."""

    def test_draft_can_submit(self):
        assert ParserStatus.PENDING_APPROVAL in PARSER_TRANSITIONS[ParserStatus.DRAFT]

    def test_draft_cannot_activate(self):
        assert ParserStatus.ACTIVE not in PARSER_TRANSITIONS[ParserStatus.DRAFT]

    def test_pending_can_approve_or_reject(self):
        allowed = PARSER_TRANSITIONS[ParserStatus.PENDING_APPROVAL]
        assert ParserStatus.APPROVED in allowed
        assert ParserStatus.DRAFT in allowed

    def test_pending_cannot_activate_directly(self):
        assert ParserStatus.ACTIVE not in PARSER_TRANSITIONS[ParserStatus.PENDING_APPROVAL]

    def test_approved_can_activate(self):
        assert ParserStatus.ACTIVE in PARSER_TRANSITIONS[ParserStatus.APPROVED]

    def test_active_can_disable_or_rollback(self):
        allowed = PARSER_TRANSITIONS[ParserStatus.ACTIVE]
        assert ParserStatus.DISABLED in allowed
        assert ParserStatus.ROLLED_BACK in allowed

    def test_disabled_can_reactivate(self):
        assert ParserStatus.ACTIVE in PARSER_TRANSITIONS[ParserStatus.DISABLED]

    def test_rolled_back_can_reactivate(self):
        assert ParserStatus.ACTIVE in PARSER_TRANSITIONS[ParserStatus.ROLLED_BACK]

    def test_all_statuses_have_transitions_defined(self):
        for status in ParserStatus:
            assert status in PARSER_TRANSITIONS, f"No transitions defined for {status}"


@pytest.mark.asyncio
async def test_registry_enforces_invalid_transition(db_session):
    from backend.app.registry.parser_registry import ParserRegistry
    from backend.app.schemas.parser import ParserCreate

    registry = ParserRegistry(db_session)
    parser = await registry.register(
        ParserCreate(
            parser_id="test-parser-lifecycle",
            name="Test Parser",
            vendor="TestVendor",
            product="TestProduct",
            format="syslog",
            version="1.0.0",
        ),
        actor="admin",
        actor_role="ADMINISTRATOR",
    )
    assert parser.status == ParserStatus.DRAFT

    # Cannot go from DRAFT directly to ACTIVE
    with pytest.raises(InvalidStateTransition):
        await registry.activate(parser.id, "admin", "ADMINISTRATOR")


@pytest.mark.asyncio
async def test_full_lifecycle_happy_path(db_session):
    from backend.app.registry.parser_registry import ParserRegistry
    from backend.app.schemas.parser import ParserCreate

    registry = ParserRegistry(db_session)
    parser = await registry.register(
        ParserCreate(
            parser_id="test-parser-full",
            name="Full Lifecycle Parser",
            vendor="TestVendor",
            product="TestProduct",
            format="cef",
            version="1.0.0",
        ),
        actor="dev",
        actor_role="PARSER_DEVELOPER",
    )
    assert parser.status == ParserStatus.DRAFT

    # DRAFT → PENDING_APPROVAL
    parser = await registry.submit(parser.id, "dev", "PARSER_DEVELOPER")
    assert parser.status == ParserStatus.PENDING_APPROVAL

    # PENDING_APPROVAL → APPROVED
    parser = await registry.approve(parser.id, "admin", "ADMINISTRATOR")
    assert parser.status == ParserStatus.APPROVED
    assert parser.approved_by == "admin"

    # APPROVED → ACTIVE
    parser = await registry.activate(parser.id, "admin", "ADMINISTRATOR")
    assert parser.status == ParserStatus.ACTIVE

    # ACTIVE → DISABLED
    parser = await registry.disable(parser.id, "admin", "ADMINISTRATOR")
    assert parser.status == ParserStatus.DISABLED

    # DISABLED → ACTIVE (re-activate)
    parser = await registry.activate(parser.id, "admin", "ADMINISTRATOR")
    assert parser.status == ParserStatus.ACTIVE

    # ACTIVE → ROLLED_BACK
    parser = await registry.rollback(parser.id, "admin", "ADMINISTRATOR", "emergency rollback")
    assert parser.status == ParserStatus.ROLLED_BACK
