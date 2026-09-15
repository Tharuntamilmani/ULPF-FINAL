import os
import json
import sqlite3
from typing import Optional, Dict, Any
import time
from collections import OrderedDict
import threading
import structlog

logger = structlog.get_logger("integration.idempotency")


class IdempotencyTracker:
    """
    Thread-safe deduplication tracker supporting volatile in-memory LRU
    and optional persistent durable storage (SQLite).
    Uses (tenant_id, raw_event_id) or (tenant_id, event_id) as compound key.
    """

    def __init__(
        self,
        capacity: int = 100000,
        ttl_seconds: int = 3600,
        db_path: Optional[str] = None,
    ):
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self.db_path = db_path
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()

        if self.db_path:
            self._init_db()

    def _init_db(self) -> None:
        if not self.db_path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS idempotency_log (
                    key TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    result_json TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS ix_idemp_tenant ON idempotency_log(tenant_id)")
            conn.commit()
        finally:
            conn.close()

    def _make_key(self, tenant_id: str, event_id: str) -> str:
        return f"{tenant_id}:{event_id}"

    def check_and_set(
        self,
        tenant_id: str,
        event_id: str,
        result_payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check if event has already been processed.
        Returns:
          True if event is NEW (first time seen, now recorded).
          False if event is a DUPLICATE (already seen and within TTL).
        """
        key = self._make_key(tenant_id, event_id)
        now = time.time()

        with self._lock:
            # 1. Check in-memory LRU cache
            if key in self._cache:
                entry = self._cache[key]
                if now - entry["timestamp"] < self.ttl_seconds:
                    self._cache.move_to_end(key)
                    logger.info("Duplicate event suppressed (in-memory)", key=key)
                    return False
                else:
                    del self._cache[key]

            # 2. Check durable SQLite store if configured
            if self.db_path:
                try:
                    conn = sqlite3.connect(self.db_path)
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT timestamp, result_json FROM idempotency_log WHERE key = ?",
                            (key,),
                        )
                        row = cursor.fetchone()
                        if row:
                            ts, r_json = row
                            if now - ts < self.ttl_seconds:
                                parsed_res = json.loads(r_json) if r_json else None
                                self._cache[key] = {"timestamp": ts, "result": parsed_res}
                                logger.info("Duplicate event suppressed (durable store)", key=key)
                                return False
                            else:
                                conn.execute("DELETE FROM idempotency_log WHERE key = ?", (key,))
                                conn.commit()
                    finally:
                        conn.close()
                except Exception as e:
                    logger.warning("Error reading durable idempotency store", error=str(e))

            # 3. New event: evict if over capacity
            if len(self._cache) >= self.capacity:
                self._cache.popitem(last=False)

            self._cache[key] = {
                "timestamp": now,
                "result": result_payload,
            }

            # 4. Write to durable SQLite store if configured
            if self.db_path:
                try:
                    res_str = json.dumps(result_payload) if result_payload is not None else None
                    conn = sqlite3.connect(self.db_path)
                    try:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO idempotency_log (key, tenant_id, event_id, timestamp, result_json)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (key, tenant_id, event_id, now, res_str),
                        )
                        conn.commit()
                    finally:
                        conn.close()
                except Exception as e:
                    logger.warning("Error writing to durable idempotency store", error=str(e))

            return True

    def get_cached_result(self, tenant_id: str, event_id: str) -> Optional[Dict[str, Any]]:
        key = self._make_key(tenant_id, event_id)
        now = time.time()
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if now - entry["timestamp"] < self.ttl_seconds:
                    return entry.get("result")

            if self.db_path:
                try:
                    conn = sqlite3.connect(self.db_path)
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT timestamp, result_json FROM idempotency_log WHERE key = ?",
                            (key,),
                        )
                        row = cursor.fetchone()
                        if row:
                            ts, r_json = row
                            if now - ts < self.ttl_seconds:
                                return json.loads(r_json) if r_json else None
                    finally:
                        conn.close()
                except Exception:
                    pass

        return None

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            if self.db_path:
                try:
                    conn = sqlite3.connect(self.db_path)
                    try:
                        conn.execute("DELETE FROM idempotency_log")
                        conn.commit()
                    finally:
                        conn.close()
                except Exception:
                    pass

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)

