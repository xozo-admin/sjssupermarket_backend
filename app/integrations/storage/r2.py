import asyncio
from pathlib import Path
from time import monotonic

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile

from app.config import settings
from app.exceptions import AppError

ALLOWED_TYPES = {"image/webp": ".webp", "image/jpeg": ".jpg", "image/png": ".png"}
MAX_IMAGE_SIZE = 8 * 1024 * 1024
_key_cache: tuple[float, set[str]] | None = None
_key_cache_lock = asyncio.Lock()


class R2Storage:
    def __init__(self) -> None:
        if not all(
            (
                settings.r2_endpoint_url,
                settings.r2_access_key_id,
                settings.r2_secret_access_key,
                settings.r2_bucket_name,
            )
        ):
            raise AppError("R2 upload is not configured on the server", 503)
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )

    async def read_image(self, upload: UploadFile) -> tuple[bytes, str]:
        if upload.content_type not in ALLOWED_TYPES:
            raise AppError("Upload a WEBP, JPG, or PNG image", 422)
        content = await upload.read(MAX_IMAGE_SIZE + 1)
        if len(content) > MAX_IMAGE_SIZE:
            raise AppError("Image must be 8 MB or smaller", 422)
        if not content:
            raise AppError("The uploaded image is empty", 422)
        return content, ALLOWED_TYPES[upload.content_type]

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        global _key_cache
        try:
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=settings.r2_bucket_name,
                Key=key,
                Body=content,
                ContentType=content_type,
                CacheControl="public, max-age=300, must-revalidate",
            )
            _key_cache = None
        except ClientError as exc:
            error = exc.response.get("Error", {})
            code = error.get("Code", "R2Error")
            if code in {
                "AccessDenied",
                "InvalidAccessKeyId",
                "SignatureDoesNotMatch",
                "Unauthorized",
            }:
                raise AppError(
                    "R2 rejected the upload credentials. Create an R2 API token with Object Read & Write access to the grocery-images bucket, then restart the API.",
                    503,
                ) from exc
            raise AppError(f"R2 upload failed ({code})", 502) from exc
        except BotoCoreError as exc:
            raise AppError("Could not connect to R2 storage", 502) from exc

    async def list_keys(self, max_age: int = 60) -> set[str]:
        global _key_cache
        if _key_cache and monotonic() - _key_cache[0] < max_age:
            return _key_cache[1]
        async with _key_cache_lock:
            if _key_cache and monotonic() - _key_cache[0] < max_age:
                return _key_cache[1]

            def fetch() -> set[str]:
                keys: set[str] = set()
                paginator = self.client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=settings.r2_bucket_name):
                    keys.update(item["Key"] for item in page.get("Contents", []))
                return keys

            try:
                keys = await asyncio.to_thread(fetch)
            except (BotoCoreError, ClientError) as exc:
                raise AppError("Could not check R2 image availability", 502) from exc
            _key_cache = (monotonic(), keys)
            return keys

    @staticmethod
    def safe_filename(name: str, extension: str) -> str:
        stem = Path(name).stem.lower().strip().replace(" ", "-")
        return f"{stem}{extension}"

    @staticmethod
    def public_url(key: str) -> str:
        return f"{settings.r2_public_base_url.rstrip('/')}/{key}"
