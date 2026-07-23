import re


def _split_long_text_by_words(
    text: str,
    chunk_size: int,
) -> list[str]:
    """Split oversized text without cutting words."""

    words = text.split()

    if not words:
        return []

    parts: list[str] = []
    current_words: list[str] = []
    current_length = 0

    for word in words:
        separator_length = 1 if current_words else 0
        proposed_length = current_length + separator_length + len(word)

        if current_words and proposed_length > chunk_size:
            parts.append(" ".join(current_words))

            current_words = [word]
            current_length = len(word)
            continue

        current_words.append(word)
        current_length = proposed_length

    if current_words:
        parts.append(" ".join(current_words))

    return parts


def _split_paragraph_into_units(
    paragraph: str,
    chunk_size: int,
) -> list[str]:
    """Split a paragraph into complete sentence-aware units."""

    if len(paragraph) <= chunk_size:
        return [paragraph]

    sentences = re.split(
        r"(?<=[.!?])\s+",
        paragraph,
    )

    units: list[str] = []

    for sentence in sentences:
        cleaned_sentence = sentence.strip()

        if not cleaned_sentence:
            continue

        if len(cleaned_sentence) <= chunk_size:
            units.append(cleaned_sentence)
            continue

        units.extend(
            _split_long_text_by_words(
                text=cleaned_sentence,
                chunk_size=chunk_size,
            )
        )

    return units


def _create_semantic_units(
    text: str,
    chunk_size: int,
) -> list[str]:
    """Create paragraph and sentence-aware text units."""

    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")

    paragraphs = re.split(
        r"\n\s*\n",
        normalized_text,
    )

    units: list[str] = []

    for paragraph in paragraphs:
        cleaned_paragraph = " ".join(paragraph.split())

        if not cleaned_paragraph:
            continue

        units.extend(
            _split_paragraph_into_units(
                paragraph=cleaned_paragraph,
                chunk_size=chunk_size,
            )
        )

    return units


def _select_overlap_units(
    previous_units: list[str],
    overlap: int,
) -> list[str]:
    """Select complete trailing units for the next chunk."""

    if overlap == 0:
        return []

    selected_units: list[str] = []
    selected_length = 0

    for unit in reversed(previous_units):
        separator_length = 2 if selected_units else 0
        proposed_length = (
            selected_length
            + separator_length
            + len(unit)
        )

        if proposed_length > overlap:
            break

        selected_units.insert(0, unit)
        selected_length = proposed_length

    return selected_units


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[str]:
    """Split text into paragraph and sentence-aware chunks."""

    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than zero.")

    if overlap < 0:
        raise ValueError("Overlap cannot be negative.")

    if overlap >= chunk_size:
        raise ValueError("Overlap must be smaller than chunk size.")

    semantic_units = _create_semantic_units(
        text=text,
        chunk_size=chunk_size,
    )

    if not semantic_units:
        return []

    chunks: list[str] = []
    current_units: list[str] = []
    current_length = 0

    for unit in semantic_units:
        separator_length = 2 if current_units else 0
        proposed_length = (
            current_length
            + separator_length
            + len(unit)
        )

        if current_units and proposed_length > chunk_size:
            completed_chunk = "\n\n".join(current_units).strip()

            if completed_chunk:
                chunks.append(completed_chunk)

            overlap_units = _select_overlap_units(
                previous_units=current_units,
                overlap=overlap,
            )

            current_units = overlap_units
            current_length = len(
                "\n\n".join(current_units)
            )

            separator_length = 2 if current_units else 0

            if (
                current_units
                and current_length
                + separator_length
                + len(unit)
                > chunk_size
            ):
                current_units = []
                current_length = 0

        separator_length = 2 if current_units else 0

        current_units.append(unit)
        current_length += separator_length + len(unit)

    if current_units:
        final_chunk = "\n\n".join(current_units).strip()

        if final_chunk:
            chunks.append(final_chunk)

    return chunks


def chunk_policy_documents(
    documents: list[dict[str, str]],
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[dict]:
    """Split policy documents into source-aware semantic chunks."""

    document_chunks: list[dict] = []

    for document in documents:
        chunks = chunk_text(
            text=document["content"],
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk_index, chunk in enumerate(chunks):
            document_chunks.append(
                {
                    "source": document["filename"],
                    "chunk_id": chunk_index,
                    "content": chunk,
                }
            )

    return document_chunks