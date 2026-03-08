"""
Bhasha-Setu — S3 Storage Service
Handles uploading local files to AWS S3.
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError

from pipeline.config import AWS_REGION, S3_BUCKET

log = logging.getLogger(__name__)


def upload_to_s3(local_path: str, s3_key: str = None) -> str:
    """
    Upload a local file to the Bhasha-Setu S3 bucket.

    Args:
        local_path: Path to the local file to upload.
        s3_key:     S3 object key. Defaults to the file's basename.

    Returns:
        The S3 URI: s3://<bucket>/<key>
    """
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"File not found: {local_path}")

    if s3_key is None:
        s3_key = os.path.basename(local_path)

    client = boto3.client("s3", region_name=AWS_REGION)

    try:
        log.info(f"Uploading {local_path} → s3://{S3_BUCKET}/{s3_key}")
        client.upload_file(local_path, S3_BUCKET, s3_key)
        uri = f"s3://{S3_BUCKET}/{s3_key}"
        log.info(f"Upload complete: {uri}")
        return uri

    except ClientError as e:
        raise RuntimeError(
            f"S3 upload failed for '{local_path}':\n{e}"
        ) from e
