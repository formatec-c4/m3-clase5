import logging
import os
import time
from typing import Callable

from fastapi import Request
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def _resource(service_name: str) -> Resource:
    return Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": os.getenv("DEPLOYMENT_ENVIRONMENT", "docker-desktop"),
            "service.namespace": "formatec",
        }
    )


def setup_telemetry(app, service_name: str) -> logging.Logger:
    resource = _resource(service_name)

    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(insecure=True)))
    trace.set_tracer_provider(trace_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(insecure=True),
        export_interval_millis=5000,
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    LoggingInstrumentor().instrument(set_logging_format=False)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s service=%(name)s trace_id=%(otelTraceID)s span_id=%(otelSpanID)s %(message)s"
        )
    )
    root_logger.addHandler(console_handler)

    FastAPIInstrumentor.instrument_app(app)
    RequestsInstrumentor().instrument()

    meter = metrics.get_meter(service_name)
    request_counter = meter.create_counter(
        "demo_http_requests_total",
        description="Cantidad de requests atendidos por el servicio de demo",
    )
    request_latency = meter.create_histogram(
        "demo_http_request_duration_ms",
        description="Duracion de requests en milisegundos",
        unit="ms",
    )

    @app.middleware("http")
    async def telemetry_middleware(request: Request, call_next: Callable):
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        attrs = {
            "service.name": service_name,
            "http.route": request.url.path,
            "http.method": request.method,
            "http.status_code": response.status_code,
        }
        request_counter.add(1, attrs)
        request_latency.record(elapsed_ms, attrs)

        span_context = trace.get_current_span().get_span_context()
        trace_id = f"{span_context.trace_id:032x}" if span_context.trace_id else "none"
        logging.getLogger(service_name).info(
            "request method=%s path=%s status=%s duration_ms=%.2f trace_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            trace_id,
        )
        return response

    return logging.getLogger(service_name)
