"""
Thin HTTP wrapper — delegates all vector operations to the original
Sales-Expert-Agent service so this plugin stays lightweight and in sync.
"""

import httpx
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
        customer_filter: Optional[str] = None,
        tenant_id: str = "default",
        collection_type: str = "private",
    ) -> str:
        """Hybrid retrieval via parent service."""
        payload = {
            "query": query,
            "top_k": top_k,
            "customer_filter": customer_filter,
            "collection_type": collection_type,
        }
        headers = {"X-Tenant-ID": tenant_id}
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            resp = client.post(
                f"{self.base_url}/api/v1/retrieve",
                json=payload,
                headers=headers,
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
        """Sync conversation / profile fragments into parent service."""
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
        }
        headers = {"X-Tenant-ID": tenant_id}
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            resp = client.post(
                f"{self.base_url}/api/v1/sync",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()

    def delete_documents_by_source(self, source_path: str, tenant_id: str = "default") -> None:
        """No-op for now — parent service manages GC."""
        pass


memory_store = RemoteMemoryStore()
