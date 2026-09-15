import time
import os
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status, Query, Depends
from pydantic import BaseModel

from app.models.envelope import RawEventEnvelope
from app.models.parsed_event import ParsedEvent, ParserInfo
from app.classifier.detector import Classifier
from app.registry.service import ParserRegistryService
from app.registry.repository import ParserRepository
from app.registry.models import ParserDefinition
from app.discovery import UnknownSourceDiscoveryEngine
from app.studio import ParserValidator, StudioTestRunner
from app.replay import ReplayService
from app.auth import AuthContext, Role, get_current_auth_context, require_roles
from app.health import (
    get_metrics_response,
    EVENTS_TOTAL,
    SUCCESS_TOTAL,
    FAILURE_TOTAL,
    UNKNOWN_TOTAL,
    LATENCY_SECONDS,
    CONFIDENCE_GAUGE,
    REPLAY_TOTAL,
    DISCOVERY_TOTAL,
    REGISTRY_SIZE,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ULPF Member 2 — Format Classifier & Parser Engine",
    description="Member 2 owns raw event format classification, parser lookup/execution, unknown-source discovery, Parser Studio APIs, and event replay.",
    version="1.0.0",
)

# Initialize Services
repository = ParserRepository()
parsers_path = os.getenv("PARSER_STORAGE_DIR", "./parsers")
if os.path.exists(parsers_path):
    repository.load_from_directory(parsers_path)

registry_service = ParserRegistryService(repository)
classifier = Classifier()
discovery_engine = UnknownSourceDiscoveryEngine()
replay_service = ReplayService(registry_service, classifier)
test_runner = StudioTestRunner(registry_service)


# API DTO Models
class DiscoverRequest(BaseModel):
    raw_event_id: Optional[str] = "raw_unknown"
    payload: str


class ValidateRequest(BaseModel):
    parser_config: Dict[str, Any]


class TestRequest(BaseModel):
    parser_definition: ParserDefinition
    sample_raw_events: List[str]


class ReplayRequest(BaseModel):
    events: List[RawEventEnvelope]
    version: Optional[str] = None


@app.on_event("startup")
def startup_event():
    active_count = len(repository.list_all())
    REGISTRY_SIZE.set(active_count)


@app.get("/health")
def health_check():
    """Unauthenticated liveness probe."""
    return {
        "status": "healthy",
        "service": "m2-parser",
        "registry_size": len(repository.list_all()),
    }


@app.get("/metrics")
def metrics():
    """Prometheus telemetry scrape endpoint."""
    return get_metrics_response()


@app.post("/v1/parse", response_model=ParsedEvent)
def parse_event(
    envelope: RawEventEnvelope,
    auth_ctx: AuthContext = Depends(require_roles(Role.INGEST.value, Role.ADMIN.value)),
):
    """
    Main M1 -> M2 Ingestion Entrypoint.
    Authenticates caller, verifies tenant authorization, classifies format,
    executes matching parser, and emits contract-compliant ParsedEvent.
    """
    # Tenant boundary enforcement: prevent cross-tenant ingestion spoofing
    if not auth_ctx.can_access_tenant(envelope.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Authenticated principal '{auth_ctx.principal_id}' scoped to tenant '{auth_ctx.tenant_id}' cannot ingest for '{envelope.tenant_id}'",
        )

    EVENTS_TOTAL.inc()
    start_time = time.perf_counter()

    # Step 1: Classify Format and Source
    classification = classifier.classify(envelope)
    CONFIDENCE_GAUGE.set(classification.confidence)

    # Step 2: Find & Execute Parser with strict tenant scope
    envelope_dict = envelope.model_dump()
    executable, parser_defn = registry_service.find_parser(
        classification, envelope_dict, tenant_id=envelope.tenant_id
    )

    status_val = "PARSED"
    err_metadata: Dict[str, Any] = {}

    if not executable or not parser_defn:
        UNKNOWN_TOTAL.inc()
        # Explicit unparsed event - do NOT synthesize fake token fields into production output
        extracted_fields: Dict[str, Any] = {}
        status_val = "UNPARSED"
        parser_info = ParserInfo(
            id="unparsed", name="Unparsed Event", version="0.0.0", confidence=0.0
        )
    else:
        try:
            extracted_fields = executable.parse(envelope_dict)
            SUCCESS_TOTAL.inc()
            parser_info = ParserInfo(
                id=parser_defn.id,
                name=parser_defn.name,
                version=parser_defn.version,
                confidence=1.0,
            )
        except (ValueError, TimeoutError) as e:
            FAILURE_TOTAL.inc()
            status_val = "FAILED"
            extracted_fields = {}
            err_metadata["error"] = str(e)
            err_metadata["error_type"] = type(e).__name__
            parser_info = ParserInfo(
                id=parser_defn.id,
                name=parser_defn.name,
                version=parser_defn.version,
                confidence=0.0,
            )
            # If payload length was exceeded, log security event
            logger.warning(f"Parse error for event '{envelope.raw_event_id}': {e}")
        except Exception as e:
            FAILURE_TOTAL.inc()
            status_val = "FAILED"
            extracted_fields = {}
            err_metadata["error"] = str(e)
            err_metadata["error_type"] = type(e).__name__
            parser_info = ParserInfo(
                id=parser_defn.id,
                name=parser_defn.name,
                version=parser_defn.version,
                confidence=0.0,
            )
            logger.error(
                f"Unexpected parser failure for event '{envelope.raw_event_id}': {e}"
            )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
    LATENCY_SECONDS.observe(elapsed_ms / 1000.0)

    return ParsedEvent(
        schema_version=envelope.schema_version,
        raw_event_id=envelope.raw_event_id,
        tenant_id=envelope.tenant_id,
        source_id=envelope.source_id,
        status=status_val,
        classification=classification,
        parser=parser_info,
        fields=extracted_fields,
        unmapped_fields=[],
        raw_reference=envelope.raw_reference,
        sha256=envelope.sha256,
        processing_time_ms=elapsed_ms,
        metadata=err_metadata,
    )


@app.post("/v1/parsers/discover")
def discover_unknown_event(
    req: DiscoverRequest,
    auth_ctx: AuthContext = Depends(
        require_roles(Role.ANALYST.value, Role.STUDIO.value, Role.ADMIN.value)
    ),
):
    """Unknown-Source Discovery endpoint analyzing candidate fields and mapping suggestions (Advisory)."""
    DISCOVERY_TOTAL.inc()
    return discovery_engine.discover(req.payload)


@app.post("/v1/parsers/validate")
def validate_parser(
    req: ValidateRequest,
    auth_ctx: AuthContext = Depends(require_roles(Role.STUDIO.value, Role.ADMIN.value)),
):
    """Parser Studio Endpoint: Validates parser configuration and ReDoS safety."""
    is_valid, errors = ParserValidator.validate_parser_config(req.parser_config)
    return {"valid": is_valid, "errors": errors}


@app.post("/v1/parsers/test")
def test_parser(
    req: TestRequest,
    auth_ctx: AuthContext = Depends(require_roles(Role.STUDIO.value, Role.ADMIN.value)),
):
    """Parser Studio Endpoint: Dry-run test parser against sample raw event payloads."""
    results = test_runner.test_parser(req.parser_definition, req.sample_raw_events)
    return {"parser_id": req.parser_definition.id, "results": results}


@app.post("/v1/parsers/register", response_model=ParserDefinition)
def register_parser(
    definition: ParserDefinition,
    auth_ctx: AuthContext = Depends(require_roles(Role.STUDIO.value, Role.ADMIN.value)),
):
    """Registers a new or updated parser in the registry with strict validation and tenant boundary checks."""
    try:
        registered = registry_service.register_parser(
            definition,
            caller_tenant_id=auth_ctx.tenant_id,
            is_system=auth_ctx.is_system,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    REGISTRY_SIZE.set(len(repository.list_all()))
    return registered


@app.get("/v1/parsers", response_model=List[ParserDefinition])
def list_parsers(
    vendor: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
):
    """Lists active registered parsers accessible to caller's tenant."""
    return repository.list_for_tenant(
        tenant_id=auth_ctx.tenant_id,
        include_global=True,
        vendor=vendor,
        format_type=format,
    )


@app.get("/v1/parsers/{parser_id}", response_model=ParserDefinition)
def get_parser(
    parser_id: str,
    version: Optional[str] = Query(None),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
):
    """Retrieves specific parser definition within tenant scope."""
    parser = repository.get(parser_id, version, tenant_id=auth_ctx.tenant_id)
    if not parser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parser '{parser_id}' not found",
        )
    return parser


@app.post("/v1/parsers/{parser_id}/disable")
def disable_parser(
    parser_id: str,
    version: Optional[str] = Query(None),
    auth_ctx: AuthContext = Depends(require_roles(Role.ADMIN.value)),
):
    """Disables a parser version within tenant scope."""
    success = registry_service.disable_parser(
        parser_id, version, tenant_id=auth_ctx.tenant_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parser '{parser_id}' not found",
        )
    REGISTRY_SIZE.set(len(repository.list_all()))
    return {"status": "disabled", "parser_id": parser_id}


@app.post("/v1/parsers/{parser_id}/enable")
def enable_parser(
    parser_id: str,
    version: Optional[str] = Query(None),
    auth_ctx: AuthContext = Depends(require_roles(Role.ADMIN.value)),
):
    """Enables a parser version within tenant scope."""
    success = registry_service.enable_parser(
        parser_id, version, tenant_id=auth_ctx.tenant_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parser '{parser_id}' not found",
        )
    REGISTRY_SIZE.set(len(repository.list_all()))
    return {"status": "active", "parser_id": parser_id}


@app.post("/v1/parsers/{parser_id}/replay", response_model=List[ParsedEvent])
def replay_events(
    parser_id: str,
    req: ReplayRequest,
    auth_ctx: AuthContext = Depends(
        require_roles(Role.ANALYST.value, Role.ADMIN.value)
    ),
):
    """Replays raw events against specified parser version within tenant scope."""
    REPLAY_TOTAL.inc(len(req.events))
    try:
        return replay_service.replay_events(
            parser_id, req.events, req.version, tenant_id=auth_ctx.tenant_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
