from phi.agent import Agent
from phi.tools.nextjs_tool import NextJsProjectTools


agent = Agent(
    tools=[NextJsProjectTools(fetch_components=True, fetch_pages=True)], 
    debug_mode=True, 
    show_tool_calls=True, 
    description="You are an investment analyst that researches stock prices, analyst recommendations, and stock fundamentals.",
    instructions=["Format your response using markdown and use tables to display data where possible."],
)

agent.print_response("Share the NVDA stock price and analyst recommendations", markdown=True)