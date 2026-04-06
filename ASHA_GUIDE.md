# 🔧 Asha's Guide — Impact Processor, Alert Evaluator & Seed Data

Hey Asha! This guide covers everything you own in QuakeWatch and how to get set up.

---

## Your Responsibilities

| Service | Directory | What It Does |
|---------|-----------|--------------|
| **Impact Processor** | `processor/` | Reads raw earthquake events from SQS, calculates population impact scores using the Haversine formula + city data, writes enriched records to DynamoDB |
| **Alert Evaluator** | `alert-evaluator/` | Monitors new earthquakes in DynamoDB, creates alert records when severity thresholds are exceeded |
| **Seed Data** | `seed-data/` | Script to populate the `cities` DynamoDB table with city names, coordinates, and population data |

---

## Getting Set Up

### 1. Clone the repo

```bash
git clone <repo-url>
cd quakewatch
```

### 2. Get the `.env` file

Ask Rishi for the `.env` file — it contains the AWS credentials and resource URLs. **Do NOT commit this file to Git.**

Place it in the project root:
```
quakewatch/
├── .env          ← put it here
├── docker-compose.yml
├── ...
```

### 3. Install Docker Desktop

Download from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) if you don't have it.

### 4. Install AWS CLI

```bash
# macOS
brew install awscli

# Windows
# Download from https://aws.amazon.com/cli/
```

### 5. Configure AWS CLI

```bash
aws configure
```

Enter the same credentials from the `.env` file:
- Access Key ID
- Secret Access Key
- Region: `us-east-1`
- Output: `json`

---

## Your Tasks

### Task 1: Seed the Cities Data

This populates DynamoDB with city + population data that the processor uses for impact scoring.

```bash
cd seed-data
pip3 install -r requirements.txt
python3 seed_cities.py
```

Verify it worked:
```bash
aws dynamodb scan --table-name cities --select COUNT
```

You should see a count of cities (several hundred). If the count is 0, something went wrong — check the script output for errors.

---

### Task 2: Understand the Impact Processor

**File:** `processor/main.py`

This service:
1. Polls the SQS queue for raw earthquake events
2. For each event, queries the `cities` table to find nearby cities
3. Calculates an **impact score** using:
   - Earthquake magnitude
   - Distance to nearby cities (Haversine formula)
   - City population
4. Writes the enriched earthquake record (with impact score) to the `earthquakes` DynamoDB table

**Key things to verify:**
- [ ] The Haversine distance calculation is correct
- [ ] Impact score formula makes sense (higher magnitude + closer to big city = higher score)
- [ ] SQS messages are being deleted after processing (no duplicate processing)
- [ ] Error handling — what happens if DynamoDB is down? If a message is malformed?

**To test in isolation:**
```bash
# Run just the processor
docker compose up --build processor

# Watch its logs
docker compose logs -f processor
```

> **Note:** The processor needs the ingester running to have messages in the queue. Run the full stack with `docker compose up --build` for end-to-end testing.

---

### Task 3: Understand the Alert Evaluator

**File:** `alert-evaluator/main.py`

This service:
1. Periodically scans the `earthquakes` table for new events
2. Checks each event against severity thresholds:
   - **High severity**: magnitude ≥ 6.0 OR impact score ≥ 80
   - **Medium severity**: magnitude ≥ 4.5 OR impact score ≥ 40
3. Creates alert records in the `alerts` DynamoDB table

**Key things to verify:**
- [ ] Threshold logic matches the `.env` configuration values
- [ ] Alerts are not duplicated (same earthquake shouldn't create multiple alerts)
- [ ] Alert records contain useful info (earthquake ID, severity level, timestamp, description)
- [ ] The evaluator handles edge cases (no earthquakes, already-alerted events)

**To test in isolation:**
```bash
docker compose up --build alert-evaluator
docker compose logs -f alert-evaluator
```

---

### Task 4: Verify End-to-End Data Flow

Once the full stack is running (`docker compose up --build`), verify the pipeline:

```bash
# 1. Check if earthquakes are being stored
aws dynamodb scan --table-name earthquakes --select COUNT

# 2. Check a sample earthquake record
aws dynamodb scan --table-name earthquakes --max-items 1

# 3. Check if alerts are being created
aws dynamodb scan --table-name alerts --select COUNT

# 4. Check a sample alert
aws dynamodb scan --table-name alerts --max-items 1

# 5. Via the API
curl http://localhost:8000/earthquakes?hours=1
curl http://localhost:8000/alerts
```

---

## Git Workflow

Always work on a branch:
```bash
git checkout -b asha/processor-fixes
# make your changes
git add .
git commit -m "fix: improve impact score calculation"
git push origin asha/processor-fixes
# then open a Pull Request on GitHub
```

---

## Common Issues

| Problem | Solution |
|---------|----------|
| Processor logs say "No messages" | The ingester might not be running, or there are no recent earthquakes. Wait ~60 seconds. |
| `AccessDeniedException` | Your `.env` credentials might be wrong. Ask Rishi to verify. |
| Seed script fails | Make sure AWS CLI is configured and the `cities` table exists. |
| Impact scores are all 0 | Check if the cities table was seeded. Run `aws dynamodb scan --table-name cities --select COUNT`. |
