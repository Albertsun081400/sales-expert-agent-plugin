from pydantic import BaseModel
from typing import Optional, Union


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 4
    customer_filter: Optional[Union[str, dict]] = None
    collection_type: str = "private"


class RetrieveResponse(BaseModel):
    results: str
    query: str
    count: int


class ConversationTurn(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class CustomerProfile(BaseModel):
    customer_name: str
    company: Optional[str] = None
    industry: Optional[str] = None
    turn_count: int = 0
    last_contact: Optional[str] = None
    tags: list[str] = []


class SyncRequest(BaseModel):
    conversations: list[ConversationTurn] = []
    profiles: list[CustomerProfile] = []
    session_id: Optional[str] = None
    customer_name: Optional[str] = None


class SyncResponse(BaseModel):
    status: str
    messages_stored: int = 0
    profiles_stored: int = 0
