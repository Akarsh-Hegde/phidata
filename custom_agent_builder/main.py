# main.py

import logging
import sys
from pathlib import Path
import argparse
from typing import Dict, List, Union
import yaml
from pydantic import ValidationError
import os
from dotenv import load_dotenv

from custom_agent_builder.tools_loader import load_selected_tools
from phi.tools.toolkit import Toolkit
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.model.groq import Groq
from phi.model.google import Gemini
from phi.storage.agent.postgres import PgAgentStorage
from config_models import Config, AgentConfig, ModelConfig, KnowledgeBaseConfig
from phi.vectordb.registry import get_vector_db_class
from phi.knowledge.registry import get_knowledge_base_class

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Run agents based on YAML configuration.")
    parser.add_argument("--config", type=str, required=True, help="Path to the YAML configuration file.")
    parser.add_argument("--agent", type=str, required=True, help="Name of the agent to run.")
    return parser.parse_args()


def load_config(config_path: str) -> Config:
    try:
        with open(config_path, "r") as file:
            raw_config = yaml.safe_load(file)
        config = Config(**raw_config)
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except ValidationError as e:
        logger.error("Configuration validation error:")
        logger.error(e)
        sys.exit(1)


def create_tool_instance(tool_spec: Union[str, dict], registry: Dict[str, type], base_dir: Path) -> Toolkit:
    if isinstance(tool_spec, str):
        tool_name = tool_spec
        tool_config = {}
    elif isinstance(tool_spec, dict):
        tool_name = tool_spec.get("name")
        tool_config = tool_spec.get("config", {})
    else:
        logger.error(f"Invalid tool specification: {tool_spec}")
        sys.exit(1)

    cls = registry.get(tool_name)
    if not cls:
        logger.error(f"Tool '{tool_name}' not found in phi.tools registry.")
        sys.exit(1)

    if cls.__name__ == "FileTools":
        return cls(base_dir=base_dir, **tool_config)
    else:
        return cls(**tool_config)


def initialize_tools(properties: Config) -> Dict[str, List[Toolkit]]:
    unique_tool_names = set()
    
    # Collect unique tool names
    for agent_cfg in properties.agents.values():
        if agent_cfg.tools:
            for tool in agent_cfg.tools:
                if isinstance(tool, str):
                    unique_tool_names.add(tool)
                elif isinstance(tool, dict) and "name" in tool:
                    unique_tool_names.add(tool["name"])

    loaded_tools = load_selected_tools(unique_tool_names)
    agent_tools_map = {}

    # Initialize tools for each agent
    for agent_key, agent_cfg in properties.agents.items():
        tool_instances = []
        if agent_cfg.tools:
            for tool_spec in agent_cfg.tools:
                if isinstance(tool_spec, str):
                    tool_name = tool_spec
                    tool_config = {}
                else:
                    tool_name = tool_spec["name"]
                    tool_config = tool_spec.get("properties", {})

                tool_cls = loaded_tools.get(tool_name)
                if not tool_cls:
                    logger.error(f"Tool '{tool_name}' not found in loaded tools.")
                    sys.exit(1)

                if tool_cls.__name__ == "FileTools":
                    base_dir = tool_config.get("base_dir", Path(properties.urls_file).parent if properties.urls_file else Path("."))
                    tool_config.pop("base_dir", None)  # Prevent duplicate argument
                    tool_instances.append(tool_cls(base_dir=base_dir, **tool_config))
                else:
                    tool_instances.append(tool_cls(**tool_config))

        agent_tools_map[agent_key] = tool_instances

    return agent_tools_map


def create_knowledge_base(kb_config: KnowledgeBaseConfig):
    if not kb_config:
        return None

    kb_type = kb_config.type
    kb_opts = kb_config.config or {}

    vector_db_opts = kb_opts.pop("vector_db", None)
    vector_db_instance = None
    if vector_db_opts:
        vdb_type = vector_db_opts.get("type")
        vdb_config = vector_db_opts.get("config", {})
        if vdb_type:
            try:
                vdb_cls = get_vector_db_class(vdb_type)
                vector_db_instance = vdb_cls(**vdb_config)
            except ValueError as ve:
                logger.error(f"Error: {ve}")
                sys.exit(1)
            except TypeError as te:
                logger.error(f"Error initializing VectorDB '{vdb_type}': {te}")
                sys.exit(1)

    try:
        kb_cls = get_knowledge_base_class(kb_type)
    except ValueError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

    try:
        kb_instance = kb_cls(vector_db=vector_db_instance, **kb_opts)
    except TypeError as te:
        logger.error(f"Error initializing KnowledgeBase '{kb_type}': {te}")
        sys.exit(1)

    load_upsert = kb_opts.get("load_upsert", False)
    if load_upsert and hasattr(kb_instance, "load"):
        try:
            kb_instance.load(upsert=True, recreate=False)
            logger.info(f"Knowledge base of type '{kb_type}' loaded with upsert=True")
        except Exception as e:
            logger.error(f"KB load encountered an error: {e}")

    return kb_instance


def create_model(model_config: ModelConfig):
    if not model_config:
        return None

    model_type = model_config.type
    model_opts = model_config.config or {}

    MODEL_CLASSES = {
        "OpenAIChat": OpenAIChat,
        "Groq": Groq,
        "Gemini": Gemini,
    }

    cls = MODEL_CLASSES.get(model_type)
    if not cls:
        logger.error(f"Unsupported model type: {model_type}")
        sys.exit(1)

    try:
        model_instance = cls(**model_opts)
        return model_instance
    except TypeError as te:
        logger.error(f"Error initializing model '{model_type}': {te}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error initializing model '{model_type}': {e}")
        sys.exit(1)


def initialize_storage():
    """Initialize PostgreSQL storage with Neon DB connection"""
    db_url = os.getenv('NEON_DB_URL')
    if not db_url:
        logger.error("NEON_DB_URL environment variable not set")
        sys.exit(1)
    return PgAgentStorage(table_name="agent_sessions", db_url=db_url)


def initialize_agents(config: Config, agent_tools_map: Dict[str, List[Toolkit]], chat_id: str = None) -> Dict[str, Agent]:
    agents: Dict[str, Agent] = {}
    agent_team_map = {}

    # Initialize storage once for all agents
    storage = initialize_storage()

    for agent_key, agent_cfg in config.agents.items():
        if agent_cfg.save_response_to_file and config.urls_file:
            agent_cfg.save_response_to_file = agent_cfg.save_response_to_file.replace(
                "{{urls_file}}", str(Path(config.urls_file))
            )

        if agent_cfg.instructions and config.urls_file:
            if isinstance(agent_cfg.instructions, list):
                agent_cfg.instructions = [
                    instr.replace("{{urls_file}}", Path(config.urls_file).name)
                    if isinstance(instr, str) else instr
                    for instr in agent_cfg.instructions
                ]
            elif isinstance(agent_cfg.instructions, str):
                agent_cfg.instructions = agent_cfg.instructions.replace(
                    "{{urls_file}}", Path(config.urls_file).name
                )

        knowledge = create_knowledge_base(agent_cfg.knowledge_base)
        model = create_model(agent_cfg.model)
        tool_instances = agent_tools_map.get(agent_key, [])
        team_names = agent_cfg.team

        try:
            agent = Agent(
                name=agent_cfg.name,
                role=agent_cfg.role,
                instructions=agent_cfg.instructions,
                knowledge=knowledge,
                tools=tool_instances,
                description=agent_cfg.description,
                save_response_to_file=agent_cfg.save_response_to_file,
                add_datetime_to_instructions=agent_cfg.add_datetime_to_instructions,
                show_tool_calls=agent_cfg.show_tool_calls,
                debug_mode=agent_cfg.debug_mode,
                markdown=agent_cfg.markdown,
                read_chat_history=agent_cfg.read_chat_history,
                model=model,
                storage=storage,  # Add storage configuration
                chat_id=chat_id,  # Add chat_id parameter
                add_history_to_messages=True  # Enable chat history
            )
            agents[agent_cfg.name] = agent
        except Exception as e:
            logger.error(f"Error initializing agent '{agent_cfg.name}': {e}")
            sys.exit(1)

        if team_names:
            agent_team_map[agent_cfg.name] = team_names

    # Resolve team references
    for agent_name, member_names in agent_team_map.items():
        member_agents = []
        for member_name in member_names:
            member_agent = agents.get(member_name)
            if not member_agent:
                logger.error(f"Team member '{member_name}' for agent '{agent_name}' not found.")
                sys.exit(1)
            member_agents.append(member_agent)
        agents[agent_name].team = member_agents

    return agents


def main():
    args = parse_arguments()
    config = load_config(args.config)

    # Ensure urls_file directory exists if specified
    if config.urls_file:
        urls_path = Path(config.urls_file)
        urls_path.parent.mkdir(parents=True, exist_ok=True)

    tool_registry = initialize_tools(config)
    agents = initialize_agents(config, tool_registry)
    logger.info(f"Initialized agents: {list(agents.keys())}")

    target_agent = agents.get(args.agent)
    if not target_agent:
        logger.error(f"Agent '{args.agent}' not found in configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()