import uvicorn

from phi.agent import Agent
from phi.llm.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools
from phi.storage.agent.postgres import PgAgentStorage
from phi.playground import Playground

agent = Agent(
    llm=OpenAIChat(model="gpt-4o"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
    storage=PgAgentStorage(table_name="agent_sessions", db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
)
# agent.create_session()
# agent.print_response("What is the stock price of NVDA")

api = Playground(agents=[agent]).api()

if __name__ == "__main__":
    uvicorn.run("serve:api", host="0.0.0.0", port=8000, reload=True)
