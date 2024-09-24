from typing import List
from pydantic import BaseModel, Field
from rich.pretty import pprint
from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat


class MovieScript(BaseModel):
    setting: str = Field(..., description="Provide a nice setting for a blockbuster movie.")
    ending: str = Field(..., description="Ending of the movie. If not available, provide a happy ending.")
    genre: str = Field(
        ..., description="Genre of the movie. If not available, select action, thriller or romantic comedy."
    )
    name: str = Field(..., description="Give a name to this movie")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(..., description="3 sentence storyline for the movie. Make it exciting!")


class Movies(BaseModel):
    scripts: List[MovieScript] = Field(..., description="Provide 3 movie scripts.")


movie_agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    description="You help people write movie scripts.",
    output_model=Movies,
    # debug_mode=True,
)

run: RunResponse = movie_agent.run("New York")
pprint(run.content)
