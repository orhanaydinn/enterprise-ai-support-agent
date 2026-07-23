import re
from collections import Counter


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "but",
    "by",
    "can",
    "for",
    "from",
    "get",
    "has",
    "have",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "order",
    "the",
    "this",
    "to",
    "was",
    "with",
}


def tokenize(text: str) -> list[str]:
    """Convert text into normalized searchable tokens."""

    tokens = re.findall(
        r"[a-zA-Z0-9]+",
        text.lower(),
    )

    return [
        token
        for token in tokens
        if token not in STOP_WORDS and len(token) > 1
    ]


def calculate_relevance_score(
    query_tokens: list[str],
    chunk: dict,
) -> float:
    """Calculate a weighted keyword relevance score."""

    content_tokens = tokenize(chunk["content"])

    source_text = (
        chunk["source"]
        .replace("_", " ")
        .replace(".md", "")
    )
    source_tokens = tokenize(source_text)

    content_counts = Counter(content_tokens)
    query_counts = Counter(query_tokens)

    content_score = sum(
        min(
            query_counts[token],
            content_counts[token],
        )
        for token in query_counts
    )

    source_score = sum(
        3
        for token in set(query_tokens)
        if token in source_tokens
    )

    phrase_score = 0

    normalized_query = " ".join(query_tokens)
    normalized_content = " ".join(content_tokens)

    if (
        normalized_query
        and normalized_query in normalized_content
    ):
        phrase_score = 5

    return float(
        content_score
        + source_score
        + phrase_score
    )


def retrieve_relevant_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 3,
) -> list[dict]:
    """Return the most relevant source-aware chunks."""

    if top_k <= 0:
        raise ValueError("Top-k must be greater than zero.")

    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    scored_chunks: list[dict] = []

    for chunk in chunks:
        score = calculate_relevance_score(
            query_tokens=query_tokens,
            chunk=chunk,
        )

        if score <= 0:
            continue

        scored_chunks.append(
            {
                "source": chunk["source"],
                "chunk_id": chunk["chunk_id"],
                "content": chunk["content"],
                "score": score,
            }
        )

    ranked_chunks = sorted(
        scored_chunks,
        key=lambda item: (
            item["score"],
            item["source"],
            -item["chunk_id"],
        ),
        reverse=True,
    )

    return ranked_chunks[:top_k]