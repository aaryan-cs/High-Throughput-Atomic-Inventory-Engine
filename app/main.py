import asyncio
import logging
import uuid
import time
import mlflow
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request

from app.config import settings
from app.schemas import ClaimRequest, ClaimResponse
from app.redis_client import get_redis, get_claim_sha, init_sale_stock
from app.fraud import fraud_check
from app.worker import run_worker_loop
from app.db import engine
from app.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flash-sale")

_worker_task: asyncio.Task | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await get_claim_sha()
    await init_sale_stock(settings.sale_item_id, settings.sale_initial_stock)

    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment("flash-sale-engine")
    except Exception:
        logger.warning("MLflow tracking unavailable; continuing without it")

    global _worker_task
    _worker_task = asyncio.create_task(run_worker_loop())

    logger.info("Flash sale engine started. Stock=%s", settings.sale_initial_stock)
    yield

    if _worker_task:
        _worker_task.cancel()

app = FastAPI(title="Flash Sale Inventory Engine", lifespan=lifespan)

@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-ms"] = f"{duration_ms:.2f}"
    if request.url.path == "/claim":
        try:
            with mlflow.start_run(run_name="api_request", nested=True):
                mlflow.log_metric("request_latency_ms", duration_ms)
                mlflow.log_metric("status_code", response.status_code)
        except Exception:
            pass
    return response

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/stock/{item_id}")
async def get_stock(item_id: str):
    r = await get_redis()
    stock = await r.get(f"stock:{item_id}")
    if stock is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item_id": item_id, "stock": int(stock)}

@app.post("/claim", response_model=ClaimResponse)
async def claim_item(payload: ClaimRequest, request: Request):
    fraud_score = await fraud_check(request, payload.user_id)

    r = await get_redis()
    sha = await get_claim_sha()
    order_id = str(uuid.uuid4())

    try:
        result = await r.evalsha(
            sha,
            2,
            f"stock:{payload.item_id}",
            f"claimed:{payload.item_id}",
            payload.user_id,
            order_id,
        )
    except Exception as e:
        logger.exception("Redis claim script failed")
        raise HTTPException(status_code=503, detail="Inventory service temporarily unavailable") from e

    if result == -3:
        raise HTTPException(status_code=404, detail="Sale not initialized for this item")
    if result == -2:
        return ClaimResponse(success=False, message="You have already claimed this item", fraud_score=fraud_score)
    if result == -1:
        return ClaimResponse(success=False, message="Sold out", remaining_stock=0, fraud_score=fraud_score)

    return ClaimResponse(
        success=True,
        message="Claim confirmed",
        order_id=order_id,
        remaining_stock=int(result),
        fraud_score=fraud_score,
    )
