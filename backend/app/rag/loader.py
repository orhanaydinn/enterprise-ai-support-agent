import os
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError


POLICIES_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "policies"
)

POLICY_BUCKET_NAME = os.getenv("POLICY_BUCKET_NAME")
POLICY_S3_PREFIX = os.getenv(
    "POLICY_S3_PREFIX",
    "policies/",
)


@lru_cache(maxsize=1)
def get_s3_client():
    """Create and cache an Amazon S3 client."""

    return boto3.client("s3")


def load_local_policy_document(filename: str) -> str:
    """Load a single policy document from the local policies directory."""

    policy_path = POLICIES_DIRECTORY / filename

    if not policy_path.exists():
        raise FileNotFoundError(
            f"Policy document not found: {filename}"
        )

    return policy_path.read_text(
        encoding="utf-8",
    )


def load_s3_policy_document(filename: str) -> str:
    """Load a single policy document from Amazon S3."""

    if not POLICY_BUCKET_NAME:
        raise RuntimeError(
            "POLICY_BUCKET_NAME is not configured."
        )

    object_key = f"{POLICY_S3_PREFIX.rstrip('/')}/{filename}"

    response = get_s3_client().get_object(
        Bucket=POLICY_BUCKET_NAME,
        Key=object_key,
    )

    return response["Body"].read().decode("utf-8")


def load_policy_document(filename: str) -> str:
    """Load a policy document from S3 with a local fallback."""

    if POLICY_BUCKET_NAME:
        try:
            return load_s3_policy_document(filename)

        except (BotoCoreError, ClientError):
            pass

    return load_local_policy_document(filename)


def load_local_policy_documents() -> list[dict[str, str]]:
    """Load all Markdown policy documents from the local directory."""

    policy_documents: list[dict[str, str]] = []

    for policy_path in sorted(
        POLICIES_DIRECTORY.glob("*.md")
    ):
        content = policy_path.read_text(
            encoding="utf-8",
        ).strip()

        if not content:
            continue

        policy_documents.append(
            {
                "filename": policy_path.name,
                "content": content,
            }
        )

    return policy_documents


def load_s3_policy_documents() -> list[dict[str, str]]:
    """Load all Markdown policy documents from Amazon S3."""

    if not POLICY_BUCKET_NAME:
        return []

    policy_documents: list[dict[str, str]] = []

    paginator = get_s3_client().get_paginator(
        "list_objects_v2"
    )

    pages = paginator.paginate(
        Bucket=POLICY_BUCKET_NAME,
        Prefix=POLICY_S3_PREFIX,
    )

    for page in pages:
        for object_data in page.get("Contents", []):
            object_key = object_data["Key"]

            if not object_key.lower().endswith(".md"):
                continue

            response = get_s3_client().get_object(
                Bucket=POLICY_BUCKET_NAME,
                Key=object_key,
            )

            content = (
                response["Body"]
                .read()
                .decode("utf-8")
                .strip()
            )

            if not content:
                continue

            policy_documents.append(
                {
                    "filename": Path(object_key).name,
                    "content": content,
                }
            )

    policy_documents.sort(
        key=lambda document: document["filename"]
    )

    return policy_documents


def load_all_policy_documents() -> list[dict[str, str]]:
    """Load policies from S3 with a local development fallback."""

    if POLICY_BUCKET_NAME:
        try:
            s3_documents = load_s3_policy_documents()

            if s3_documents:
                return s3_documents

        except (BotoCoreError, ClientError):
            pass

    return load_local_policy_documents()