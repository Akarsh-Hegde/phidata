from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.dalle import Dalle

image_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[Dalle()],
    description="You are an AI agent that can generate images using DALL-E.",
    instructions=[
        "When the user asks you to generate an image, use the DALL-E tool to generate an image.",
        "The DALL-E tool will return an image URL.",
        "Return the image URL in your response in the following format: `![image description](image URL)`",
    ],
    markdown=True,
    debug_mode=True,
)

image_agent.print_response("Generate an image of a white siamese cat")
