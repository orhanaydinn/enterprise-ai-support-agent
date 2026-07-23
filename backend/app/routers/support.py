from fastapi import APIRouter

from app.agent.workflows import process_support_request
from app.models.requests import SupportRequest
from app.models.responses import SupportResponse


router = APIRouter(
    prefix="/support",
    tags=["Support Agent"],
)


@router.post(
    "/analyse",
    response_model=SupportResponse,
)
def analyse_support_request(
    request: SupportRequest,
) -> SupportResponse:
    """Analyse and process a customer support request."""

    return process_support_request(request)