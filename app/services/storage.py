from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings



def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket_exists(bucket: str) -> None:
    s3 = _get_s3_client()
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError:
        s3.create_bucket(Bucket=bucket)


def upload_stream(fileobj: BinaryIO, original_name: str, content_type: str) -> str:
    """
    Загружает файл в MinIO и возвращает object_key.
    """
    s3 = _get_s3_client()
    bucket = settings.s3_bucket

    safe_name = original_name.replace("/", "_").replace("\\", "_")
    object_key = f"uploads/{uuid.uuid4()}-{safe_name}"

    s3.upload_fileobj(
        Fileobj=fileobj,
        Bucket=bucket,
        Key=object_key,
        ExtraArgs={"ContentType": content_type},
    )

    return object_key
