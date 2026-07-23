from uuid import uuid4


def generate_request_id() -> str:
    """Generate a unique identifier for a support request."""

    return f"req_{uuid4().hex[:12]}"