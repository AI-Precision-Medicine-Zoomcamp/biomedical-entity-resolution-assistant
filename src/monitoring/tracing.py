from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
import logfire

# Global Tracer
_tracer = None

def get_tracer():
    global _tracer
    if _tracer is None:
        # Initialize and configure Logfire
        logfire.configure(
            service_name="biomedical-entity-resolution-assistant",
            service_version="0.1.0"
        )
        
        # We also get the tracer via standard OpenTelemetry
        _tracer = trace.get_tracer("biomedical.resolver")
        
    return _tracer
