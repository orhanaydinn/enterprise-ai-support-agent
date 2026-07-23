from app.rag.chunker import chunk_policy_documents
from app.rag.loader import load_all_policy_documents
from app.rag.semantic_retriever import retrieve_semantic_chunks


POLICY_SCOPE: dict[str, set[str]] = {
    "refund_request": {
        "refund_policy.md",
        "escalation_policy.md",
    },
    "damaged_item_request": {
        "damaged_item_policy.md",
        "escalation_policy.md",
    },
    "cancellation_request": {
        "cancellation_policy.md",
        "escalation_policy.md",
    },
    "shipping_request": {
        "shipping_policy.md",
        "escalation_policy.md",
    },
    "late_delivery_request": {
        "shipping_policy.md",
        "escalation_policy.md",
    },
}


def select_policy_documents_for_intent(
    intent: str,
    documents: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Select policy documents that are relevant to an intent."""

    allowed_sources = POLICY_SCOPE.get(intent)

    if allowed_sources is None:
        return documents

    return [
        document
        for document in documents
        if document["filename"] in allowed_sources
    ]


def retrieve_policy_context(
    intent: str,
    query: str,
    top_k: int = 3,
    minimum_score: float = 0.25,
) -> dict:
    """Retrieve semantic policy context for a support workflow."""

    all_documents = load_all_policy_documents()

    selected_documents = select_policy_documents_for_intent(
        intent=intent,
        documents=all_documents,
    )

    selected_sources = [
        document["filename"]
        for document in selected_documents
    ]

    if not selected_documents:
        return {
            "selected_sources": [],
            "chunks": [],
            "context": "",
            "highest_score": None,
        }

    policy_chunks = chunk_policy_documents(
        documents=selected_documents,
        chunk_size=500,
        overlap=80,
    )

    retrieved_chunks = retrieve_semantic_chunks(
        query=query,
        chunks=policy_chunks,
        top_k=top_k,
        minimum_score=minimum_score,
    )

    if not retrieved_chunks:
        return {
            "selected_sources": selected_sources,
            "chunks": [],
            "context": "",
            "highest_score": None,
        }

    policy_context = "\n\n".join(
        (
            f"Source: {chunk['source']}\n"
            f"Reference: chunk_{chunk['chunk_id']}\n"
            f"{chunk['content']}"
        )
        for chunk in retrieved_chunks
    )

    return {
        "selected_sources": selected_sources,
        "chunks": retrieved_chunks,
        "context": policy_context,
        "highest_score": retrieved_chunks[0]["score"],
    }