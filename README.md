# Azure Table or Cosmos DB Partition Key Design Study

## Project ID

24CC3046-P082

## Category

Database Design

## Project Title

**Azure Table or Cosmos DB Partition Key Design Study**

---

## 1. Project Overview

This project studies how partition-key design affects workload distribution and scalability in **Azure Cosmos DB for NoSQL**.

Instead of using a completely synthetic application, the study uses **PhishGuard AI**, a phishing URL detection application, as the source of realistic data and access patterns.

The experiment evaluates candidate partition keys under normal and skewed workloads and measures:

- Request distribution
- Request latency
- Request Units (RU)
- Successful requests
- HTTP 429 throttling
- Hot-partition risk

### Core Research Question

> How should we design partition keys for our application's access patterns while minimizing the risk of uneven workload distribution and hot partitions?

---

# 2. Project Methodology

The study follows:

**DATA → ACCESS → KEY → LOAD → HOT → OPTIMIZE**

### Step 1 — Data

Identify the data stored in Cosmos DB.

### Step 2 — Access

Identify how the application accesses the data.

### Step 3 — Key

Identify candidate partition-key fields.

### Step 4 — Load

Test the database under realistic workloads.

### Step 5 — Hot

Introduce workload skew and evaluate hot-partition risk.

### Step 6 — Optimize

Evaluate whether the partition-key design should be changed based on measured results.

---

# 3. Experimental Application — PhishGuard AI

PhishGuard AI is a phishing URL detection application.

The application processes URLs and predicts whether they are:

- Legitimate
- Phishing

The scan information is stored as JSON documents in Azure Cosmos DB.

### Relevant Data Fields

```text
userId
url
verdict
confidenceScore
riskBand
country
explanation
scannedAt