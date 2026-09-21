"""
ULPF — M1->M2 Consumer Bridge Runner.
Runs M1RawEventConsumer with automatic reconnect on transient network/broker interruptions.
"""

import asyncio
import os
import sys

sys.path.insert(0, "E:/ULPF")

from integration.consumers.m1_raw_consumer import M1RawEventConsumer

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
M2_BASE_URL = os.getenv("M2_BASE_URL", "http://127.0.0.1:18082")


async def main():
    while True:
        try:
            consumer = M1RawEventConsumer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                m2_base_url=M2_BASE_URL,
            )
            await consumer.start()
        except BaseException as e:
            print(f"[Bridge Runner] Consumer exited with error: {e}. Reconnecting in 1s...", flush=True)
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
