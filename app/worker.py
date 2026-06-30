import asyncio
import json
import logging
import time
import mlflow
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.db import AsyncSessionLocal
from app.models import Order
from app.redis_client import get_redis
from app.config import settings

logger = logging.getLogger("worker")
QUEUE_KEY = "orders:queue"

async def drain_batch() -> int:
    r = await get_redis()
    batch_size = settings.worker_batch_size

    raw_items = await r.lpop(QUEUE_KEY, batch_size)
    if not raw_items:
        return 0

    orders = [json.loads(item) for item in raw_items]

    rows = [
        {
            "order_id": o["order_id"],
            "user_id": o["user_id"],
            "item_id": o["item_id"].replace("stock:", ""),
            "status": "CONFIRMED",
        }
        for o in orders
    ]

    start = time.perf_counter()
    async with AsyncSessionLocal() as session:
        try:
            stmt = pg_insert(Order).values(rows)
            stmt = stmt.on_conflict_do_nothing(index_elements=["order_id"])
            await session.execute(stmt)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Worker batch insert failed, requeueing batch")
            if raw_items:
                await r.rpush(QUEUE_KEY, *raw_items)
            raise

    latency_ms = (time.perf_counter() - start) * 1000
    try:
        with mlflow.start_run(run_name="worker_batch_persist", nested=True):
            mlflow.log_metric("batch_size", len(rows))
            mlflow.log_metric("db_write_latency_ms", latency_ms)
    except Exception:
        pass

    logger.info(f"Persisted {len(rows)} orders in {latency_ms:.2f}ms")
    return len(rows)

async def run_worker_loop():
    interval = settings.worker_interval_ms / 1000
    logger.info("Order drain worker started")
    while True:
        try:
            n = await drain_batch()
            if n == 0:
                await asyncio.sleep(interval)
        except Exception:
            logger.exception("Worker loop error, backing off")
            await asyncio.sleep(1)
