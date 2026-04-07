# 📋 QuakeWatch — Team Contributions & Submission Order

This document defines which files each team member owns, the order in which work should be committed, and the git workflow to follow.

---

## 👥 Team File Ownership

### 🔵 Rishi — Infrastructure, Ingester & API

**Files owned:**

| File | Description |
|------|-------------|
| `docker-compose.yml` | Orchestrates all 5 services together |
| `.env.example` | Template for environment variables (never commit `.env`) |
| `.gitignore` | Ensures secrets and build artifacts are not committed |
| `ingester/main.py` | Polls USGS every 60s, deduplicates, publishes to SQS |
| `ingester/Dockerfile` | Container build instructions for the ingester |
| `ingester/requirements.txt` | Python dependencies for the ingester |
| `api/main.py` | FastAPI server — serves earthquakes, alerts, stats |
| `api/Dockerfile` | Container build instructions for the API |
| `api/requirements.txt` | Python dependencies for the API |
| `README.md` | Project overview, architecture diagram, setup instructions |

---

### 🟢 Asha — Processor, Alert Evaluator & Data

**Files owned:**

| File | Description |
|------|-------------|
| `processor/main.py` | Reads SQS messages, calculates impact scores, writes to DynamoDB |
| `processor/Dockerfile` | Container build instructions for the processor |
| `processor/requirements.txt` | Python dependencies for the processor |
| `alert-evaluator/main.py` | Monitors earthquakes, creates alert records for high/medium events |
| `alert-evaluator/Dockerfile` | Container build instructions for the alert evaluator |
| `alert-evaluator/requirements.txt` | Python dependencies for the alert evaluator |
| `seed-data/seed_cities.py` | Script to populate the DynamoDB cities table with population data |
| `seed-data/requirements.txt` | Python dependencies for the seed script |

---

### 🟠 Haina — Dashboard & Frontend

**Files owned:**

| File | Description |
|------|-------------|
| `dashboard/index.html` | Main HTML structure — map container, sidebar, filters, stats |
| `dashboard/style.css` | All styling — dark theme, responsive layout, animations |
| `dashboard/app.js` | JavaScript — Leaflet map, API fetching, markers, auto-refresh |
| `dashboard/nginx.conf` | Nginx config — serves frontend, proxies `/api` to FastAPI |
| `dashboard/Dockerfile` | Container build instructions for the dashboard |

---

## 🔀 Git Workflow

### Setup (everyone does this once)
```bash
git clone https://github.com/rishitaido/quakewatch.git
cd quakewatch
```

### Daily Workflow
```bash
# 1. Always pull latest before starting work
git pull origin main

# 2. Create a branch for your work (use your name prefix)
git checkout -b rishi/feature-name      # Rishi
git checkout -b asha/feature-name       # Asha
git checkout -b haina/feature-name      # Haina

# 3. Make your changes, then stage only YOUR files
git add ingester/ api/                  # Rishi example
git add processor/ alert-evaluator/     # Asha example
git add dashboard/                      # Haina example

# 4. Commit with a clear message (see format below)
git commit -m "feat(ingester): add deduplication logic"

# 5. Push your branch
git push origin rishi/feature-name

# 6. Open a Pull Request on GitHub → merge into main
```

---

## 📦 Commit Order for Submission

Follow this order so that each piece builds on a working foundation. Each phase should be a separate commit on `main`.

```
Phase 1 — Rishi
  ├── Root config files (.gitignore, .env.example, docker-compose.yml, README.md)
  └── Commit: "chore: add project config and docker-compose"

Phase 2 — Rishi
  ├── ingester/Dockerfile
  ├── ingester/requirements.txt
  ├── ingester/main.py
  ├── api/Dockerfile
  ├── api/requirements.txt
  └── api/main.py
  └── Commit: "feat(ingester, api): add seismic ingester and REST API"

Phase 3 — Asha
  ├── seed-data/requirements.txt
  ├── seed-data/seed_cities.py
  ├── processor/Dockerfile
  ├── processor/requirements.txt
  ├── processor/main.py
  ├── alert-evaluator/Dockerfile
  ├── alert-evaluator/requirements.txt
  └── alert-evaluator/main.py
  └── Commit: "feat(processor, alerts): add impact processor and alert evaluator"

Phase 4 — Haina
  ├── dashboard/Dockerfile
  ├── dashboard/nginx.conf
  ├── dashboard/index.html
  ├── dashboard/style.css
  └── dashboard/app.js
  └── Commit: "feat(dashboard): add geo dashboard with Leaflet map"

Phase 5 — Rishi (final integration)
  └── Any fixes needed to make it all work together
  └── Commit: "chore: integration fixes and final cleanup"
```

---

## ✅ Commit Message Format

Use this format so the commit history is clean and professional:

```
<type>(<scope>): <short description>

Types:
  feat     → new feature or file
  fix      → bug fix
  chore    → config, setup, tooling
  docs     → documentation changes
  style    → CSS/formatting only (no logic change)
  refactor → code restructure, no feature change
```

**Examples:**
```bash
git commit -m "feat(processor): implement Haversine impact scoring"
git commit -m "fix(api): handle empty earthquakes table gracefully"
git commit -m "style(dashboard): improve marker colors and mobile layout"
git commit -m "docs: update README with EC2 deployment steps"
git commit -m "chore: add .gitignore for .env and __pycache__"
```

---

## ⚠️ Important Rules

> **Never commit `.env`** — it contains AWS secret keys. Only share it with teammates via DM.

> **Never push directly to `main`** — always use a branch + Pull Request.

> **Only `git add` your own files** — don't stage files that belong to another teammate.

> **Always `git pull` before starting work** — avoids merge conflicts.
