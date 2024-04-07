from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.llm.cohere import Cohere

assistant = Assistant(llm=Cohere(model="command-r"), tools=[DuckDuckGo()], show_tool_calls=True)
assistant.print_response("Share 1 story from france and 1 from germany?", markdown=True)
