from fastapi import APIRouter, File, Header, Request, UploadFile, status

from app.transports.file_replay import FileReplayResponse, handle_file_replay_endpoint
from app.transports.http import EventIngestResponse, handle_http_ingest

router = APIRouter(prefix="/v1", tags=["Ingestion"])


@router.post(
    "/events",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EventIngestResponse,
    summary="Ingest raw log event via HTTP",
)
async def post_event(
    request: Request,
    authorization: str | None = Header(None, alias="Authorization"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    x_source_id: str | None = Header(None, alias="X-Source-ID"),
    x_source_type: str | None = Header(None, alias="X-Source-Type"),
    x_ingest_zone: str | None = Header(None, alias="X-Ingest-Zone"),
    x_collector_id: str | None = Header(None, alias="X-Collector-ID"),
) -> EventIngestResponse:
    return await handle_http_ingest(
        request=request,
        authorization=authorization,
        x_tenant_id=x_tenant_id,
        x_source_id=x_source_id,
        x_source_type=x_source_type,
        x_ingest_zone=x_ingest_zone,
        x_collector_id=x_collector_id,
    )


@router.post(
    "/replay/file",
    status_code=status.HTTP_200_OK,
    response_model=FileReplayResponse,
    summary="Replay a log file line-by-line",
)
async def replay_file_endpoint(
    request: Request,
    file: UploadFile = File(...),
    authorization: str | None = Header(None, alias="Authorization"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    x_source_id: str | None = Header(None, alias="X-Source-ID"),
) -> FileReplayResponse:
    return await handle_file_replay_endpoint(
        request=request,
        file=file,
        authorization=authorization,
        x_tenant_id=x_tenant_id,
        x_source_id=x_source_id,
    )
