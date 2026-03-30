import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .schemas import RetrieveRequest, RetrieveResponse, SyncRequest, SyncResponse
from .memory_store import memory_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("SalesExpertPlugin")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Sales-Expert Plugin started")
    yield
    logger.info("Sales-Expert Plugin shutting down")


app = FastAPI(title="Sales-Expert Plugin", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_tenant_id(x_tenant_id: str = Header(default="default")) -> str:
    return x_tenant_id


@app.post("/api/v1/retrieve", response_model=RetrieveResponse)
async def retrieve(req: RetrieveRequest, tenant_id: str = Depends(get_tenant_id)):
    """
    Hybrid search (vector + BM25 + rerank) via parent Sales-Expert-Agent service.
    """
    results = memory_store.search(
        query=req.query,
        top_k=req.top_k,
        customer_filter=req.customer_filter,
        tenant_id=tenant_id,
        collection_type=req.collection_type,
    )
    count = results.count("\n\n---\n\n") + 1 if "---" in results else (1 if results and "[未找到]" not in results else 0)
    return RetrieveResponse(results=results, query=req.query, count=count)


@app.post("/api/v1/sync", response_model=SyncResponse)
async def sync(req: SyncRequest, tenant_id: str = Depends(get_tenant_id)):
    """
    Ingest conversation turns and customer profile fragments into ChromaDB
    via parent service. Idempotent — safe to call after every session.
    """
    import datetime

    messages_stored = 0
    for turn in req.conversations:
        doc_content = f"[{turn.role.upper()}] {turn.content}"
        ts = turn.timestamp or datetime.datetime.now().isoformat()
        memory_store.add_documents(
            documents=[doc_content],
            metadatas=[{
                "source_dir": "conversations",
                "file_name": f"session_{req.session_id or 'unknown'}",
                "customer_name": req.customer_name or "unknown",
                "role": turn.role,
                "timestamp": ts,
            }],
            tenant_id=tenant_id,
        )
        messages_stored += 1

    profiles_stored = 0
    for profile in req.profiles:
        profile_doc = (
            f"客户: {profile.customer_name}\n"
            f"公司: {profile.company or '未知'}\n"
            f"行业: {profile.industry or '未知'}\n"
            f"跟进轮次: {profile.turn_count}\n"
            f"最后接触: {profile.last_contact or '未知'}\n"
            f"标签: {', '.join(profile.tags)}"
        )
        memory_store.add_documents(
            documents=[profile_doc],
            metadatas=[{
                "source_dir": "profiles",
                "file_name": profile.customer_name,
                "customer_name": profile.customer_name,
                "company": profile.company,
                "industry": profile.industry,
                "turn_count": str(profile.turn_count),
                "last_contact": profile.last_contact,
                "tags": ",".join(profile.tags),
            }],
            tenant_id=tenant_id,
        )
        profiles_stored += 1

    return SyncResponse(
        status="ok",
        messages_stored=messages_stored,
        profiles_stored=profiles_stored,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
