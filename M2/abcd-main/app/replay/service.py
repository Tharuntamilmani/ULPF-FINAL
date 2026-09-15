import time
import logging
from typing import List, Optional
from app.models.envelope import RawEventEnvelope
from app.models.parsed_event import ParsedEvent, ParserInfo
from app.registry.service import ParserRegistryService
from app.classifier.detector import Classifier

logger = logging.getLogger(__name__)


class ReplayService:
    """
    Replay Engine re-parsing historical stored RawEventEnvelopes
    against a newly registered or updated parser version with tenant isolation and structured error handling.
    """

    def __init__(
        self,
        registry_service: ParserRegistryService,
        classifier: Optional[Classifier] = None,
    ):
        self.registry_service = registry_service
        self.classifier = classifier or Classifier()

    def replay_events(
        self,
        parser_id: str,
        events: List[RawEventEnvelope],
        version: Optional[str] = None,
        tenant_id: str = "global",
    ) -> List[ParsedEvent]:
        """
        Replays raw events against a target parser ID & version scoped to tenant.
        Returns a list of updated ParsedEvent instances.
        """
        parser_defn = self.registry_service.repository.get(
            parser_id, version, tenant_id=tenant_id
        )
        if not parser_defn:
            raise ValueError(
                f"Parser '{parser_id}' version '{version}' not found or inaccessible for tenant '{tenant_id}'"
            )

        executable = self.registry_service.build_executable_parser(parser_defn)
        parsed_results = []

        for envelope in events:
            # Enforce tenant match
            if tenant_id != "global" and envelope.tenant_id != tenant_id:
                logger.warning(
                    f"Replay skipped event: envelope tenant '{envelope.tenant_id}' does not match caller '{tenant_id}'"
                )
                continue

            start_time = time.perf_counter()
            envelope_dict = envelope.model_dump()
            classification = self.classifier.classify(envelope)

            extracted_fields = {}
            status = "PARSED"
            error_meta = {}

            try:
                extracted_fields = executable.parse(envelope_dict)
                success = True
            except Exception as e:
                success = False
                status = "FAILED"
                error_meta["replay_error"] = str(e)
                error_meta["error_type"] = type(e).__name__
                # Structured error log without printing raw payload
                logger.error(
                    f"Replay failure: parser='{parser_defn.id}:{parser_defn.version}', "
                    f"raw_event_id='{envelope.raw_event_id}', tenant_id='{envelope.tenant_id}', "
                    f"error='{type(e).__name__}: {str(e)}'"
                )

            processing_time = round((time.perf_counter() - start_time) * 1000, 3)

            parsed_event = ParsedEvent(
                schema_version=envelope.schema_version,
                raw_event_id=envelope.raw_event_id,
                tenant_id=envelope.tenant_id,
                source_id=envelope.source_id,
                status=status,
                classification=classification,
                parser=ParserInfo(
                    id=parser_defn.id,
                    name=parser_defn.name,
                    version=parser_defn.version,
                    confidence=1.0 if success else 0.0,
                ),
                fields=extracted_fields,
                unmapped_fields=[],
                raw_reference=envelope.raw_reference,
                sha256=envelope.sha256,
                processing_time_ms=processing_time,
                metadata=error_meta,
            )
            parsed_results.append(parsed_event)

        return parsed_results
