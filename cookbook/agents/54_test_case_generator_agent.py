import os
from pathlib import Path
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools import tool, FunctionCall

# Hooks for debugging
def pre_hook(fc: FunctionCall):
    print(f"[DEBUG] Pre-hook: {fc.function.name}")
    print(f"[DEBUG] Arguments: {fc.arguments}")

def post_hook(fc: FunctionCall):
    print(f"[DEBUG] Post-hook: {fc.function.name}")
    print(f"[DEBUG] Result: {fc.result}")

# Tool to read the file content
@tool(pre_hook=pre_hook, post_hook=post_hook)
def get_file_code(file_path: str) -> str:
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return ""  # Prevents returning None, which causes API errors

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        print(f"[DEBUG] Read file: {file_path}, Content length: {len(content)}")
        return content if content else "[ERROR] File is empty."

# Tool to store Jest test cases
@tool(pre_hook=pre_hook, post_hook=post_hook)
def store_jest_test_case_of_file(app_path: str, file_path: str, test_code: str):
    if not test_code.strip():
        print(f"[ERROR] No test code generated for {file_path}. Skipping storage.")
        return

    relative_path = os.path.relpath(file_path, app_path)
    test_file_path = os.path.join(app_path, "__tests__", relative_path)

    os.makedirs(os.path.dirname(test_file_path), exist_ok=True)
    
    with open(test_file_path + ".test.js", "w", encoding="utf-8") as f:
        f.write(test_code)
        print(f"[DEBUG] Test file stored at: {test_file_path}.test.js")

# Get file paths for Next.js components
def get_nextjs_file_paths(app_path: str):
    components = []
    for root, _, files in os.walk(app_path):
        if "node_modules" in root:
            continue
        for file in files:
            if file.endswith(".tsx"):
                components.append(os.path.join(root, file))
    print(f"[DEBUG] Found {len(components)} Next.js component files.")
    return {"components": components}

# Agents
reader_agent = Agent(
    name="ReaderAgent",
    model=OpenAIChat(model_name="gpt-4o"),
    description="Reads the content of Next.js component files.",
    tools=[get_file_code],
    instructions=["Use the `get_file_code` tool to read the given file path."],
    debug_mode=True,
)

writer_agent = Agent(
    name="WriterAgent",
    model=OpenAIChat(model_name="gpt-4o"),
    description="Generates Jest test cases for Next.js components.",
    instructions=[
        "Given the content of a Next.js component, generate Jest test cases.",
        "Ensure test coverage includes success and failure cases.",
        "Return the Jest test cases as a formatted code block enclosed in triple quotes (```js).",
    ],
    debug_mode=True,
)

store_agent = Agent(
    name="StoreAgent",
    model=OpenAIChat(model_name="gpt-4o"),
    description="Stores Jest test cases in the correct file location.",
    tools=[store_jest_test_case_of_file],
    instructions=["Use the `store_jest_test_case_of_file` tool to save test cases."],
    debug_mode=True,
)

orchestrator_agent = Agent(
    name="OrchestratorAgent",
    description="Coordinates the test generation workflow.",
    team=[reader_agent, writer_agent, store_agent],
    instructions=[
        "For each file path, perform the following steps:",
        "1. Use `ReaderAgent` to read the file content.",
        "2. If content is valid, use `WriterAgent` to generate test cases.",
        "3. If test cases are valid, use `StoreAgent` to store them in the correct location.",
    ],
    debug_mode=True,
)

# Function to process files
def generate_test_cases_for_app(app_path: str):
    file_paths_dict = get_nextjs_file_paths(app_path)
    components = file_paths_dict["components"]

    for file_path in components:
        print(f"\n[PROCESSING] {file_path}")

        response = orchestrator_agent.print_response(
            f"Process the file: {file_path}. "
            f"1. Read using ReaderAgent, 2. Generate Jest test cases using WriterAgent, "
            f"3. Store the test cases using StoreAgent. App root is {app_path}."
        )

        print(f"[DEBUG] Processing complete for {file_path}\n")

if __name__ == "__main__":
    app_root = "/Users/akarshhegde/Documents/Forgd/PESU/4gd-pesu-eval-ui"
    generate_test_cases_for_app(app_root)