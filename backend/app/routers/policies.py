from time import perf_counter

from fastapi import APIRouter, Query

from app.rag.chunker import (
    chunk_policy_documents,
    chunk_text,
)
from app.rag.loader import (
    load_all_policy_documents,
    load_policy_document,
)
from app.rag.retriever import retrieve_relevant_chunks
from app.rag.semantic_retriever import retrieve_semantic_chunks


router = APIRouter(
    prefix="/policies",
    tags=["Policy Knowledge Base"],
)


@router.get("")
def get_all_policies() -> dict:
    """Return metadata for all available policy documents."""

    policy_documents = load_all_policy_documents()

    return {
        "document_count": len(policy_documents),
        "documents": [
            {
                "filename": document["filename"],
                "character_count": len(document["content"]),
            }
            for document in policy_documents
        ],
    }


@router.get("/refund")
def get_refund_policy() -> dict[str, str]:
    """Return the refund policy document."""

    policy_text = load_policy_document("refund_policy.md")

    return {
        "filename": "refund_policy.md",
        "content": policy_text,
    }


@router.get("/refund/chunks")
def get_refund_policy_chunks() -> dict:
    """Return chunked refund policy content."""

    policy_text = load_policy_document("refund_policy.md")
    chunks = chunk_text(policy_text)

    return {
        "filename": "refund_policy.md",
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


@router.get("/chunks")
def get_all_policy_chunks() -> dict:
    """Return chunks generated from all policy documents."""

    policy_documents = load_all_policy_documents()

    policy_chunks = chunk_policy_documents(
        documents=policy_documents,
        chunk_size=500,
        overlap=80,
    )

    return {
        "document_count": len(policy_documents),
        "chunk_count": len(policy_chunks),
        "chunks": policy_chunks,
    }


@router.get("/search")
def search_all_policies(
    query: str,
    top_k: int = Query(
        default=3,
        ge=1,
        le=20,
    ),
) -> dict:
    """Search all policy documents using keyword retrieval."""

    policy_documents = load_all_policy_documents()

    policy_chunks = chunk_policy_documents(
        documents=policy_documents,
        chunk_size=500,
        overlap=80,
    )

    results = retrieve_relevant_chunks(
        query=query,
        chunks=policy_chunks,
        top_k=top_k,
    )

    return {
        "query": query,
        "retrieval_method": "keyword",
        "result_count": len(results),
        "results": results,
    }


@router.get("/semantic-search")
def semantic_search_all_policies(
    query: str,
    top_k: int = Query(
        default=3,
        ge=1,
        le=20,
    ),
    minimum_score: float = Query(
        default=0.25,
        ge=0.0,
        le=1.0,
    ),
) -> dict:
    """Search all policy documents using semantic embeddings."""

    start_time = perf_counter()

    policy_documents = load_all_policy_documents()

    policy_chunks = chunk_policy_documents(
        documents=policy_documents,
        chunk_size=500,
        overlap=80,
    )

    results = retrieve_semantic_chunks(
        query=query,
        chunks=policy_chunks,
        top_k=top_k,
        minimum_score=minimum_score,
    )

    latency_ms = round(
        (perf_counter() - start_time) * 1000,
        2,
    )

    return {
        "query": query,
        "retrieval_method": "semantic",
        "minimum_score": minimum_score,
        "result_count": len(results),
        "latency_ms": latency_ms,
        "results": results,
    }