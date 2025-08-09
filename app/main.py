import os, time, random, logging
from typing import Optional
from fastapi import FastAPI, Response, status
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

SERVICE = os.getenv("SERVICE_NAME", "app")
PROM_PORT = int(os.getenv("PROM_PORT", "8000"))
LOG_PATH = os.getenv("LOG_PATH", "/var/log/app/app.log")

# logging -> file (promtail scrapes bind mount)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
log = logging.getLogger(SERVICE)

# metrics
REQS = Counter("app_requests_total", "Total requests", ["route", "status"])
ERRS = Counter("app_errors_total", "Errors", ["route", "exc"])
LAT = Histogram("app_request_seconds", "Latency", ["route"])
HEALTH = Gauge("app_health", "1 if healthy else 0")
HEALTH.set(1)

# tracing
provider = TracerProvider(resource=Resource.create({"service.name": SERVICE}))
processor = BatchSpanProcessor(OTLPSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

ERROR_RATE = float(os.getenv("ERROR_RATE", "0.0"))
EXTRA_LAT = float(os.getenv("EXTRA_LATENCY_MS", "0")) / 1000.0

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/")
def root():
    return {"msg": "ok", "service": SERVICE}

@app.get("/work")
def do_work():
    with tracer.start_as_current_span("do_work"):
        t0 = time.time()
        time.sleep(EXTRA_LAT)
        # 5% base error + toggled error
        if random.random() < (0.05 + ERROR_RATE):
            ERRS.labels("/work", "boom").inc()
            log.error("processing failed")
            REQS.labels("/work", "500").inc()
            return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        log.info("processing ok")
        REQS.labels("/work", "200").inc()
        LAT.labels("/work").observe(time.time() - t0)
        return {"ok": True, "latency_ms": int((time.time() - t0)*1000)}

# Fault toggles (runtime)
@app.post("/faults/error")
def set_error(rate: Optional[float] = 0.5):
    global ERROR_RATE
    ERROR_RATE = max(0.0, min(1.0, rate or 0.0))
    log.warning(f"ERROR_RATE set to {ERROR_RATE}")
    return {"ERROR_RATE": ERROR_RATE}

@app.post("/faults/latency")
def set_latency(ms: Optional[int] = 200):
    global EXTRA_LAT
    EXTRA_LAT = max(0, (ms or 0)) / 1000.0
    log.warning(f"EXTRA_LATENCY_MS set to {EXTRA_LAT*1000}")
    return {"EXTRA_LATENCY_MS": int(EXTRA_LAT*1000)}

@app.post("/faults/reset")
def reset_faults():
    global ERROR_RATE, EXTRA_LAT
    ERROR_RATE, EXTRA_LAT = 0.0, 0.0
    log.warning("faults reset")
    return {"ERROR_RATE": ERROR_RATE, "EXTRA_LATENCY_MS": int(EXTRA_LAT*1000)}
