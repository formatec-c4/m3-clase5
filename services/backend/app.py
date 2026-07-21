import os
import random

import requests
from fastapi import FastAPI, HTTPException

from common.telemetry import setup_telemetry

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "backend")
CATALOG_URL = os.getenv("CATALOG_URL", "http://catalog:8000")

app = FastAPI(title="Backend observability demo")
logger = setup_telemetry(app, SERVICE_NAME)


@app.get("/checkout")
def checkout():
    item_id = random.choice(["notebook", "monitor", "teclado"])
    logger.info("backend_checkout_started item=%s", item_id)
    try:
        response = requests.get(f"{CATALOG_URL}/price/{item_id}", timeout=3)
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", "unknown")
        logger.error(
            "backend_catalog_call_failed item=%s status=%s error_type=%s",
            item_id,
            status,
            exc.__class__.__name__,
        )
        raise HTTPException(status_code=502, detail="catalog unavailable") from None
    price = response.json()["price"]
    logger.info("backend_checkout_finished item=%s price=%s", item_id, price)
    return {"service": SERVICE_NAME, "item": item_id, "price": price}


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}
