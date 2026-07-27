import asyncio
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile

from app.config import settings
from app.exceptions import AppError

ALLOWED_TYPES = {"image/webp": ".webp", "image/jpeg": ".jpg", "image/png": ".png"}
MAX_IMAGE_SIZE = 8 * 1024 * 1024


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
        try:
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=settings.r2_bucket_name,
                Key=key,
                Body=content,
                ContentType=content_type,
                CacheControl="public, max-age=300, must-revalidate",
            )
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

    @staticmethod
    def safe_filename(name: str, extension: str) -> str:
        stem = Path(name).stem.lower().strip().replace(" ", "-")
        return f"{stem}{extension}"

    @staticmethod
    def public_url(key: str) -> str:
        return f"{settings.r2_public_base_url.rstrip('/')}/{key}"
