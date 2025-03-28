from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yaml
import os

app = FastAPI(root_path="/agent-api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_DIR = "custom_agent_builder/agent_configs"

@app.post("/api/save-yaml/{agent_name}")
async def save_yaml(agent_name: str, request: Request):
    data = await request.json()
    yaml_config = data.get("yamlConfig")
    
    # Replace spaces with underscores in the agent name
    safe_agent_name = agent_name.replace(" ", "_")
    
    try:
        parsed = yaml.safe_load(yaml_config)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")
    
    # Ensure the config directory exists
    file_path = os.path.join(CONFIG_DIR, f"{safe_agent_name}.yaml")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    try:
        with open(file_path, "w") as f:
            f.write(yaml_config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    return {"success": True, "path": file_path, "agent_name": safe_agent_name}

@app.get("/api/agents")
def list_agents():
    """Returns a list of available agents based on the YAML files in agent_configs directory."""
    if not os.path.exists(CONFIG_DIR):
        return []
    
    files = os.listdir(CONFIG_DIR)
    agents = [os.path.splitext(f)[0] for f in files if f.endswith((".yaml", ".yml"))]
    return agents

class ChatRequest(BaseModel):
    message: str
    chat_id: str = None

@app.post("/api/agent/{agent_name}/chat")
def chat_with_agent(agent_name: str, request: ChatRequest):
    # Convert URL agent name to file name
    file_path = os.path.join(CONFIG_DIR, f"{agent_name}.yaml")
    print(f"Looking for file at: {file_path}")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Agent config not found: {agent_name}")

    from custom_agent_builder.main import load_config, initialize_tools, initialize_agents
    config = load_config(file_path)
    tool_registry = initialize_tools(config)
    agents = initialize_agents(config, tool_registry, chat_id=request.chat_id)

    # If there's only one agent in the config, use it
    if len(agents) == 1:
        target_agent = list(agents.values())[0]
    else:
        # Try to find the agent by matching against the first part of the agent name
        target_agent = None
        request_parts = agent_name.lower().replace('_', ' ').split()
        for name, agent in agents.items():
            agent_parts = name.lower().replace('_', ' ').split()
            # Check if the first word matches (e.g., "hackernews" matches "HackerNews Researcher")
            if request_parts[0] in agent_parts[0]:
                target_agent = agent
                break
        
        if not target_agent:
            # If still not found, show available agents
            available_agents = [f"{agent.name} (key: {name})" for name, agent in agents.items()]
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{agent_name}' not found. Available agents: {available_agents}"
            )

    user_input = request.message
    response = target_agent.run(user_input, stream=False)
    return {"response": response.content}