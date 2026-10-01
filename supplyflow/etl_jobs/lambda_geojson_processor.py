from __future__ import annotations

import csv
import io
import json
import os
from urllib.parse import unquote_plus

import boto3


s3 = boto3.client("s3")


def coordinates_to_wkt(coordinates: list) -> str:
    points = []
    for longitude, latitude, *_ in coordinates:
        points.append(f"{longitude} {latitude}")
    return f"LINESTRING ({', '.join(points)})"


def geometry_to_wkt(geometry: dict) -> str:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geometry_type == "LineString":
        return coordinates_to_wkt(coordinates)
    if geometry_type == "MultiLineString":
        segments = [coordinates_to_wkt(segment).replace("LINESTRING ", "") for segment in coordinates]
        return f"MULTILINESTRING ({', '.join(segments)})"
    raise ValueError(f"Unsupported geometry type: {geometry_type}")


def flatten_geojson(payload: dict) -> list[dict[str, str]]:
    rows = []
    for index, feature in enumerate(payload.get("features", []), start=1):
        properties = feature.get("properties", {})
        rows.append(
            {
                "route_id": str(properties.get("route_id", f"ROUTE{index:05d}")),
                "carrier_id": str(properties.get("carrier_id", "")),
                "origin_location_id": str(properties.get("origin_location_id", "")),
                "destination_location_id": str(properties.get("destination_location_id", "")),
                "route_wkt": geometry_to_wkt(feature.get("geometry", {})),
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["route_id", "carrier_id", "origin_location_id", "destination_location_id", "route_wkt"])
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def lambda_handler(event, context):
    output_bucket = os.environ["PROCESSED_BUCKET"]
    output_prefix = os.environ.get("PROCESSED_PREFIX", "processed_routes/")
    processed = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        response = s3.get_object(Bucket=bucket, Key=key)
        payload = json.loads(response["Body"].read().decode("utf-8"))
        rows = flatten_geojson(payload)
        output_key = f"{output_prefix}{key.rsplit('/', 1)[-1].replace('.geojson', '.csv').replace('.json', '.csv')}"
        s3.put_object(Bucket=output_bucket, Key=output_key, Body=write_csv(rows).encode("utf-8"), ContentType="text/csv")
        processed.append({"source": f"s3://{bucket}/{key}", "output": f"s3://{output_bucket}/{output_key}", "rows": len(rows)})

    return {"statusCode": 200, "body": json.dumps({"processed": processed})}
