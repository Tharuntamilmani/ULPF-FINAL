import asyncio
import json
import sys

from aiokafka import AIOKafkaConsumer

# Force UTF-8 stdout formatting on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def run_consumer(bootstrap_servers: str = "localhost:9092", topic: str = "ulpf.raw"):
    print(f"[INFO] Connecting to Kafka topic '{topic}' at {bootstrap_servers}...")
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="m1-demo-group",
        auto_offset_reset="earliest",
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )

    await consumer.start()
    print("[INFO] Consumer active. Waiting for RawEventEnvelope messages (Ctrl+C to stop)...")
    try:
        async for msg in consumer:
            envelope = msg.value
            print("\n=================== RawEventEnvelope Received ===================")
            print(f"Raw Event ID:  {envelope.get('raw_event_id')}")
            print(f"Tenant ID:     {envelope.get('tenant_id')}")
            print(f"Source ID:     {envelope.get('source_id')}")
            print(f"Received At:   {envelope.get('received_at')}")
            print(f"Transport:     {envelope.get('transport')}")
            print(f"SHA-256 Hash:  {envelope.get('integrity', {}).get('hash')}")
            print(f"MinIO Key:     {envelope.get('raw_storage', {}).get('object_key')}")
            print(f"Raw Data:      {envelope.get('payload', {}).get('data')[:100]}...")
            print("==================================================================")
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\nStopping consumer...")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    servers = sys.argv[1] if len(sys.argv) > 1 else "localhost:29092"
    asyncio.run(run_consumer(servers))
