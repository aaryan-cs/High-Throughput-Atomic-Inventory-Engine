import uuid
import random
from locust import HttpUser, task, between, events

ITEM_ID = "jersey-2026-ltd"

class FlashSaleUser(HttpUser):
    wait_time = between(0.01, 0.05)

    def on_start(self):
        self.user_id = f"user-{uuid.uuid4()}"

    @task
    def claim_item(self):
        headers = {
            "User-Agent": "LocustLoadTest/1.0 (compatible; stress-bot)",
            "Accept-Language": "en-US",
            "X-Forwarded-For": f"10.0.{random.randint(0,255)}.{random.randint(0,255)}",
        }
        payload = {"user_id": self.user_id, "item_id": ITEM_ID}

        with self.client.post("/claim", json=payload, headers=headers, catch_response=True) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") or data.get("message") in ("Sold out", "You have already claimed this item"):
                    resp.success()
                else:
                    resp.failure(f"Unexpected response body: {data}")
            else:
                resp.failure(f"HTTP {resp.status_code}: {resp.text}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats.total
    print("\n===== FLASH SALE LOAD TEST SUMMARY =====")
    print(f"Total requests:      {stats.num_requests}")
    print(f"Total failures:      {stats.num_failures}")
    print(f"RPS:                 {stats.total_rps:.2f}")
    print(f"Median latency (ms): {stats.median_response_time}")
    print(f"95th pct (ms):       {stats.get_response_time_percentile(0.95)}")
    print(f"99th pct (ms):       {stats.get_response_time_percentile(0.99)}")
    print("=========================================\n")
