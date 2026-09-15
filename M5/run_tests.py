"""
Master Test Suite Runner for ULPF M5 Integration.
Executes all unit, routing, connector, failure, and integration tests.
"""
import os
import sys
import asyncio
import traceback

sys.path.insert(0, os.path.dirname(__file__))

from tests.unit.test_evaluator import (
    test_extract_field_value,
    test_compare_values,
    test_evaluate_condition_single,
    test_evaluate_condition_nested_all_any
)
from tests.routing.test_smart_router import (
    test_smart_router_matching,
    test_tenant_specific_routing
)
from tests.connectors.test_connectors import (
    test_opensearch_connector_idempotency_and_field_control,
    test_kafka_connector_ai_stream,
    test_http_connector_webhook,
    test_datalake_writer_partitioning
)
from tests.failure.test_retry_dlq import (
    test_retry_success_on_second_attempt,
    test_retry_exhaustion_promotes_to_dlq,
    test_permanent_error_promotes_immediately_to_dlq
)
from tests.integration.test_pipeline import (
    setup_m5_test_environment,
    test_dod_1_siem_indexing,
    test_dod_2_datalake_writing,
    test_dod_3_ai_stream,
    test_dod_4_multi_routing,
    test_dod_5_failure_and_dlq,
    test_dod_6_idempotency
)
from tests.integration.test_tenant_isolation import (
    setup_m5 as setup_tenant_m5,
    test_tenant_isolation_on_event_queries
)

passed_count = 0
failed_count = 0


def run_sync_test(test_func):
    global passed_count, failed_count
    name = test_func.__name__
    try:
        test_func()
        print(f"  [PASS] {name}")
        passed_count += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        traceback.print_exc()
        failed_count += 1


async def run_async_test(test_func):
    global passed_count, failed_count
    name = test_func.__name__
    try:
        await test_func()
        print(f"  [PASS] {name}")
        passed_count += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        traceback.print_exc()
        failed_count += 1


async def run_pipeline_test(test_func):
    global passed_count, failed_count
    name = test_func.__name__
    try:
        setup_m5_test_environment()
        await test_func()
        print(f"  [PASS] {name}")
        passed_count += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        traceback.print_exc()
        failed_count += 1


def main():
    global passed_count, failed_count
    print("==================================================")
    print("      ULPF M5 - Complete Test Suite Runner        ")
    print("==================================================")

    print("\n1. Unit Tests (Evaluator):")
    run_sync_test(test_extract_field_value)
    run_sync_test(test_compare_values)
    run_sync_test(test_evaluate_condition_single)
    run_sync_test(test_evaluate_condition_nested_all_any)

    print("\n2. Routing Tests (SmartRouter):")
    run_sync_test(test_smart_router_matching)
    run_sync_test(test_tenant_specific_routing)

    print("\n3. Connector Tests:")
    asyncio.run(run_async_test(test_opensearch_connector_idempotency_and_field_control))
    asyncio.run(run_async_test(test_kafka_connector_ai_stream))
    asyncio.run(run_async_test(test_http_connector_webhook))
    asyncio.run(run_async_test(test_datalake_writer_partitioning))

    print("\n4. Failure Handling & Retry / DLQ Tests:")
    asyncio.run(run_async_test(test_retry_success_on_second_attempt))
    asyncio.run(run_async_test(test_retry_exhaustion_promotes_to_dlq))
    asyncio.run(run_async_test(test_permanent_error_promotes_immediately_to_dlq))

    print("\n5. Integration Tests (Definition of Done Requirements 1-6):")
    asyncio.run(run_pipeline_test(test_dod_1_siem_indexing))
    asyncio.run(run_pipeline_test(test_dod_2_datalake_writing))
    asyncio.run(run_pipeline_test(test_dod_3_ai_stream))
    asyncio.run(run_pipeline_test(test_dod_4_multi_routing))
    asyncio.run(run_pipeline_test(test_dod_5_failure_and_dlq))
    asyncio.run(run_pipeline_test(test_dod_6_idempotency))

    print("\n6. Tenant Isolation Security Tests:")
    setup_tenant_m5()
    asyncio.run(run_async_test(test_tenant_isolation_on_event_queries))

    print("\n==================================================")
    print(f" Summary: {passed_count} Passed, {failed_count} Failed")
    print("==================================================")

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
