import os
import random
import uuid
import time
from collections import Counter
from datetime import datetime, timezone

from dotenv import load_dotenv
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

# --------------------------------
# Load Cosmos DB credentials
# --------------------------------

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

# --------------------------------
# Dataset configuration
# --------------------------------

TOTAL_RECORDS = 1000

users = [
    f"user-{i:03d}"
    for i in range(1, 21)
]

urls = [
    "https://google.com",
    "https://github.com",
    "https://microsoft.com",
    "https://amazon.com",
    "https://linkedin.com",
    "http://secure-login-example.com",
    "http://verify-account-example.com",
    "http://free-prize-example.com",
    "http://account-verification-example.com",
    "http://update-payment-example.com"
]

countries = [
    "India",
    "USA",
    "UK",
    "Germany",
    "Singapore"
]

user_counts = Counter()

# --------------------------------
# Generate records
# --------------------------------

print("Starting PhishGuard dataset generation...")
print(f"Target records: {TOTAL_RECORDS}")
print(f"Users: {len(users)}")
print("-" * 50)

for i in range(TOTAL_RECORDS):

    user_id = random.choice(users)

    # 75% legitimate, 25% phishing
    if random.random() < 0.75:
        verdict = "LEGITIMATE"
        risk_band = "LOW"
        explanation = "No suspicious URL patterns detected"
    else:
        verdict = "PHISHING"
        risk_band = "HIGH"
        explanation = "Suspicious URL patterns detected"

    document = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "url": random.choice(urls),
        "verdict": verdict,
        "confidenceScore": round(random.uniform(0.75, 0.99), 2),
        "riskBand": risk_band,
        "country": random.choice(countries),
        "explanation": explanation,
        "scannedAt": datetime.now(timezone.utc).isoformat()
    }

    # Insert with retry for throttling
    while True:

        try:

            container.create_item(body=document)
            break

        except CosmosHttpResponseError as e:

            if e.status_code == 429:

                print("429 throttled → waiting...")
                time.sleep(1)

            else:
                raise

    user_counts[user_id] += 1

    if (i + 1) % 100 == 0:
        print(f"Inserted {i + 1}/{TOTAL_RECORDS}")

# --------------------------------
# Results
# --------------------------------

print("\n" + "=" * 50)
print("DATASET GENERATION COMPLETE")
print("=" * 50)

print(f"Total records inserted: {TOTAL_RECORDS}")

print("\nDistribution by user:")

for user, count in sorted(user_counts.items()):
    print(f"{user}: {count}")

print("\nDatabase :", database.id)
print("Container:", container.id)
print("Partition:", "/userId")