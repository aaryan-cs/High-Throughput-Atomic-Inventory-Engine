import time
import mlflow
from fastapi import Request, HTTPException
from app.redis_client import get_redis
from app.config import settings

async def fraud_check(request: Request, user_id: str) -> float:
    start = time.perf_counter()
    r = await get_redis()
    client_ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")

    score = 0.0
    window = settings.fraud_ip_velocity_window_sec
    max_allowed = settings.fraud_ip_velocity_max
    now = time.time()
    key = f"fraud:ip_velocity:{client_ip}"

    pipe = r.pipeline()
    pipe.zadd(key, {f"{now}:{user_id}": now})
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zcard(key)
    pipe.expire(key, window * 2)
    _, _, request_count, _ = await pipe.execute()

    if request_count > max_allowed:
        score += 0.6

    if not ua or "bot" in ua.lower() or len(ua) < 10:
        score += 0.3

    if not request.headers.get("accept-language"):
        score += 0.1

    score = min(score, 1.0)
    latency_ms = (time.perf_counter() - start) * 1000

    try:
        with mlflow.start_run(run_name="fraud_inference", nested=True):
            mlflow.log_metric("fraud_score", score)
            mlflow.log_metric("fraud_latency_ms", latency_ms)
            mlflow.log_metric("ip_request_count_window", request_count)
    except Exception:
        pass

    if score >= 0.85:
        raise HTTPException(status_code=403, detail="Request flagged as high-risk by fraud detection")

    return score
