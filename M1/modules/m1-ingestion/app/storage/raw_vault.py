import asyncio
import gzip
import io
from typing import Any

import structlog
from minio import Minio

logger = structlog.get_logger(__name__)


class RawVault:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = False,
        default_bucket: str = "ulpf-raw",
    ):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.default_bucket = default_bucket
        self.client: Minio | None = None

    def connect(self) -> None:
        if self.client is None:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )

    def _ensure_bucket_sync(self, bucket_name: str) -> None:
        self.connect()
        assert self.client is not None
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)
            logger.info("Created MinIO bucket", bucket=bucket_name)

    async def ensure_bucket(self, bucket_name: str | None = None) -> None:
        target_bucket = bucket_name or self.default_bucket
        await asyncio.to_thread(self._ensure_bucket_sync, target_bucket)

    def _store_sync(self, bucket: str, object_key: str, payload_bytes: bytes) -> dict[str, Any]:
        self.connect()
        assert self.client is not None

        compressed_data = gzip.compress(payload_bytes)
        stream = io.BytesIO(compressed_data)
        size = len(compressed_data)

        self.client.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=stream,
            length=size,
            content_type="application/gzip",
        )
        return {
            "bucket": bucket,
            "object_key": object_key,
            "compressed_size": size,
            "original_size": len(payload_bytes),
        }

    async def store_raw_event(
        self, bucket: str, object_key: str, payload_bytes: bytes
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self._store_sync, bucket, object_key, payload_bytes)

    def _get_sync(self, bucket: str, object_key: str) -> bytes:
        self.connect()
        assert self.client is not None
        response = self.client.get_object(bucket, object_key)
        try:
            compressed_data = response.read()
            return gzip.decompress(compressed_data)
        finally:
            response.close()
            response.release_conn()

    async def get_raw_event(self, bucket: str, object_key: str) -> bytes:
        return await asyncio.to_thread(self._get_sync, bucket, object_key)

    def _health_sync(self, bucket: str) -> bool:
        try:
            self.connect()
            assert self.client is not None
            return bool(self.client.bucket_exists(bucket))
        except BaseException as e:
            logger.warning("MinIO health check failed", error=str(e))
            return False

    async def is_healthy(self, bucket: str | None = None) -> bool:
        target_bucket = bucket or self.default_bucket
        return await asyncio.to_thread(self._health_sync, target_bucket)
