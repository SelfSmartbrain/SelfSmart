from prometheus_client import Counter, Histogram, make_asgi_app
from fastapi import Request
import time

# HTTP Metrics
REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP Requests',
    ['method', 'endpoint', 'http_status']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 'HTTP Request Latency',
    ['method', 'endpoint']
)

# LLM Metrics
LLM_LATENCY = Histogram(
    'llm_request_duration_seconds', 'LLM Request Latency',
    ['provider', 'model']
)
TOKEN_USAGE = Counter(
    'llm_token_usage_total', 'Total LLM Token Usage',
    ['provider', 'model', 'token_type']  # token_type: prompt or completion
)

# Learning Metrics
LEARNING_PAGES_PROCESSED = Counter(
    'learning_pages_processed_total', 'Total pages processed during learning',
    ['source_type']
)
KNOWLEDGE_CHUNKS_ADDED = Counter(
    'knowledge_chunks_added_total', 'Total knowledge chunks added to vector store'
)

def instrument_app(app):
    """
    Mount Prometheus metrics endpoint to the FastAPI app.
    """
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start_time = time.time()
        method = request.method
        endpoint = request.url.path

        response = await call_next(request)

        status_code = response.status_code
        latency = time.time() - start_time

        REQUEST_COUNT.labels(method=method, endpoint=endpoint, http_status=status_code).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)

        return response
