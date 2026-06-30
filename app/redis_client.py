import redis.asyncio as redis
from app.config import settings

_pool: redis.Redis | None = None
_claim_sha: str | None = None

LUA_PATH = "app/lua/claim_inventory.lua"

async def get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=200,
        )
    return _pool

async def load_claim_script() -> str:
    global _claim_sha
    r = await get_redis()
    with open(LUA_PATH, "r") as f:
        script_body = f.read()
    _claim_sha = await r.script_load(script_body)
    return _claim_sha

async def get_claim_sha() -> str:
    if _claim_sha is None:
        return await load_claim_script()
    return _claim_sha

async def init_sale_stock(item_id: str, stock: int):
    r = await get_redis()
    await r.set(f"stock:{item_id}", stock)
    await r.delete(f"claimed:{item_id}")
