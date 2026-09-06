import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from app.auth import authenticate
from app.config import Settings
from app.models import ChatRequest, ChatResponse, IngestRequest, Principal
from app.services.guardrails import check_input
from app.services.llm import Provider
from app.services.rag import RAG
from app.services.orchestrator import Orchestrator

logger = logging.getLogger("portfolio")
logging.basicConfig(level=logging.INFO)
# Do not log provider URLs, request bodies, bearer tokens or document content.
logging.getLogger("httpx").setLevel(logging.WARNING)


def create_app(settings=None, provider=None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        llm = provider or Provider(settings)
        rag = RAG(settings, llm)
        try:
            await rag.open()

            async def status_tool():
                return {
                    "service": "portfolio-api",
                    "status": "operational" if await rag.ready() else "unavailable",
                }

            app.state.rag = rag
            app.state.orchestrator = Orchestrator(llm, rag, status_tool)
            yield
        finally:
            await rag.close()
            await llm.close()

    app = FastAPI(
        title="Enterprise GenAI",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if settings.app_env == "production" else "/docs",
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["POST", "GET"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def observe(request: Request, call_next):
        rid, started = str(uuid4()), time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        logger.info(
            json.dumps(
                {
                    "request_id": rid,
                    "method": request.method,
                    "status": response.status_code,
                    "latency_ms": round((time.monotonic() - started) * 1000),
                }
            )
        )
        return response

    @app.get("/health")
    async def health():
        return {"status": "ok", "mode": settings.llm_provider}

    @app.get("/ready")
    async def ready():
        try:
            await app.state.rag.ready()
            return {"status": "ready"}
        except Exception:
            raise HTTPException(503, "Database unavailable") from None

    @app.post("/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest, principal: Principal = Depends(authenticate)):
        try:
            async with asyncio.timeout(settings.request_timeout):
                return await app.state.orchestrator.run(req.message, principal.tenant)
        except TimeoutError:
            raise HTTPException(504, "Request timed out") from None
        except Exception as exc:
            logger.error(json.dumps({"event": "chat_failed", "type": type(exc).__name__}))
            raise HTTPException(502, "AI dependency failed; retry later") from None

    @app.post("/documents", status_code=201)
    async def ingest(req: IngestRequest, principal: Principal = Depends(authenticate)):
        if principal.role != "admin":
            raise HTTPException(403, "Admin role required")
        if not check_input(req.text).allowed:
            raise HTTPException(422, "Document failed safety checks")
        try:
            async with asyncio.timeout(settings.request_timeout):
                count = await app.state.rag.ingest(principal.tenant, req.source, req.text)
            return {"source": req.source, "chunks": count}
        except ValueError:
            raise HTTPException(422, "Invalid document") from None
        except TimeoutError:
            raise HTTPException(504, "Ingestion timed out") from None
        except Exception:
            raise HTTPException(502, "Ingestion dependency failed") from None

    return app


app = create_app()
