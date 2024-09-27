from pydantic import BaseModel
from typing import List, Optional, Any, Dict

from fastapi import UploadFile


class AgentModel(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None


class AgentGetResponse(BaseModel):
    agent_id: str
    name: Optional[str] = None
    model: Optional[AgentModel] = None
    enable_rag: Optional[bool] = None
    tools: Optional[List[Dict[str, Any]]] = None
    memory: Optional[Dict[str, Any]] = None
    storage: Optional[Dict[str, Any]] = None
    knowledge: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    instructions: Optional[List[str]] = None


class AgentRunRequest(BaseModel):
    message: str
    agent_id: str
    stream: bool = True
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    image: Optional[UploadFile] = None


class AgentRenameRequest(BaseModel):
    name: str
    agent_id: str
    session_id: str


class GetAgentSessionsRequest(BaseModel):
    agent_id: str
    user_id: Optional[str] = None


class GetAgentSessionsResponse(BaseModel):
    session_id: Optional[str] = None
    title: Optional[str] = None
