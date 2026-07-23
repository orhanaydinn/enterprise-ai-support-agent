from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.policies import router as policies_router
from app.routers.support import router as support_router


app = FastAPI(
    title="Enterprise AI Support Agent",
    version="0.2.0",
    description=(
        "An enterprise support agent with intent classification, "
        "semantic policy retrieval, deterministic business rules, "
        "citations, and execution traces."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4173",
        "http://localhost:5173",
        "https://d1qo68bktehjcu.cloudfront.net",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(support_router)
app.include_router(policies_router)


@app.get("/")
def root() -> dict[str, str]:
    """Return basic service information."""

    return {
        "service": "Enterprise AI Support Agent",
        "version": "0.2.0",
        "status": "running",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return the current health status of the API."""

    return {
        "status": "healthy",
        "service": "enterprise-ai-support-agent",
    }