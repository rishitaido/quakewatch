"""
QuakeWatch - REST API Service
FastAPI server exposing earthquake data, alerts, and statistics
to the Geo Dashboard frontend.
Owner: Rishi
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ── Configuration ──────────────────────────────────────────
EARTHQUAKES_TABLE = os.environ.get("EARTHQUAKES_TABLE", "earthquakes")
ALERTS_TABLE = os.environ.get("ALERTS_TABLE", "alerts")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# ── Logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [API] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("api")

# ── AWS Clients ────────────────────────────────────────────
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
earthquakes_table = dynamodb.Table(EARTHQUAKES_TABLE)
alerts_table = dynamodb.Table(ALERTS_TABLE)

# ── FastAPI App ────────────────────────────────────────────
app = FastAPI(
    title="QuakeWatch API",
    description="Real-time earthquake data with impact scores and alerts",
    version="1.0.0",
)

# Allow all origins for development (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def decimal_to_float(obj):
    """
    Recursively convert Decimal values to float for JSON serialization.
    DynamoDB returns Decimal types which aren't JSON-serializable by default.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


# ── Health Check ───────────────────────────────────────────
@app.get("/health")
def health_check():
    """Health check endpoint. Returns 200 if the service is running."""
    return {
        "status": "ok",
        "service": "quakewatch-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Earthquakes ────────────────────────────────────────────
@app.get("/earthquakes")
def get_earthquakes(
    hours: int = Query(default=6, ge=1, le=168, description="Hours of data to return"),
    min_mag: float = Query(default=0, ge=0, le=10, description="Minimum magnitude"),
    min_impact: float = Query(default=0, ge=0, le=100, description="Minimum impact score"),
    limit: int = Query(default=200, ge=1, le=1000, description="Max results"),
):
    """
    Return recent earthquakes with enrichment data.
    Supports filtering by time window, magnitude, and impact score.
    """
    try:
        # Calculate the cutoff timestamp
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        cutoff_ms = now_ms - (hours * 3600 * 1000)

        # Scan with filter (in production, you'd use a GSI for better performance)
        response = earthquakes_table.scan(
            FilterExpression="(#ts >= :cutoff)",
            ExpressionAttributeNames={"#ts": "timestamp"},
            ExpressionAttributeValues={":cutoff": cutoff_ms},
        )
        items = response.get("Items", [])

        while "LastEvaluatedKey" in response:
            response = earthquakes_table.scan(
                FilterExpression="(#ts >= :cutoff)",
                ExpressionAttributeNames={"#ts": "timestamp"},
                ExpressionAttributeValues={":cutoff": cutoff_ms},
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        # Apply additional filters in memory
        filtered = []
        for item in items:
            mag = float(item.get("magnitude", 0))
            impact = float(item.get("impact_score", 0))
            if mag >= min_mag and impact >= min_impact:
                filtered.append(decimal_to_float(item))

        # Sort by timestamp descending (most recent first)
        filtered.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        return {
            "count": len(filtered[:limit]),
            "earthquakes": filtered[:limit],
            "query": {
                "hours": hours,
                "min_mag": min_mag,
                "min_impact": min_impact,
            },
        }

    except ClientError as e:
        logger.error(f"Failed to query earthquakes: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")


@app.get("/earthquakes/{event_id}")
def get_earthquake(event_id: str):
    """Return full detail for a single earthquake event."""
    try:
        response = earthquakes_table.get_item(Key={"event_id": event_id})

        if "Item" not in response:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

        return decimal_to_float(response["Item"])

    except ClientError as e:
        logger.error(f"Failed to get event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")


# ── Alerts ─────────────────────────────────────────────────
@app.get("/alerts")
def get_alerts(
    severity: str = Query(default=None, description="Filter: high, medium"),
    hours: int = Query(default=24, ge=1, le=168, description="Hours of alerts"),
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
):
    """
    Return recent alerts, optionally filtered by severity.
    """
    try:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        cutoff_ms = now_ms - (hours * 3600 * 1000)

        if severity:
            response = alerts_table.scan(
                FilterExpression="severity = :sev AND created_at >= :cutoff",
                ExpressionAttributeValues={
                    ":sev": severity,
                    ":cutoff": cutoff_ms,
                },
            )
        else:
            response = alerts_table.scan(
                FilterExpression="created_at >= :cutoff",
                ExpressionAttributeValues={":cutoff": cutoff_ms},
            )

        items = response.get("Items", [])

        while "LastEvaluatedKey" in response:
            scan_kwargs = {
                "ExclusiveStartKey": response["LastEvaluatedKey"],
                "FilterExpression": "created_at >= :cutoff",
                "ExpressionAttributeValues": {":cutoff": cutoff_ms},
            }
            if severity:
                scan_kwargs["FilterExpression"] = "severity = :sev AND created_at >= :cutoff"
                scan_kwargs["ExpressionAttributeValues"][":sev"] = severity
            response = alerts_table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))

        alerts = [decimal_to_float(item) for item in items]
        alerts.sort(key=lambda x: x.get("created_at", 0), reverse=True)

        return {
            "count": len(alerts[:limit]),
            "alerts": alerts[:limit],
        }

    except ClientError as e:
        logger.error(f"Failed to query alerts: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")


# ── Stats ──────────────────────────────────────────────────
@app.get("/stats")
def get_stats():
    """
    Return summary statistics: total events today, highest magnitude,
    highest impact score, total alerts.
    """
    try:
        # Get today's earthquakes
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        day_cutoff = now_ms - (24 * 3600 * 1000)

        eq_response = earthquakes_table.scan(
            FilterExpression="#ts >= :cutoff",
            ExpressionAttributeNames={"#ts": "timestamp"},
            ExpressionAttributeValues={":cutoff": day_cutoff},
        )
        earthquakes = eq_response.get("Items", [])

        while "LastEvaluatedKey" in eq_response:
            eq_response = earthquakes_table.scan(
                FilterExpression="#ts >= :cutoff",
                ExpressionAttributeNames={"#ts": "timestamp"},
                ExpressionAttributeValues={":cutoff": day_cutoff},
                ExclusiveStartKey=eq_response["LastEvaluatedKey"],
            )
            earthquakes.extend(eq_response.get("Items", []))

        # Get today's alerts
        alert_response = alerts_table.scan(
            FilterExpression="created_at >= :cutoff",
            ExpressionAttributeValues={":cutoff": day_cutoff},
        )
        alerts = alert_response.get("Items", [])

        # Compute stats
        magnitudes = [float(e.get("magnitude", 0)) for e in earthquakes]
        impacts = [float(e.get("impact_score", 0)) for e in earthquakes]

        return {
            "total_events_24h": len(earthquakes),
            "highest_magnitude": max(magnitudes) if magnitudes else 0,
            "highest_impact": max(impacts) if impacts else 0,
            "total_alerts_24h": len(alerts),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    except ClientError as e:
        logger.error(f"Failed to compute stats: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")
