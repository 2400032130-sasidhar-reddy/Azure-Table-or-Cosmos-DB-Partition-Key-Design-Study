import os
import random
import time
from collections import Counter

from dotenv import load_dotenv
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

load_dotenv()

endpoint = os.getenv("COSMOS_ENDPOINT")
key = os.getenv("COSMOS_KEY")

client = CosmosClient(
    endpoint,
    credential=key,
    connection_mode="Gateway"
)

database = client.get_database_client("phishguard-study-db")
container = database.get_container_client("scans")

# Same 20 users used in the normal workload
users = [f"user-{i:03d}" for i in range(1, 21)]

TOTAL_REQUESTS = 500

# 80% of requests will target one user
HOT_USER = "user-001"
HOT_REQUESTS = 400

successful = 0
throttled = 0
errors = 0

latencies = []
request_distribution = Counter()
ru_consumption = []

print("=" * 60)
print("PHISHGUARD - HOT / SKEWED WORKLOAD EXPERIMENT")
print("=" * 60)

# Create workload:
# 400 requests -> user-001
# 100 requests -> remaining users
workload = [HOT_USER] * HOT_REQUESTS

remaining_users = users[1:]

for _ in range(TOTAL_REQUESTS - HOT_REQUESTS):
    workload.append(random.choice(remaining_users))

# Shuffle so requests are not simply 400 consecutive requests
random.shuffle(workload)

for i, user_id in enumerate(workload):

    start = time.perf_counter()

    try:
        query = """
        SELECT TOP 10 *
        FROM c
        WHERE c.userId = @userId
        """

        parameters = [
            {"name": "@userId", "value": user_id}
        ]

        items = list(
            container.query_items(
                query=query,
                parameters=parameters,
                partition_key=user_id,
                populate_query_metrics=True
            )
        )

        elapsed = (time.perf_counter() - start) * 1000

        successful += 1
        latencies.append(elapsed)
        request_distribution[user_id] += 1

        # Try to capture RU charge
        response_headers = getattr(container.client_connection, "last_response_headers", {})

        if response_headers:
            ru = response_headers.get("x-ms-request-charge")

            if ru:
                ru_consumption.append(float(ru))

    except CosmosHttpResponseError as e:

        if e.status_code == 429:
            throttled += 1
            request_distribution[user_id] += 1
        else:
            errors += 1
            print(
                f"Error for {user_id}: "
                f"HTTP {e.status_code}"
            )

    if (i + 1) % 100 == 0:
        print(
            f"Completed {i + 1}/{TOTAL_REQUESTS} "
            f"| Successful: {successful} "
            f"| Throttled: {throttled}"
        )


print("\n" + "=" * 60)
print("HOT / SKEWED WORKLOAD RESULTS")
print("=" * 60)

print("Total requests :", TOTAL_REQUESTS)
print("Successful     :", successful)
print("Throttled      :", throttled)
print("Other errors   :", errors)

if latencies:
    print(
        "Average latency:",
        round(sum(latencies) / len(latencies), 2),
        "ms"
    )

if ru_consumption:
    print(
        "Average RU     :",
        round(sum(ru_consumption) / len(ru_consumption), 2)
    )

print("\nRequest distribution:")
for user, count in sorted(
    request_distribution.items(),
    key=lambda x: x[1],
    reverse=True
):
    print(f"{user}: {count}")

print("\n" + "=" * 60)
print("Experiment completed.")
print("=" * 60)