import json
from phi.llm.ollama import Ollama
from phi.assistant.duckdb import DuckDbAssistant

duckdb_assistant = DuckDbAssistant(
    llm=Ollama(model="openhermes"),
    show_tool_calls=True,
    semantic_model=json.dumps(
        {
            "tables": [
                {
                    "name": "movies",
                    "description": "Contains information about movies from IMDB.",
                    "path": "https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv",
                }
            ]
        }
    ),
    debug_mode=True,
)

duckdb_assistant.print_response("What is the average rating of movies? Show me the SQL.", markdown=True)
