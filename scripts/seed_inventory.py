import asyncio
import sys
sys.path.append(".")
from app.redis_client import init_sale_stock
from app.config import settings

async def main():
    await init_sale_stock(settings.sale_item_id, settings.sale_initial_stock)
    print(f"Seeded {settings.sale_item_id} with {settings.sale_initial_stock} units")

if __name__ == "__main__":
    asyncio.run(main())
