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

users = [
    f"user-{i:03d}"
    for i in range(1, 21)
]

TOTAL_REQUESTS = 500

successful = 0
throttled = 0
latencies = []

request_distribution = Counter()

print("=" * 55)
print("PHISHGUARD - NORMAL WORKLOAD EXPERIMENT")
print("=" * 55)

for i in range(TOTAL_REQUESTS):

    # Randomly select a normal user
    user_id = random.choice(users)

    start = time.perf_counter()

    try:

        query = """
        SELECT TOP 10 *
        FROM c
        WHERE c.userId = @userId
        """

        parameters = [
            {
                "name": "@userId",
                "value": user_id
            }
        ]

        list(
            container.query_items(
                query=query,
                parameters=parameters,
                partition_key=user_id
            )
        )

        elapsed = (time.perf_counter() - start) * 1000

        successful += 1
        latencies.append(elapsed)

        request_distribution[user_id] += 1

    except CosmosHttpResponseError as e:

        if e.status_code == 429:
            throttled += 1
        else:
            print("Error:", e.status_code)

    if (i + 1) % 100 == 0:
        print(
            f"Completed {i + 1}/{TOTAL_REQUESTS} "
            f"| Successful: {successful} "
            f"| Throttled: {throttled}"
        )


print("\n" + "=" * 55)
print("NORMAL WORKLOAD RESULTS")
print("=" * 55)

print("Total requests :", TOTAL_REQUESTS)
print("Successful     :", successful)
print("Throttled      :", throttled)

if latencies:
    average_latency = sum(latencies) / len(latencies)

    print(
        "Average latency:",
        round(average_latency, 2),
        "ms"
    )

print("\nRequest distribution by user:")

for user, count in sorted(request_distribution.items()):
    print(f"{user}: {count}")

print("\nExperiment completed.")