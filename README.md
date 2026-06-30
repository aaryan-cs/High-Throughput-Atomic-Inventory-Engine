# High-Throughput Atomic Inventory Engine

A high-concurrency distributed microservice designed to handle extreme burst-traffic events (e.g., flash sales, ticket drops) without inventory overselling or database lock contention. 

This project solves the classic "Read-Modify-Write" race condition by offloading hot-path inventory checks to a single-threaded Redis instance, while asynchronously batching confirmed orders into PostgreSQL.

## 🚀 Architecture & Core Features

* **Atomic Redis Transactions:** Utilizes single-threaded Lua scripts for uninterruptible `check-and-decrement` operations, mathematically guaranteeing zero inventory overselling under high concurrency.
* **Database Protection:** PostgreSQL is entirely removed from the synchronous request path. A background worker drains the Redis queue and bulk-inserts orders via `INSERT ... ON CONFLICT DO NOTHING`, utilizing unique constraints to guarantee strict idempotency.
* **Bot Mitigation:** Includes a dependency-injected sliding-window rate limiter utilizing Redis Sorted Sets (`ZSET`) to instantly block high-velocity IP traffic.
* **Fully Asynchronous:** End-to-end async implementation using FastAPI, `redis.asyncio`, and `asyncpg` to maximize I/O throughput and efficiently yield the Python event loop.

## 🛠️ Tech Stack

* **Backend:** Python 3.12, FastAPI, Uvicorn
* **In-Memory Datastore / Queue:** Redis, Lua Scripting
* **Database:** PostgreSQL, SQLAlchemy 2.0, asyncpg
* **Observability:** MLflow (Fail-open integration)
* **Infrastructure:** Docker, Docker Compose
* **Load Testing:** Locust

## 📊 Performance Benchmark

Tested locally simulating 10,000 concurrent users attempting to claim 100 limited-stock items with near-zero think time.

* **Total Requests:** [e.g., 12,450]
* **Failures:** 0
* **Oversold Items:** 0 (Database verified exactly 100 records)
* **Requests Per Second (RPS):** [e.g., 850.5]
* **Median Latency:** [e.g., 25ms]
* **p99 Latency:** [e.g., 85ms]

## ⚙️ Quickstart

**1. Start the cluster**
Start the API, Redis, Postgres, and MLflow containers in the background:
```bash
docker-compose up --build -d
```
**2. Run the load test**
Simulate a massive traffic spike using Locust:
```bash
locust -f locust/locustfile.py --host http://localhost:8000 -u 10000 -r 500 --run-time 1m --headless
```
**3. Verify zero overselling**
Query the database to prove the strict 100-item limit was enforced:
```bash
docker exec -it flash-sale-engine-postgres-1 psql -U flash -d flashsale -c "SELECT COUNT(*) FROM orders WHERE status = 'CONFIRMED';"
```
**4. View Dashboards**

    API Documentation: http://localhost:8000/docs

    MLflow Observability: http://localhost:5000

## Repository Structure
```plaintext
├── app/
│   ├── lua/
│   │   └── claim_inventory.lua   # Atomic check-and-decrement logic
│   ├── main.py                   # FastAPI entry point
│   ├── worker.py                 # Async Postgres batch-insert loop
│   ├── fraud.py                  # Redis ZSET rate limiter
│   └── ...
├── locust/
│   └── locustfile.py             # Load test simulation
├── scripts/
│   └── seed_inventory.py         # Helper to reset stock
├── docker-compose.yml
└── Dockerfile
```
