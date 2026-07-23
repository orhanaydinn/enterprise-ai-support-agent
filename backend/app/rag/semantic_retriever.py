import json
import math
import os
from functools import lru_cache

import boto3
from botocore.client import BaseClient


BEDROCK_REGION = os.getenv(
    "AWS_REGION_NAME",
    os.getenv("AWS_REGION", "eu-west-2"),
)

EMBEDDING_MODEL_ID = os.getenv(
    "BEDROCK_EMBEDDING_MODEL_ID",
    "amazon.titan-embed-text-v2:0",
)

EMBEDDING_DIMENSIONS = int(
    os.getenv("BEDROCK_EMBEDDING_DIMENSIONS", "256")
)


@lru_cache(maxsize=1)
def get_bedrock_runtime_client() -> BaseClient:
    """Create and cache the Amazon Bedrock Runtime client."""

    return boto3.client(
        "bedrock-runtime",
        region_name=BEDROCK_REGION,
    )


def generate_embedding(text: str) -> tuple[float, ...]:
    """Generate a normalized embedding using Amazon Bedrock."""

    normalized_text = text.strip()

    if not normalized_text:
        raise ValueError("Embedding text must not be empty.")

    request_body = {
        "inputText": normalized_text,
        "dimensions": EMBEDDING_DIMENSIONS,
        "normalize": True,
    }

    response = get_bedrock_runtime_client().invoke_model(
        modelId=EMBEDDING_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body),
    )

    response_body = json.loads(
        response["body"].read().decode("utf-8")
    )

    embedding = response_body.get("embedding")

    if not isinstance(embedding, list) or not embedding:
        raise RuntimeError(
            "Amazon Bedrock returned an invalid embedding response."
        )

    return tuple(float(value) for value in embedding)


@lru_cache(maxsize=16)
def encode_documents(
    document_texts: tuple[str, ...],
) -> tuple[tuple[float, ...], ...]:
    """Generate and cache embeddings for policy document chunks."""

    return tuple(
        generate_embedding(document_text)
        for document_text in document_texts
    )


def calculate_cosine_similarity(
    first_vector: tuple[float, ...],
    second_vector: tuple[float, ...],
) -> float:
    """Calculate cosine similarity between two embedding vectors."""

    if len(first_vector) != len(second_vector):
        raise ValueError(
            "Embedding vectors must have the same dimensions."
        )

    dot_product = sum(
        first_value * second_value
        for first_value, second_value in zip(
            first_vector,
            second_vector,
            strict=True,
        )
    )

    first_magnitude = math.sqrt(
        sum(value * value for value in first_vector)
    )

    second_magnitude = math.sqrt(
        sum(value * value for value in second_vector)
    )

    denominator = first_magnitude * second_magnitude

    if denominator == 0.0:
        return 0.0

    return dot_product / denominator


def retrieve_semantic_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 3,
    minimum_score: float = 0.25,
) -> list[dict]:
    """Return the most semantically relevant source-aware chunks."""

    if top_k <= 0:
        raise ValueError("Top-k must be greater than zero.")

    if not 0.0 <= minimum_score <= 1.0:
        raise ValueError(
            "Minimum score must be between zero and one."
        )

    normalized_query = query.strip()

    if not normalized_query or not chunks:
        return []

    document_texts = tuple(
        chunk["content"]
        for chunk in chunks
    )

    query_embedding = generate_embedding(normalized_query)
    document_embeddings = encode_documents(document_texts)

    scored_chunks: list[tuple[int, float]] = []

    for index, document_embedding in enumerate(
        document_embeddings
    ):
        score = calculate_cosine_similarity(
            query_embedding,
            document_embedding,
        )

        scored_chunks.append((index, score))

    scored_chunks.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    results: list[dict] = []

    for index, score in scored_chunks:
        if score < minimum_score:
            continue

        chunk = chunks[index]

        results.append(
            {
                "source": chunk["source"],
                "chunk_id": chunk["chunk_id"],
                "content": chunk["content"],
                "score": round(score, 4),
                "retrieval_method": "bedrock_semantic",
            }
        )

        if len(results) >= top_k:
            break

    return results