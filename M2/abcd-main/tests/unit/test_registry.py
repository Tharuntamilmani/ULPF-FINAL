from app.registry.models import ParserDefinition, ParserStatus
from app.registry.repository import ParserRepository
from app.registry.service import ParserRegistryService


def test_registry_lifecycle():
    repo = ParserRepository()
    service = ParserRegistryService(repo)

    p1 = ParserDefinition(
        id="parser-test-custom",
        name="Test Custom Parser",
        vendor="Custom",
        product="App",
        formats=["syslog"],
        version="1.0.0",
        patterns=["src=%{IP:srcip}"],
    )

    service.register_parser(p1)
    retrieved = repo.get("parser-test-custom", "1.0.0")
    assert retrieved is not None
    assert retrieved.name == "Test Custom Parser"

    # Version bump
    p2 = ParserDefinition(
        id="parser-test-custom",
        name="Test Custom Parser v1.1",
        vendor="Custom",
        product="App",
        formats=["syslog"],
        version="1.1.0",
        patterns=["src=%{IP:srcip} dst=%{IP:dstip}"],
    )
    service.register_parser(p2)
    latest = repo.get("parser-test-custom")
    assert latest.version == "1.1.0"

    # Disable v1.1.0 and test fallback / lookup
    service.disable_parser("parser-test-custom", "1.1.0")
    active = repo.get("parser-test-custom")
    assert active.version == "1.0.0"

    # Rollback to 1.1.0
    rolled = service.rollback_parser("parser-test-custom", "1.1.0")
    assert rolled.version == "1.1.0"
    assert rolled.status == ParserStatus.ACTIVE
