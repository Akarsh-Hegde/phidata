# config_models.py

from typing import List, Optional, Union, Callable, Dict, Any
from pydantic import BaseModel, Field
from phi.agent import Agent
from phi.knowledge.agent import AgentKnowledge

class ModelConfig(BaseModel):
    type: str
    config: Dict[str, Any] = {}

class VectorDBConfig(BaseModel):
    type: str
    config: Dict[str, Any] = {}

class KnowledgeBaseConfig(BaseModel):
    type: str
    config: Dict[str, Any] = {}

class AgentConfig(BaseModel):
    name: str
    role: Optional[str] = None
    instructions: Optional[Union[str, List[str], Callable]] = None
    knowledge_base: Optional[KnowledgeBaseConfig] = Field(None, alias="knowledge")
    model: Optional[ModelConfig] = None
    tools: Optional[List[Union[str, Dict[str, Any]]]] = None
    description: Optional[str] = None
    save_response_to_file: Optional[str] = None
    add_datetime_to_instructions: Optional[bool] = False
    show_tool_calls: Optional[bool] = False
    debug_mode: Optional[bool] = False
    markdown: Optional[bool] = False
    team: Optional[List[str]] = None
    read_chat_history: Optional[bool] = True

class Config(BaseModel):
    urls_file: Optional[str] = None
    agents: Dict[str, AgentConfig]
