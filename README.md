# 🌍 QuakeWatch — Real-Time Earthquake Alert & Impact Analysis Platform

A real-time earthquake monitoring platform that ingests USGS seismic data, calculates population impact scores, triggers smart alerts, and visualizes everything on an interactive geospatial dashboard.

Built with containerized microservices on AWS for the Cloud Computing course project.

---

## Architecture

```
USGS GeoJSON Feed
       │
       ▼
┌──────────────┐     ┌───────────┐     ┌──────────────────┐
│   Seismic    │────▶│  AWS SQS  │────▶│    Impact         │
│   Ingester   │     │   Queue   │     │    Processor      │
└──────────────┘     └───────────┘     └────────┬─────────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │  DynamoDB     │
                                        │  (earthquakes │◀── cities table
                                        │   + alerts)   │      (seed data)
                                        └──────┬───────┘
                                               │
                              ┌────────────────┼────────────────┐
                              ▼                                 ▼
                     ┌──────────────┐                  ┌──────────────┐
                     │    Alert     │                  │   REST API   │
                     │  Evaluator   │──────────────▶   │  (FastAPI)   │
                     └──────────────┘   writes alerts  └──────┬───────┘
                                                              │
                                                              ▼
                                                     ┌──────────────┐
                                                     │     Geo      │
                                                     │  Dashboard   │
                                                     │ (Leaflet.js) │
                                                     └──────────────┘
```

### Services

| Service | Description | Tech |
|---------|-------------|------|
| **Seismic Ingester** | Polls USGS feed every 60s, deduplicates, publishes to SQS | Python, Requests, Boto3 |
| **Impact Processor** | Calculates impact scores using Haversine formula + population data | Python, Boto3 |
| **Alert Evaluator** | Monitors for high/medium severity events, creates alert records | Python, Boto3 |
| **REST API** | Serves earthquake data, alerts, and stats to the dashboard | Python, FastAPI |
| **Geo Dashboard** | Interactive map with live markers, alert banner, and filters | HTML/JS, Leaflet.js |

### AWS Services

- **EC2** (t2.micro) — hosts all Docker containers
- **SQS** — message queue between ingester and processor
- **DynamoDB** — stores earthquakes, alerts, and city population data
- **IAM** — role-based access control

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- AWS account with access keys
- AWS CLI configured (for seeding data)

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd quakewatch
cp .env.example .env
# Edit .env with your AWS credentials and resource URLs
```

### 2. Create AWS resources

```bash
# SQS Queue
aws sqs create-queue --queue-name quakewatch-raw-events

# DynamoDB Tables
aws dynamodb create-table \
  --table-name earthquakes \
  --attribute-definitions AttributeName=event_id,AttributeType=S \
  --key-schema AttributeName=event_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb create-table \
  --table-name alerts \
  --attribute-definitions AttributeName=alert_id,AttributeType=S \
  --key-schema AttributeName=alert_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb create-table \
  --table-name cities \
  --attribute-definitions AttributeName=city_id,AttributeType=S \
  --key-schema AttributeName=city_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### 3. Seed city data

```bash
cd seed-data
pip install -r requirements.txt
python seed_cities.py
cd ..
```

### 4. Launch

```bash
docker-compose up --build -d
```

### 5. Open the dashboard

Visit `http://localhost` in your browser.

---

## API Documentation

| Endpoint | Method | Description | Query Params |
|----------|--------|-------------|--------------|
| `/health` | GET | Health check | — |
| `/earthquakes` | GET | Recent earthquakes with enrichment | `hours`, `min_mag`, `min_impact`, `limit` |
| `/earthquakes/{event_id}` | GET | Single earthquake detail | — |
| `/alerts` | GET | Recent alerts | `severity`, `hours`, `limit` |
| `/stats` | GET | Summary statistics (24h) | — |

### Example requests

```bash
# Health check
curl http://localhost:8000/health

# Last 6 hours, magnitude >= 2.5
curl "http://localhost:8000/earthquakes?hours=6&min_mag=2.5"

# High severity alerts only
curl "http://localhost:8000/alerts?severity=high"

# Dashboard stats
curl http://localhost:8000/stats
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key | (required) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | (required) |
| `AWS_REGION` | AWS region | `us-east-1` |
| `SQS_QUEUE_URL` | SQS queue URL | (required) |
| `EARTHQUAKES_TABLE` | DynamoDB table name | `earthquakes` |
| `ALERTS_TABLE` | DynamoDB table name | `alerts` |
| `CITIES_TABLE` | DynamoDB table name | `cities` |
| `USGS_FEED_URL` | USGS GeoJSON feed URL | all_hour.geojson |
| `POLL_INTERVAL_SECONDS` | Ingester poll interval | `60` |
| `HIGH_SEVERITY_MAG` | High alert magnitude threshold | `6.0` |
| `HIGH_SEVERITY_IMPACT` | High alert impact threshold | `80` |
| `MEDIUM_SEVERITY_MAG` | Medium alert magnitude threshold | `4.5` |
| `MEDIUM_SEVERITY_IMPACT` | Medium alert impact threshold | `40` |
| `API_PORT` | FastAPI port | `8000` |

---

## Project Structure

```
quakewatch/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── ingester/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── processor/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── alert-evaluator/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── api/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── dashboard/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── index.html
│   ├── style.css
│   └── app.js
└── seed-data/
    ├── seed_cities.py
    └── requirements.txt
```

---

## Deploying to AWS EC2

```bash
# 1. Launch a t2.micro instance (Amazon Linux 2)
# 2. SSH in and install Docker
sudo yum update -y
sudo yum install -y docker git
sudo service docker start
sudo usermod -aG docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. Clone repo and configure
git clone <your-repo-url>
cd quakewatch
cp .env.example .env
nano .env  # Add your AWS credentials

# 4. Seed cities (if not already done)
pip3 install boto3 requests
cd seed-data && python3 seed_cities.py && cd ..

# 5. Launch
docker-compose up --build -d

# 6. Open port 80 in EC2 security group, then visit http://<public-ip>
```

---

## Data Sources

- **USGS Earthquake Hazards Program**: https://earthquake.usgs.gov/earthquakes/feed/
- **GeoNames Cities**: https://download.geonames.org/export/dump/ (CC BY 4.0)

---

## Team

- **Rishi** — Seismic Ingester, REST API, Docker/DevOps, EC2 deployment
- **Asha** — Impact Processor, Alert Evaluator, DynamoDB schema, seed data
- **Haina** — Geo Dashboard, frontend design, presentation
