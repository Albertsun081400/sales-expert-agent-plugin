"""
Thin HTTP wrapper — delegates all vector operations to the original
Sales-Expert-Agent service so this plugin stays lightweight and in sync.
"""

import httpx
import uuid
from typing import Optional
from .config import SALES_EXPERT_BASE_URL, TIMEOUT_SECONDS
from .schemas import (
    RetrieveRequest,
    RetrieveResponse,
    SyncRequest,
    SyncResponse,
)


class RemoteMemoryStore:
    """Calls the parent service's /api/v1/* endpoints."""

    def __init__(self, base_url: str = SALES_EXPERT_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def search(
        self,
        query: str,
        top_k: int = 4,
        customer_filter: Optional[dict] = None,
        tenant_id: str = "default",
        collection_type: str = "private",
    ) -> str:
        """Hybrid retrieval via parent service internal endpoint (no auth)."""
        # Build proper customer_filter dict for parent service
        filter_dict = None
        if customer_filter:
            if isinstance(customer_filter, str):
                filter_dict = {"customer_name": customer_filter, "tenant_id": tenant_id}
            elif isinstance(customer_filter, dict):
                filter_dict = customer_filter
                if "tenant_id" not in filter_dict:
                    filter_dict["tenant_id"] = tenant_id
        else:
            filter_dict = {"tenant_id": tenant_id}
        
        payload = {
            "query": query,
            "top_k": top_k,
            "customer_filter": filter_dict,
            "collection_type": collection_type,
        }
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            resp = client.post(
                f"{self.base_url}/api/v1/internal/retrieve",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["results"]

    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict],
        tenant_id: str = "default",
        collection_type: str = "private",
    ) -> None:
        """Sync conversation / profile fragments into parent service via internal endpoint."""
        ids = [str(uuid.uuid4()) for _ in documents]
        payload = {
            "conversations": [
                {
                    "role": m.get("role", "user"),
                    "content": doc,
                    "timestamp": m.get("timestamp"),
                }
                for doc, m in zip(documents, metadatas)
            ],
            "session_id": metadatas[0].get("file_name", "unknown") if metadatas else None,
            "customer_name": metadatas[0].get("customer_name") if metadatas else None,
            "profiles": [],
            "tenant_id": tenant_id,
            "ids": ids,
        }
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            resp = client.post(
                f"{self.base_url}/api/v1/internal/sync",
                json=payload,
            )
            resp.raise_for_status()

    def delete_documents_by_source(self, source_path: str, tenant_id: str = "default") -> None:
        """No-op for now — parent service manages GC."""
        pass


memory_store = RemoteMemoryStore()
