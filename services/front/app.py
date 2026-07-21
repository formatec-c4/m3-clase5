import os

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from common.telemetry import setup_telemetry

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "front")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

app = FastAPI(title="Front observability demo")
logger = setup_telemetry(app, SERVICE_NAME)


@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FormaTEC Observabilidad</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 40px; max-width: 760px; color: #172026; }
    button { font-size: 16px; padding: 10px 14px; cursor: pointer; }
    pre { background: #111827; color: #d1fae5; padding: 16px; overflow: auto; min-height: 120px; }
  </style>
</head>
<body>
  <h1>Demo OpenTelemetry</h1>
  <p>Este front llama al backend, y el backend llama a otro backend. Cada click genera trazas y logs correlacionados.</p>
  <button onclick="runDemo()">Generar request</button>
  <pre id="out">Esperando...</pre>
  <script>
    async function runDemo() {
      const out = document.getElementById('out');
      out.textContent = 'Llamando...';
      const res = await fetch('/api/demo');
      out.textContent = JSON.stringify(await res.json(), null, 2);
    }
  </script>
</body>
</html>
"""


@app.get("/api/demo")
def demo():
    logger.info("front_starting_backend_call")
    try:
        response = requests.get(f"{BACKEND_URL}/checkout", timeout=3)
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", "unknown")
        logger.error(
            "front_backend_call_failed status=%s error_type=%s",
            status,
            exc.__class__.__name__,
        )
        raise HTTPException(status_code=502, detail="backend unavailable") from None
    payload = response.json()
    logger.info("front_finished_backend_call item=%s price=%s", payload["item"], payload["price"])
    return {"front": "ok", "backend": payload}


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}
