from phi.assistant import Assistant
from phi.llm.together import Together

assistant = Assistant(
    llm=Together(),
    description="You help people with their health and fitness goals.",
    debug_mode=True,
)
assistant.print_response("Share a quick healthy breakfast recipe.", stream=False)
