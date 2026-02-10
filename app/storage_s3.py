from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from loguru import logger

_client = None
_config: Optional["S3Config"] = None


@dataclass
class S3Config:
    bucket: str
    endpoint_url: Optional[str] = None
    region_name: Optional[str] = None
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None


def configure(config: S3Config) -> None:
    global _client, _config
    _config = config
    _client = boto3.client(
        "s3",
        endpoint_url=config.endpoint_url or None,
        region_name=config.region_name or None,
        aws_access_key_id=config.access_key_id or None,
        aws_secret_access_key=config.secret_access_key or None,
    )
    logger.debug("S3 client configured for bucket {bucket}", bucket=config.bucket)


def _get_client():
    if _client is None or _config is None:
        raise RuntimeError("S3 storage is not configured")
    return _client


def upload_bytes(key: str, data: bytes, mime: str = "application/pdf") -> None:
    client = _get_client()
    client.put_object(Bucket=_config.bucket, Key=key, Body=data, ContentType=mime)
    logger.info("Uploaded protocol to S3", key=key, bucket=_config.bucket)


def generate_presigned_url(key: str, expire: int = 3600) -> str:
    client = _get_client()
    return client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": _config.bucket, "Key": key},
        ExpiresIn=expire,
    )


def exists(key: str) -> bool:
    client = _get_client()
    try:
        client.head_object(Bucket=_config.bucket, Key=key)
        return True
    except ClientError as exc:
        if exc.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
            return False
        raise


def get_size(key: str) -> Optional[int]:
    client = _get_client()
    try:
        response = client.head_object(Bucket=_config.bucket, Key=key)
        return response.get("ContentLength")
    except ClientError as exc:
        if exc.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
            return None
        raise


__all__ = [
    "S3Config",
    "configure",
    "upload_bytes",
    "generate_presigned_url",
    "exists",
    "get_size",
]
