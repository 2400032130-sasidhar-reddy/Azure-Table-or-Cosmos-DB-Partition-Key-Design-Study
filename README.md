# Azure Table or Cosmos DB Partition Key Design Study

> **Experimental evaluation of partition-key design, workload distribution, and hot-partition risk using Azure Cosmos DB for NoSQL and a real application workload.**

**Project ID:** `24CC3046-P082`  
**Category:** Database Design  
**Experimental Application:** PhishGuard AI  
**Database:** Azure Cosmos DB for NoSQL  
**Primary Experimental Partition Key:** `/userId`

---

## Table of Contents

- [1. Project Overview](#1-project-overview)
- [2. Research Question](#2-research-question)
- [3. Objectives](#3-objectives)
- [4. Why PhishGuard AI](#4-why-phishguard-ai)
- [5. System Data Model](#5-system-data-model)
- [6. Access Patterns](#6-access-patterns)
- [7. Partition-Key Design](#7-partition-key-design)
- [8. Cosmos DB Architecture](#8-cosmos-db-architecture)
- [9. Azure Environment](#9-azure-environment)
- [10. Step-by-Step Azure Setup](#10-step-by-step-azure-setup)
- [11. Local Project Setup](#11-local-project-setup)
- [12. Dataset Generation](#12-dataset-generation)
- [13. Experiment 1 — Normal Workload](#13-experiment-1--normal-workload)
- [14. Experiment 2 — Skewed Workload](#14-experiment-2--skewed-workload)
- [15. Results](#15-results)
- [16. Hot-Partition Analysis](#16-hot-partition-analysis)
- [17. Important Technical Distinctions](#17-important-technical-distinctions)
- [18. Controlled Stress Testing](#18-controlled-stress-testing)
- [19. Candidate Partition-Key Comparison](#19-candidate-partition-key-comparison)
- [20. Reproducibility Workflow](#20-reproducibility-workflow)
- [21. Project Structure](#21-project-structure)
- [22. Security](#22-security)
- [23. Engineering Lessons](#23-engineering-lessons)
- [24. Future Work](#24-future-work)
- [25. Final Conclusion](#25-final-conclusion)

---

## 1. Project Overview

This project investigates how partition-key design influences the behavior of a distributed application workload in **Azure Cosmos DB for NoSQL**.

Rather than evaluating partition keys only from a theoretical perspective, the study uses **PhishGuard AI**, a phishing URL detection application, as the source of realistic scan data and application access patterns.

The experiment follows a measurement-driven workflow:

```text
DATA
  ↓
ACCESS PATTERNS
  ↓
CANDIDATE KEYS
  ↓
DATA DISTRIBUTION
  ↓
WORKLOAD DISTRIBUTION
  ↓
CONTROLLED LOAD
  ↓
LATENCY / RU / 429
  ↓
HOT-PARTITION ANALYSIS
  ↓
ENGINEERING DECISION
```

The initial experimental container uses `/userId` as its partition key.

---

## 2. Research Question

> **How should we design partition keys for our application's access patterns while minimizing the risk of uneven workload distribution and hot partitions?**

The study focuses on a practical database-design problem:

- Which fields represent meaningful access patterns?
- How evenly does each candidate distribute data?
- How evenly does real workload distribute requests?
- What happens when traffic becomes highly skewed?
- How do latency and RU consumption behave?
- Does increased demand eventually produce throttling?
- What evidence is required before calling a workload a hot-partition problem?

---

## 3. Objectives

### Primary objectives

1. Identify important application access patterns.
2. Derive candidate partition-key fields from those patterns.
3. Examine cardinality and data distribution.
4. Establish a normal-workload baseline.
5. Introduce intentionally skewed traffic.
6. Measure latency, RU consumption, success rate, and HTTP 429 responses.
7. Distinguish workload skew from confirmed physical hot-partition contention.
8. Perform controlled stress testing.
9. Compare alternative partition-key designs using measured evidence.

### Design principle

> **A partition key is a workload-design decision, not simply a field-selection decision.**

---

## 4. Why PhishGuard AI?

PhishGuard AI is a phishing URL detection application that processes URLs and stores scan results.

It provides a realistic workload because scan records naturally support several application queries:

- User scan history
- Risk-based security analysis
- Regional analytics
- Scan-level reporting

Using a real application's data model makes the experiment more representative than a purely synthetic database benchmark.

### Scope

PhishGuard AI is the **experimental workload source**.

The primary subject of this project is:

> **Azure Cosmos DB partition-key design and workload behavior.**

---

## 5. System Data Model

The scan document stored in Cosmos DB contains fields such as:

```json
{
  "id": "scan-000001",
  "userId": "user-001",
  "url": "https://example.com",
  "verdict": "LEGITIMATE",
  "confidenceScore": 0.94,
  "riskBand": "LOW",
  "country": "India",
  "explanation": "No significant phishing indicators detected.",
  "scannedAt": "2026-09-25T12:30:00Z"
}
```

### Important fields

| Field | Purpose |
|---|---|
| `userId` | Identify the user who performed the scan |
| `url` | Scanned URL |
| `verdict` | Phishing or legitimate prediction |
| `confidenceScore` | Model confidence |
| `riskBand` | Risk classification |
| `country` | Regional analysis |
| `explanation` | Prediction explanation |
| `scannedAt` | Scan timestamp |

---

## 6. Access Patterns

The application was analyzed before selecting the initial partition key.

| Application access pattern | Candidate key |
|---|---|
| User scan history | `/userId` |
| Security dashboard by risk | `/riskBand` |
| Regional analytics | `/country` |

### Evaluation pipeline

```text
Access Pattern
      ↓
Candidate Field
      ↓
Cardinality
      ↓
Data Distribution
      ↓
Request Distribution
      ↓
Performance Testing
```

The candidate field is therefore treated as a **hypothesis to validate**, not an automatically correct partition key.

---

## 7. Partition-Key Design

The initial experimental container was created with:

```text
Partition Key:
 /userId
```

### Why `/userId`?

The application frequently needs user-specific scan history.

It also gives the experiment a controllable workload dimension: requests can be distributed across many users and then intentionally concentrated on one user.

### Important consideration

A field can have many possible values and still produce a hot workload if the application repeatedly targets only a small subset of those values.

Therefore:

```text
High cardinality ≠ automatically safe from hot workloads
```

Partition-key selection must consider both **data distribution** and **request distribution**.

---

## 8. Cosmos DB Architecture

The experimental data hierarchy is:

```text
Azure Cosmos DB Account
│
└── Database: phishguard-study-db
    │
    └── Container: scans
        │
        ├── Partition Key: /userId
        │
        └── JSON scan documents
            ├── userId
            ├── url
            ├── verdict
            ├── confidenceScore
            ├── riskBand
            ├── country
            ├── explanation
            └── scannedAt
```

### Conceptual partitioning model

```text
                    Cosmos DB Container
                           │
                     Partition Key
                        /userId
                           │
          ┌────────────────┼────────────────┐
          ↓                ↓                ↓
      user-001         user-002         user-003
          ↓                ↓                ↓
       scans             scans             scans
```

The application supplies the partition-key value with targeted queries so Cosmos DB can route the request efficiently.

---

## 9. Azure Environment

The baseline experiment was performed using:

| Component | Configuration |
|---|---|
| API | Azure Cosmos DB for NoSQL |
| Region | Central India |
| Database | `phishguard-study-db` |
| Container | `scans` |
| Partition key | `/userId` |
| Throughput | 400 RU/s manual |
| Dataset | ~1,000 scan records |
| Users | 20 |
| Primary workload | 500 requests |

---

## 10. Step-by-Step Azure Setup

### 10.1 Open Azure Portal

Open the Azure Portal and search for:

```text
Azure Cosmos DB
```

Select:

```text
Azure Cosmos DB for NoSQL
```

Choose:

```text
Create
```

---

### 10.2 Configure the Cosmos DB account

Use the following baseline configuration:

| Setting | Value |
|---|---|
| Subscription | Azure for Students |
| Resource Group | `phishguard-rg` |
| Account name | Globally unique account name |
| API | Azure Cosmos DB for NoSQL |
| Region | Central India |
| Availability Zones | Disabled for this study |
| Geo-redundancy | Disabled |
| Multi-region writes | Disabled |

Example account name:

```text
phishguard-cosmos-2026
```

The account name must be globally unique.

---

### 10.3 Configure throughput

For the baseline experiment:

```text
Capacity mode:
Provisioned throughput

Container throughput:
400 RU/s
```

The experiment intentionally uses a fixed throughput level so workload behavior can be measured consistently.

---

### 10.4 Create the account

Select:

```text
Review + create
```

After validation succeeds:

```text
Create
```

Wait until the deployment completes.

---

### 10.5 Open Data Explorer

Open the Cosmos DB account.

Navigate to:

```text
Data Explorer
```

Select:

```text
New Container
```

---

### 10.6 Create the database

Use:

```text
Database ID:
phishguard-study-db
```

---

### 10.7 Create the container

Use:

```text
Container ID:
scans
```

Partition key:

```text
/userId
```

Throughput:

```text
400 RU/s
```

The resulting structure should be:

```text
phishguard-study-db
└── scans
    └── Partition Key: /userId
```

### Critical design decision

The partition-key path is part of the container design.

For this experiment, do not create the baseline container with:

```text
/riskBand
/country
```

The initial experiment specifically evaluates:

```text
/userId
```

---

### 10.8 Retrieve connection credentials

Navigate to the account's key/connection settings and obtain:

```text
URI
PRIMARY KEY
```

These credentials are used only locally.

**Never commit the primary key to GitHub.**

---

## 11. Local Project Setup

### 11.1 Clone the repository

```bash
git clone https://github.com/2400032130-sasidhar-reddy/Azure-Table-or-Cosmos-DB-Partition-Key-Design-Study.git
cd Azure-Table-or-Cosmos-DB-Partition-Key-Design-Study
```

### 11.2 Create a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 11.3 Install dependencies

```bash
pip install -r requirements.txt
```

Current dependencies:

```text
azure-cosmos==4.17.1
python-dotenv==1.2.3
```

---

## 12. Environment Configuration

Create a local `.env` file.

Use `.env.example` as the template:

```env
COSMOS_ENDPOINT=https://YOUR-COSMOS-ACCOUNT.documents.azure.com:443/
COSMOS_KEY=YOUR_PRIMARY_KEY

COSMOS_DATABASE=phishguard-study-db
COSMOS_CONTAINER=scans
```

### Security rule

`.env` is intentionally ignored by Git.

Verify:

```bash
git status
```

The actual `.env` file must not appear as a file to be committed.

---

## 13. Dataset Generation

The project contains:

```text
generate_scand.py
```

The script generates realistic scan documents and inserts them into the Cosmos DB container.

Run:

```bash
python generate_scand.py
```

### Dataset characteristics

The experiment uses approximately:

```text
1,000 scan records
20 users
Multiple countries
Multiple risk bands
Phishing and legitimate verdicts
```

Observed user distribution in the baseline dataset:

| User | Records |
|---|---:|
| user-001 | 56 |
| user-002 | 41 |
| user-003 | 52 |
| user-004 | 55 |
| user-005 | 37 |
| user-006 | 47 |
| user-007 | 50 |
| user-008 | 54 |
| user-009 | 64 |
| user-010 | 48 |
| user-011 | 54 |
| user-012 | 49 |
| user-013 | 59 |
| user-014 | 38 |
| user-015 | 49 |
| user-016 | 56 |
| user-017 | 44 |
| user-018 | 46 |
| user-019 | 54 |
| user-020 | 47 |

This provides a non-uniform but broadly distributed dataset for the initial workload study.

---

## 14. Experiment 1 — Normal Workload

Script:

```text
normal_workload.py
```

Run:

```bash
python normal_workload.py
```

### Workload definition

```text
Total requests : 500
Users          : 20
Partition key  : /userId
```

Requests were randomly distributed across the 20 users.

### Results

| Metric | Normal workload |
|---|---:|
| Total requests | 500 |
| Successful | 500 |
| Throttled | 0 |
| Average latency | 58.14 ms |

### Interpretation

The initial `/userId` design successfully handled the tested normal workload.

This result establishes a **baseline**.

It does not prove that `/userId` is universally optimal.

---

## 15. Experiment 2 — Skewed Workload

Script:

```text
hot_workload.py
```

Run:

```bash
python hot_workload.py
```

The experiment intentionally concentrates traffic on one partition-key value.

### Workload definition

```text
Total requests:
500

Requests to user-001:
400

Requests to other users:
100
```

Therefore:

```text
user-001 = 80% of all requests
```

---

## 16. Results

### Baseline vs. skewed workload

| Metric | Normal | Skewed |
|---|---:|---:|
| Requests | 500 | 500 |
| Workload distribution | Across 20 users | 80% → `user-001` |
| Successful | 500 | 500 |
| HTTP 429 | 0 | 0 |
| Average latency | 58.14 ms | 51.34 ms |
| Average RU | — | 3.09 RU/request |

### Skewed request distribution

```text
user-001      400
other users   100
-------------------
total         500
```

This means:

```text
400 / 500 = 80%
```

of the requests were directed to one partition-key value.

---

## 17. Hot-Partition Analysis

The skewed experiment successfully demonstrated **workload concentration on a single logical partition-key value**.

However:

```text
500 requests
500 successful
0 HTTP 429
```

were observed.

Therefore, the experiment did **not** conclusively demonstrate physical-partition contention.

### Correct engineering interpretation

> The experiment demonstrated severe workload skew toward a single logical partition. However, under the tested 500-request workload and configured throughput, no throttling occurred, so physical hot-partition contention was not conclusively demonstrated.

This distinction is important.

A workload can be highly skewed without immediately producing throttling.

---

## 18. Important Technical Distinctions

### 18.1 Logical partition

Items sharing the same logical partition-key value belong to the same logical partition.

For the experiment:

```text
userId = user-001
```

identifies one logical partition-key value.

### 18.2 Physical partition

Azure Cosmos DB distributes logical partitions across physical storage/throughput infrastructure.

The application does not directly choose the physical partition.

### 18.3 Workload skew

Workload skew means requests are disproportionately concentrated on one or a small number of partition-key values.

Example:

```text
user-001 → 80%
all other users → 20%
```

### 18.4 Hot partition

A hot-partition condition is a stronger operational conclusion: a small subset of partition-key ranges consumes a disproportionate amount of available throughput.

Therefore:

```text
Workload skew
      ≠
Confirmed physical hot partition
      ≠
Automatic throttling
```

### 18.5 HTTP 429

HTTP `429` indicates that the service is rate-limiting a request because the available throughput cannot immediately satisfy the workload.

### 18.6 RU

A Request Unit (RU) is the normalized measure of database work consumed by operations.

`RU/request` is different from provisioned `RU/s`.

---

## 19. Controlled Stress Testing

The 500-request experiment was intentionally conservative.

The next stage is to progressively increase the workload while preserving approximately the same skew.

### Proposed sequence

```text
500 requests
     ↓
1,000 requests
     ↓
2,000 requests
     ↓
Higher levels if required
```

Maintain:

```text
~80% → user-001
~20% → other users
```

### Metrics

At every load level record:

- Total requests
- Successful requests
- HTTP 429 responses
- Average latency
- RU/request
- Request distribution
- Throughput behavior

### Expected analysis

```text
Increasing Load
       ↓
Increasing Demand
       ↓
Observe RU / Latency
       ↓
Check 429 Responses
       ↓
Inspect Partition-Level Metrics
       ↓
Determine Whether Contention Emerges
```

The purpose is not to force a failure artificially, but to identify the point at which the selected design becomes constrained under the tested workload.

---

## 20. Candidate Partition-Key Comparison

The study identified three candidates:

```text
/userId
/riskBand
/country
```

They should be compared using the same evaluation framework.

| Criterion | `/userId` | `/riskBand` | `/country` |
|---|---|---|---|
| Matches access pattern | User history | Risk dashboard | Regional analytics |
| Cardinality | Higher | Lower | Medium |
| Data distribution | To measure | To measure | To measure |
| Request distribution | To measure | To measure | To measure |
| RU behavior | To measure | To measure | To measure |
| Latency | To measure | To measure | To measure |
| Hot-partition risk | To test | To test | To test |

The table intentionally does not declare a universal winner.

The correct design depends on the application's actual workload and access patterns.

---

## 21. Reproducibility Workflow

The complete experiment can be reproduced using:

```text
1. Create Azure Cosmos DB for NoSQL account
        ↓
2. Create database: phishguard-study-db
        ↓
3. Create container: scans
        ↓
4. Set partition key: /userId
        ↓
5. Provision 400 RU/s
        ↓
6. Configure local .env
        ↓
7. Install Python dependencies
        ↓
8. Generate dataset
        ↓
9. Run normal workload
        ↓
10. Run skewed workload
        ↓
11. Record latency / RU / 429
        ↓
12. Increase workload progressively
        ↓
13. Inspect partition-level behavior
        ↓
14. Compare candidate partition keys
```

---

## 22. Project Structure

```text
Azure-Table-or-Cosmos-DB-Partition-Key-Design-Study/
│
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
│
├── generate_scand.py
├── normal_workload.py
├── hot_workload.py
│
└── docs/
    └── STEP_04_TO_14_EXPERIMENT_AND_AZURE_SETUP.txt
```

---

## 23. Security

### Secrets never committed

The following must never be pushed to GitHub:

```text
.env
Cosmos DB primary keys
API keys
Passwords
Access tokens
Private connection strings
```

The repository contains:

```text
.env.example
```

only as a configuration template.

### Verify before committing

```bash
git status
```

The real `.env` file should not be staged.

If a credential is accidentally exposed, rotate the credential immediately.

---

## 24. Engineering Lessons

### Lesson 1 — Partition-key design begins with access patterns

The best candidate is not determined by field name alone.

### Lesson 2 — Cardinality is necessary but not sufficient

A field may have many values while the workload still repeatedly targets a small subset.

### Lesson 3 — Data distribution and request distribution are different

A balanced dataset does not guarantee a balanced workload.

### Lesson 4 — Normal tests are not enough

A design can behave correctly under normal traffic and still become vulnerable under skew.

### Lesson 5 — Skew is evidence, not the final diagnosis

A concentrated workload indicates risk.

It does not automatically prove physical hot-partition contention.

### Lesson 6 — Measure before changing the design

Latency, RU consumption, throttling, and partition-level metrics provide stronger evidence than assumptions.

### Lesson 7 — Partition-key decisions have architectural consequences

Changing a partition key can involve data movement into a destination container, so partition-key selection should be treated as an early data-modeling decision.

---

## 25. Future Work

The next phase of the study can extend the experiment in several directions:

### A. Controlled load escalation

Run:

```text
500 → 1,000 → 2,000 → 5,000 → higher
```

where practical.

### B. Candidate-key experiments

Create separate experimental containers for:

```text
/userId
/riskBand
/country
```

and execute equivalent workloads.

### C. Partition-level telemetry

Use Azure monitoring/Insights to inspect normalized RU consumption by partition-key range when diagnosing hot-partition behavior.

### D. Query-cost analysis

Compare targeted partition-key queries against queries that do not provide the partition key.

### E. Advanced partitioning

For workloads that require more complex distribution, investigate hierarchical or synthetic partition-key strategies.

---

## 26. Final Conclusion

This project demonstrates a practical, evidence-driven approach to partition-key design.

The initial `/userId` experiment successfully handled the tested 500-request normal workload and also handled a deliberately skewed 500-request workload without HTTP 429 responses.

The skewed test nevertheless demonstrated an important design risk:

```text
80% of traffic → one partition-key value
```

The result shows why partition-key evaluation cannot stop at:

```text
"Does the query work?"
```

It must also ask:

```text
"How is the workload distributed?"
"How much throughput does it consume?"
"What happens as demand increases?"
"Where does the bottleneck appear?"
```

### Final engineering principle

> **We are not selecting a partition key based on theory alone; we are validating the design using realistic workloads, controlled stress testing, and measurable performance data.**

---

## Official Documentation

This project follows Azure Cosmos DB for NoSQL concepts and terminology documented by Microsoft Learn.

Recommended references:

- Azure Cosmos DB overview
- Azure Cosmos DB for NoSQL portal quickstart
- Containers and partitioning
- Partition-key design and horizontal scaling
- Request Units and throughput
- Monitoring normalized RU consumption
- Changing partition keys
- Hierarchical partition keys

