from __future__ import annotations

import json
import os
from urllib.parse import unquote_plus

import boto3


glue = boto3.client("glue")


def lambda_handler(event, context):
    job_name = os.environ["GLUE_JOB_NAME"]
    curated_bucket = os.environ["CURATED_BUCKET"]
    redshift_tmp_dir = os.environ.get("REDSHIFT_TMP_DIR")
    redshift_jdbc_url = os.environ.get("REDSHIFT_JDBC_URL")
    raw_prefix = os.environ.get("RAW_PREFIX", "raw/")
    started_jobs = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        if not key.startswith(raw_prefix):
            continue

        arguments = {
            "--SOURCE_BUCKET": bucket,
            "--CURATED_BUCKET": curated_bucket,
            "--SOURCE_KEY": key,
            "--LOAD_DATE": key.split("/")[-2] if "/" in key else "manual",
        }
        if redshift_tmp_dir and redshift_jdbc_url:
            arguments["--REDSHIFT_TMP_DIR"] = redshift_tmp_dir
            arguments["--REDSHIFT_JDBC_URL"] = redshift_jdbc_url

        response = glue.start_job_run(JobName=job_name, Arguments=arguments)
        started_jobs.append({"source": f"s3://{bucket}/{key}", "job_run_id": response["JobRunId"]})

    return {
        "statusCode": 202,
        "body": json.dumps({"started_jobs": started_jobs}),
    }
