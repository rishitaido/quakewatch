# 🌍 Haina's Guide — Geo Dashboard & Frontend

Hey Haina! This guide covers everything you own in QuakeWatch and how to get set up.

---

## Your Responsibilities

| Area | Directory/Files | What It Does |
|------|----------------|--------------|
| **Geo Dashboard** | `dashboard/` | Interactive Leaflet.js map showing earthquake markers, alert banners, and filters |
| **Frontend Design** | `dashboard/style.css`, `dashboard/index.html` | Visual design, layout, responsive styling |
| **Presentation** | — | Final presentation/demo of the project |

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

---

## Your Files

### `dashboard/index.html`
The main HTML structure of the dashboard. Contains:
- Map container (Leaflet.js)
- Alert banner area
- Filter controls (magnitude, time range)
- Stats summary panel

### `dashboard/style.css`
All the styling. Key sections:
- Color scheme and CSS variables
- Map layout and responsiveness
- Alert banner animations
- Filter panel styling
- Marker popups

### `dashboard/app.js`
The JavaScript logic. Key functions:
- Fetching earthquake data from the API (`/earthquakes`, `/alerts`, `/stats`)
- Rendering markers on the Leaflet map
- Color-coding markers by magnitude/impact
- Displaying alert banners
- Filter controls
- Auto-refresh on an interval

### `dashboard/nginx.conf`
Nginx configuration that:
- Serves the static frontend on port 80
- Proxies API requests (`/api/*`) to the FastAPI backend on port 8000

### `dashboard/Dockerfile`
Builds the nginx container with your frontend files.

---

## Running the Dashboard

### Option A: Full stack (recommended)

Run everything together to see real data:
```bash
docker compose up --build
```
Then open: **http://localhost**

> **Note:** It takes ~1-2 minutes for the first earthquake data to appear. The ingester polls every 60 seconds, then the processor enriches the data.

### Option B: Frontend only (for quick CSS/HTML changes)

If you're just tweaking styles and layout, you can open the HTML directly:
```bash
# From the project root
open dashboard/index.html
```

> ⚠️ **API calls will fail** in this mode since there's no backend. But you can see layout and styling changes instantly without rebuilding Docker.

### Option C: Rebuild just the dashboard container

After making changes, rebuild only your container:
```bash
docker compose up --build dashboard
```

---

## Your Tasks

### Task 1: Review the Dashboard UI

Open the dashboard at `http://localhost` after running `docker compose up --build` and check:

- [ ] Map loads and centers correctly
- [ ] Earthquake markers appear after ~1-2 minutes
- [ ] Marker colors reflect magnitude/severity
- [ ] Clicking a marker shows a popup with earthquake details
- [ ] Alert banner appears when there are active alerts
- [ ] Filter controls work (magnitude slider, time range)
- [ ] Stats panel shows correct numbers

---

### Task 2: Polish the Frontend Design

Look for opportunities to improve:

- [ ] **Responsive design** — Does it look good on mobile/tablet?
- [ ] **Color scheme** — Are the marker colors distinguishable? Is the UI readable?
- [ ] **Loading states** — What does the user see while data is loading?
- [ ] **Empty states** — What happens when there are no earthquakes or alerts?
- [ ] **Animations** — Are marker popups and alert banners smooth?
- [ ] **Typography** — Is text readable and well-sized?

---

### Task 3: Test the API Integration

The dashboard talks to these API endpoints (proxied through nginx):

```bash
# These should all return JSON:
curl http://localhost:8000/health
curl http://localhost:8000/earthquakes?hours=6
curl http://localhost:8000/alerts
curl http://localhost:8000/stats
```

Verify that `app.js` correctly:
- Handles API errors gracefully (show a message, don't crash)
- Refreshes data periodically
- Parses the JSON response correctly

---

### Task 4: Prepare the Presentation

For the demo, plan to show:
1. **Architecture diagram** — from the README
2. **Live demo** — the running dashboard on EC2 (Rishi will deploy)
3. **Data flow walkthrough** — earthquake appears on USGS → ingester → SQS → processor → DynamoDB → API → dashboard
4. **Key features** — real-time updates, impact scoring, smart alerts, filtering
5. **AWS services used** — EC2, SQS, DynamoDB, IAM

---

## Git Workflow

Always work on a branch:
```bash
git checkout -b haina/dashboard-polish
# make your changes
git add .
git commit -m "style: improve marker colors and mobile layout"
git push origin haina/dashboard-polish
# then open a Pull Request on GitHub
```

---

## Useful References

- **Leaflet.js docs**: https://leafletjs.com/reference.html
- **Leaflet marker customization**: https://leafletjs.com/examples/custom-icons/
- **CSS Grid/Flexbox guide**: https://css-tricks.com/snippets/css/complete-guide-grid/
- **USGS earthquake data format**: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php

---

## Common Issues

| Problem | Solution |
|---------|----------|
| Map is blank | Check browser console for JS errors. Leaflet CDN might be blocked. |
| No markers appear | Backend might not be running. Check `docker compose ps` and wait 1-2 mins. |
| API calls fail (404/502) | Make sure the `api` container is running. Check `docker compose logs api`. |
| CSS changes don't appear | Hard refresh with `Cmd+Shift+R`. If using Docker, rebuild with `docker compose up --build dashboard`. |
| Map tiles not loading | You might be offline, or the tile provider is down. |
