from __future__ import annotations

import asyncio
import logging
import os
import sys
import tempfile
import traceback
from pathlib import Path

import azure.functions as func


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tweetpulse.bluesky_stream import DEFAULT_JETSTREAM_URL, collect_posts


app = func.FunctionApp()


def run_ingestion() -> None:
    max_posts = int(os.getenv("BLUESKY_MAX_POSTS", "500"))
    batch_size = int(os.getenv("BLUESKY_BATCH_SIZE", "100"))
    jetstream_url = os.getenv("BLUESKY_JETSTREAM_URL", DEFAULT_JETSTREAM_URL)

    logging.info(
        "Starting TweetPulse scheduled ingestion: max_posts=%s batch_size=%s",
        max_posts,
        batch_size,
    )
    output_dir = Path(tempfile.gettempdir()) / "tweetpulse" / "raw"
    asyncio.run(
        collect_posts(
            url=jetstream_url,
            output_dir=output_dir,
            batch_size=batch_size,
            max_posts=max_posts,
            upload_azure=True,
        )
    )
    logging.info("Finished TweetPulse scheduled ingestion.")


@app.timer_trigger(
    schedule="0 */30 * * * *",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def ingest_bluesky_posts(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logging.warning("TweetPulse timer trigger is past due.")
    run_ingestion()


@app.route(route="ingest-once", auth_level=func.AuthLevel.FUNCTION)
def ingest_once(req: func.HttpRequest) -> func.HttpResponse:
    try:
        run_ingestion()
    except Exception:
        logging.exception("TweetPulse manual ingestion failed.")
        return func.HttpResponse(traceback.format_exc(), status_code=500)
    return func.HttpResponse("TweetPulse ingestion completed.", status_code=200)
