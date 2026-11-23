"""Verify spans for Saga operations without accessing MySQL or Redis."""
import pytest
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import store_manager


@pytest.mark.parametrize("method,path,controller,operation", [
    ("post", "/orders", "create_order", "orders.create"),
    ("get", "/orders/42", "get_order", "orders.get"),
    ("put", "/orders", "update_order", "orders.update"),
    ("delete", "/orders/42", "remove_order", "orders.delete"),
    ("put", "/stocks", "update_stock", "stocks.update"),
])
def test_saga_endpoint_continues_incoming_trace(monkeypatch, method, path, controller, operation):
    exporter = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(store_manager, controller, lambda *args: ({"status": "ok"}, 200))
    trace_id = "1234567890abcdef1234567890abcdef"
    parent_id = "1234567890abcdef"

    response = getattr(store_manager.app.test_client(), method)(path, json={}, headers={
        "traceparent": f"00-{trace_id}-{parent_id}-01"
    })

    assert response.status_code == 200
    finished = exporter.get_finished_spans()
    server = next(span for span in finished if span.kind == SpanKind.SERVER)
    business = next(span for span in finished if span.name == operation)
    assert server.context.trace_id == int(trace_id, 16)
    assert server.parent.span_id == int(parent_id, 16)
    assert business.parent.span_id == server.context.span_id
    assert business.resource.attributes["service.name"] == "store-manager"
