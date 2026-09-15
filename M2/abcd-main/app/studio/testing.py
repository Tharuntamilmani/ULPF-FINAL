from typing import Dict, Any, List
from app.registry.models import ParserDefinition
from app.registry.service import ParserRegistryService


class StudioTestRunner:
    """Dry-run testing for candidate parsers before registration."""

    def __init__(self, registry_service: ParserRegistryService):
        self.registry_service = registry_service

    def test_parser(
        self, definition: ParserDefinition, sample_raw_events: List[str]
    ) -> List[Dict[str, Any]]:
        executable = self.registry_service.build_executable_parser(definition)
        results = []

        for idx, payload in enumerate(sample_raw_events):
            envelope_dict = {"raw_event_id": f"test_{idx}", "payload": payload}
            try:
                extracted = executable.parse(envelope_dict)
                results.append(
                    {
                        "sample_index": idx,
                        "success": True,
                        "extracted_fields": extracted,
                        "error": None,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "sample_index": idx,
                        "success": False,
                        "extracted_fields": {},
                        "error": str(e),
                    }
                )

        return results
