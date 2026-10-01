from __future__ import annotations

import time

from tweetpulse.blob_storage import upload_file
from tweetpulse.config import LOCAL_BLOB_DIR
from tweetpulse.synthetic_stream import write_batch


def main() -> None:
    while True:
        batch_path = write_batch(LOCAL_BLOB_DIR, batch_size=100)
        upload_file(batch_path)
        print(f"Uploaded {batch_path.name}")
        time.sleep(60)


if __name__ == "__main__":
    main()
