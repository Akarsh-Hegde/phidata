from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo

assistant = Assistant(tools=[DuckDuckGo()], show_tool_calls=True)
assistant.print_response("List 10 latest news in US Stock.")
