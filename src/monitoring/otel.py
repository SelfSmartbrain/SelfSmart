"""
src/monitoring/otel.py

Purpose:
OpenTelemetry (OTel) configuration for distributed tracing across
the API, LangGraph workers, and Database.
"""

from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


def setup_opentelemetry(app: FastAPI) -> None:
    """Initialize OpenTelemetry tracing for the application."""
    settings = get_settings()
    
    # Do not crash if OTel endpoint is not provided, just skip
    otlp_endpoint = getattr(settings, "otlp_endpoint", None)
    if not otlp_endpoint:
        logger.warning("No OTLP endpoint configured. Distributed tracing disabled.")
        return
        
    resource = Resource(attributes={
        SERVICE_NAME: settings.project_name
    })

    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    logger.info("OpenTelemetry tracing configured successfully.")


def instrument_db(engine) -> None:
    """Instrument SQLAlchemy engine."""
    try:
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            enable_commenter=True,
            commenter_options={}
        )
    except Exception as e:
        logger.warning("Failed to instrument SQLAlchemy", error=str(e))
