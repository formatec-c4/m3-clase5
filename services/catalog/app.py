import os
import random
import time

from fastapi import FastAPI, HTTPException

from common.telemetry import setup_telemetry

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "catalog")
ERROR_RATE = float(os.getenv("ERROR_RATE", "0.2"))

PRICES = {
    "notebook": 1200,
    "monitor": 280,
    "teclado": 45,
}

app = FastAPI(title="Catalog observability demo")
logger = setup_telemetry(app, SERVICE_NAME)


@app.get("/price/{item_id}")
def price(item_id: str):
    simulated_ms = random.randint(40, 180)
    time.sleep(simulated_ms / 1000)
    if random.random() < ERROR_RATE:
        logger.error("catalog_price_failed item=%s latency_ms=%s reason=random_demo_error", item_id, simulated_ms)
        raise HTTPException(status_code=503, detail="random catalog error")
    price_value = PRICES.get(item_id, 99)
    logger.info("catalog_price_calculated item=%s price=%s latency_ms=%s", item_id, price_value, simulated_ms)
    return {"service": SERVICE_NAME, "item": item_id, "price": price_value}


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}
