"""
Sales-Expert MCP Server — Industrial standard for Claude/Cursor integration.
Acts as a high-level tool set for AI Agents to interact with the Sales-Expert-Agent backend.
"""

import httpx
from mcp.server.fastmcp import FastMCP
from .config import SALES_EXPERT_BASE_URL, TIMEOUT_SECONDS
from .memory_store import RemoteMemoryStore

# Initialize FastMCP
mcp = FastMCP("SalesExpert")
store = RemoteMemoryStore(SALES_EXPERT_BASE_URL)

@mcp.tool()
def retrieve_knowledge(
    query: str, 
    scoped_id: str, 
    customer_name: str = None, 
    top_k: int = 3
) -> str:
    """
    Search for sales strategies, battle logs, and customer history.
    Args:
        query: The search intent or client question.
        scoped_id: The Scoped-ID (tenant/user) from your settings card.
        customer_name: Optional filter to search specific client data.
        top_k: Number of relevant fragments to return.
    """
    try:
        # RemoteMemoryStore.search takes (query, top_k, customer_filter, tenant_id)
        results = store.search(
            query=query,
            top_k=top_k,
            customer_filter=customer_name,
            tenant_id=scoped_id
        )
        return results if results else "[NO_DATA] No relevant sales records found for this user/tenant."
    except Exception as e:
        return f"[ERROR] Failed to connect to Sales-Expert backend: {str(e)}"

@mcp.tool()
def sync_turn(
    role: str, 
    content: str, 
    scoped_id: str, 
    customer_name: str, 
    session_id: str = "mcp_session"
) -> str:
    """
    Save a conversation turn into the RAG memory for future retrieval.
    Args:
        role: Either 'user' or 'assistant'.
        content: The text of the conversation.
        scoped_id: The Scoped-ID (tenant/user) from settings.
        customer_name: The client associated with this memory.
        session_id: Optional ID to group these memories.
    """
    try:
        store.add_documents(
            documents=[content],
            metadatas=[{
                "role": role,
                "customer_name": customer_name,
                "file_name": session_id
            }],
            tenant_id=scoped_id
        )
        return f"[SUCCESS] Memory synced for {customer_name}."
    except Exception as e:
        return f"[ERROR] Failed to sync memory: {str(e)}"

if __name__ == "__main__":
    mcp.run()
