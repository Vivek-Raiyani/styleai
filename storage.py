"""
Backblaze B2 storage helpers (S3-compatible).
All uploads return a presigned URL (7 days) safe to pass to YouCam API and display in UI.
"""
import os
import uuid
import base64
import time
import logging
from pathlib import Path
import boto3
from botocore.config import Config
import httpx
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("styleai.storage")

KEY_ID      = os.getenv("B2_KEY_ID", "")
SECRET_KEY  = os.getenv("B2_SECRET_KEY", "")
ENDPOINT    = os.getenv("B2_ENDPOINT", "https://s3.us-east-005.backblazeb2.com")
BUCKET      = os.getenv("B2_BUCKET", "")
URL_EXPIRY  = 604_800  # 7 days in seconds

def get_s3_client():
    key_id = os.getenv("B2_KEY_ID", KEY_ID)
    secret_key = os.getenv("B2_SECRET_KEY", SECRET_KEY)
    endpoint = os.getenv("B2_ENDPOINT", ENDPOINT)
    if not key_id or not secret_key:
        logger.warning("B2_KEY_ID and B2_SECRET_KEY are not configured.")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=key_id,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )

_s3 = get_s3_client()

_b2_auth_cache = {
    "download_url": None,
    "dl_auth_token": None,
    "expires_at": 0
}


def get_b2_download_url(key: str) -> str:
    """Generate a clean B2 native authorized download URL 100% compatible with external AI crawlers."""
    key_id = os.getenv("B2_KEY_ID", KEY_ID)
    secret_key = os.getenv("B2_SECRET_KEY", SECRET_KEY)
    bucket = os.getenv("B2_BUCKET", BUCKET)

    if not key_id or not secret_key or not bucket:
        logger.warning("B2 credentials or bucket name not configured.")
        return ""

    now = time.time()
    if not _b2_auth_cache["dl_auth_token"] or now >= _b2_auth_cache["expires_at"]:
        try:
            auth_header = 'Basic ' + base64.b64encode(f'{key_id}:{secret_key}'.encode()).decode()
            auth_res = requests.get('https://api.backblazeb2.com/b2api/v2/b2_authorize_account', headers={'Authorization': auth_header}, timeout=10).json()
            api_url = auth_res['apiUrl']
            auth_token = auth_res['authorizationToken']
            download_url = auth_res['downloadUrl']

            buckets_res = requests.post(f'{api_url}/b2api/v2/b2_list_buckets', headers={'Authorization': auth_token}, json={'accountId': auth_res['accountId']}, timeout=10).json()
            bucket_id = [b['bucketId'] for b in buckets_res['buckets'] if b['bucketName'] == bucket][0]

            dl_auth = requests.post(f'{api_url}/b2api/v2/b2_get_download_authorization', headers={'Authorization': auth_token}, json={
                'bucketId': bucket_id,
                'fileNamePrefix': '',
                'validDurationInSeconds': URL_EXPIRY
            }, timeout=10).json()

            _b2_auth_cache["download_url"] = download_url
            _b2_auth_cache["dl_auth_token"] = dl_auth['authorizationToken']
            _b2_auth_cache["expires_at"] = now + URL_EXPIRY - 3600
        except Exception as e:
            logger.warning(f"B2 native auth failed, falling back to S3 presigned URL: {e}")
            client = get_s3_client()
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=URL_EXPIRY,
            )

    return f"{_b2_auth_cache['download_url']}/file/{bucket}/{key}?Authorization={_b2_auth_cache['dl_auth_token']}"


# ─── Core upload ──────────────────────────────────────────────────────────────

def _upload(data: bytes, content_type: str, prefix: str = "styleai/uploads") -> dict:
    """
    Upload raw bytes to B2.
    Returns {"key": str, "url": str (7-day presigned)}.
    """
    bucket = os.getenv("B2_BUCKET", BUCKET)
    ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else \
          "png" if "png" in content_type else \
          "webp" if "webp" in content_type else "bin"
    key = f"{prefix}/{uuid.uuid4().hex}.{ext}"

    client = get_s3_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )

    url = get_b2_download_url(key)
    return {"key": key, "url": url}


# ─── Public API ───────────────────────────────────────────────────────────────

async def upload_fastapi_file(upload_file) -> dict:
    """Upload a FastAPI UploadFile. Returns {key, url}."""
    data = await upload_file.read()
    ct   = upload_file.content_type or "image/jpeg"
    return _upload(data, ct, prefix="styleai/selfies")


def upload_base64_image(b64_string: str) -> dict:
    """
    Upload a base64 image string (with or without data-URL prefix).
    Returns {key, url}.
    """
    if "," in b64_string:          # strip "data:image/png;base64,"
        header, b64_string = b64_string.split(",", 1)
        ct = header.split(":")[1].split(";")[0] if ":" in header else "image/jpeg"
    else:
        ct = "image/jpeg"
    data = base64.b64decode(b64_string)
    return _upload(data, ct, prefix="styleai/selfies")


async def download_and_upload(url: str, prefix: str = "styleai/results") -> dict:
    """
    Download a URL (e.g. expiring YouCam result) and re-upload to B2.
    Returns {key, url} with permanent 7-day presigned URL.
    """
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    ct = resp.headers.get("content-type", "image/jpeg").split(";")[0]
    return _upload(resp.content, ct, prefix=prefix)


def upload_bytes_sync(data: bytes, content_type: str, prefix: str = "styleai/assets") -> dict:
    """Synchronous upload (used in admin routes). Returns {key, url}."""
    return _upload(data, content_type, prefix=prefix)


def refresh_url(key: str) -> str:
    """Generate a fresh presigned URL for an existing B2 key."""
    return get_b2_download_url(key)
