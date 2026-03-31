"""
QuakeWatch - Seismic Ingester Service
Polls the USGS earthquake feed, deduplicates events, and publishes new ones to SQS.
Owner: Rishi
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timezone

import boto3
import requests
from botocore.exceptions import ClientError

# ── Configuration ──────────────────────────────────────────
USGS_FEED_URL = os.environ.get(
    "USGS_FEED_URL",
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
)
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "60"))
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]
EARTHQUAKES_TABLE = os.environ.get("EARTHQUAKES_TABLE", "earthquakes")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# ── Logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [INGESTER] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("ingester")

# ── AWS Clients ────────────────────────────────────────────
sqs = boto3.client("sqs", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
earthquakes_table = dynamodb.Table(EARTHQUAKES_TABLE)


def fetch_usgs_feed() -> list[dict]:
    """
    Fetch the latest earthquake data from USGS GeoJSON feed.
    Returns a list of parsed earthquake dicts.
    """
    try:
        response = requests.get(USGS_FEED_URL, timeout=30)
        response.raise_for_status()
        data = response.json()

        earthquakes = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [0, 0, 0])

            earthquake = {
                "event_id": feature.get("id", ""),
                "magnitude": props.get("mag"),
                "place": props.get("place", "Unknown"),
                "time": props.get("time", 0),  # milliseconds since epoch
                "url": props.get("url", ""),
                "tsunami": props.get("tsunami", 0),
                "depth": coords[2] if len(coords) > 2 else 0,
                "lon": coords[0],
                "lat": coords[1],
            }
            earthquakes.append(earthquake)

        logger.info(f"Fetched {len(earthquakes)} earthquakes from USGS feed")
        return earthquakes

    except requests.RequestException as e:
        logger.error(f"Failed to fetch USGS feed: {e}")
        return []


def event_exists(event_id: str) -> bool:
    """
    Check if an earthquake event already exists in DynamoDB.
    Used for deduplication so we don't reprocess the same event.
    """
    try:
        response = earthquakes_table.get_item(
            Key={"event_id": event_id},
            ProjectionExpression="event_id",
        )
        return "Item" in response
    except ClientError as e:
        logger.error(f"DynamoDB check failed for {event_id}: {e}")
        # If we can't check, assume it doesn't exist (will be deduplicated downstream)
        return False


def publish_to_sqs(earthquake: dict) -> bool:
    """
    Publish a single earthquake event to the SQS queue for processing.
    """
    try:
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(earthquake),
            MessageAttributes={
                "event_id": {
                    "DataType": "String",
                    "StringValue": earthquake["event_id"],
                },
                "magnitude": {
                    "DataType": "Number",
                    "StringValue": str(earthquake.get("magnitude", 0)),
                },
            },
        )
        return True
    except ClientError as e:
        logger.error(f"Failed to publish {earthquake['event_id']} to SQS: {e}")
        return False


def run_ingestion_cycle():
    """
    Single ingestion cycle: fetch USGS data, deduplicate, publish new events.
    """
    earthquakes = fetch_usgs_feed()

    new_count = 0
    duplicate_count = 0

    for eq in earthquakes:
        if not eq["event_id"]:
            continue

        # Skip events with no magnitude (sometimes USGS returns null)
        if eq["magnitude"] is None:
            continue

        if event_exists(eq["event_id"]):
            duplicate_count += 1
            continue

        if publish_to_sqs(eq):
            new_count += 1
            logger.info(
                f"NEW EVENT: {eq['event_id']} | mag={eq['magnitude']} | "
                f"{eq['place']} | depth={eq['depth']}km"
            )

    logger.info(
        f"Cycle complete: {new_count} new, {duplicate_count} duplicates, "
        f"{len(earthquakes)} total from feed"
    )


def main():
    """
    Main loop: run ingestion cycles with configurable interval and backoff on errors.
    """
    logger.info("=" * 60)
    logger.info("QuakeWatch Seismic Ingester starting")
    logger.info(f"Feed URL: {USGS_FEED_URL}")
    logger.info(f"Poll interval: {POLL_INTERVAL}s")
    logger.info(f"SQS Queue: {SQS_QUEUE_URL}")
    logger.info("=" * 60)

    consecutive_errors = 0
    max_backoff = 300  # 5 minutes max

    while True:
        try:
            run_ingestion_cycle()
            consecutive_errors = 0  # Reset on success
            time.sleep(POLL_INTERVAL)

        except Exception as e:
            consecutive_errors += 1
            backoff = min(30 * (2 ** consecutive_errors), max_backoff)
            logger.error(
                f"Ingestion cycle failed (attempt {consecutive_errors}): {e}. "
                f"Retrying in {backoff}s"
            )
            time.sleep(backoff)


if __name__ == "__main__":
    main()
