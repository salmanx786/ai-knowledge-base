"""S3-compatible storage service."""

import boto3
from typing import IO
from app.config.settings import settings

class StorageService:
    def __init__(self):
        self._s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url,
        )
        self._bucket = settings.aws_bucket_name

    def upload_fileobj(self, file_obj: IO[bytes], key: str) -> None:
        """Upload a file-like object to S3."""
        self._s3.upload_fileobj(file_obj, self._bucket, key)

    def download_fileobj(self, key: str, file_obj: IO[bytes]) -> None:
        """Download a file from S3 into a file-like object."""
        self._s3.download_fileobj(self._bucket, key, file_obj)

    def delete_object(self, key: str) -> None:
        """Delete an object from S3."""
        self._s3.delete_object(Bucket=self._bucket, Key=key)

