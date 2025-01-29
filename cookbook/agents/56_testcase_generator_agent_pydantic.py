import os
import asyncio
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat
from phi.tools import tool

# ======================== Pydantic Models ========================

class FilePath(BaseModel):
    file_path: str = Field(..., description="Path to the Next.js component file.")

class JestTestCase(BaseModel):
    app_path: str = Field(..., description="Root directory of the Next.js application.")
    file_path: str = Field(..., description="Path to the component file for which Jest test cases are generated.")
    test_code: str = Field(..., description="Jest test code formatted within triple double quotes.")

class NextJsFilePaths(BaseModel):
    components: List[str] = Field(..., description="List of .tsx file paths in the Next.js app.")

# ======================== Tools ========================

@tool
def get_file_code(file_path) -> str:
    """
    Use this function to read the contents of each Next.js component file.

    Args:
        file_path (str): Path to the component file

    Returns:
        str: The contents of the component file
    """
    print("[DEBUG] This is the file path I am reading", file_path)
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return ""

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        print(f"[DEBUG] Read file: {file_path}, Content length: {len(content)}")
        return content if content else "[ERROR] File is empty."


@tool
def store_jest_test_case_of_file(test_data: JestTestCase):
    """
    Use this function to store the generated test data in a '__tests__' folder structure
    mirroring the original file path.

    By default, the test file will have the same name + '.test'
    and will be placed under app_path/__tests__/...

    Args:
        app_path (str): Path to the root directory of the Next.js app
        file_path (str): The original file (page or component) path
        test_code (str): The Jest test code to be saved
    """
    app_path = test_data.app_path
    file_path = test_data.file_path
    test_code = test_data.test_code
    print(f"[DEBUG] Storing test for {file_path} in {app_path} and code is {test_code}")

    if not test_code.strip():
        print(f"[ERROR] No test code generated for {file_path}. Skipping storage.")
        return

    relative_path = os.path.relpath(file_path, app_path)
    test_file_path = os.path.join(app_path, "__tests__", relative_path)

    os.makedirs(os.path.dirname(test_file_path), exist_ok=True)

    with open(test_file_path + ".test.js", "w", encoding="utf-8") as f:
        f.write(test_code)
        print(f"[DEBUG] Test file stored at: {test_file_path}.test.js")


def get_nextjs_file_paths(app_path: str) -> NextJsFilePaths:
    """
    Use this function to find all .tsx files in the Next.js app (treated as "components").

    Args:
        app_path (str): Path to the root directory of the Next.js app

    Returns:
        dict: {
            "components": [<list of other .tsx file paths>]
        }
    """
    components = []
    for root, _, files in os.walk(app_path):
        if "node_modules" in root:
            continue
        for file in files:
            if file.endswith(".tsx"):
                components.append(os.path.join(root, file))

    print(f"[DEBUG] Found {len(components)} Next.js component files.")
    return NextJsFilePaths(components=components)

# ======================== Agents ========================

reader_agent = Agent(
    name="ReaderAgent",
    model=OpenAIChat(model_name="gpt-4o"),
    description="Reads the content of Next.js component file.",
    tools=[get_file_code],
    instructions=["Use the `get_file_code` tool to read the code by passing the file_path to the tool as parameter"],
    # debug_mode=True,
)

writer_agent = Agent(
    name="WriterAgent",
    model=OpenAIChat(model_name="gpt-4o"),
    description="Generates Jest test cases for Next.js component code that is given as input",
    instructions=[
        "Given the content of a Next.js component, generate Jest test cases.",
        "Ensure test coverage includes both success and failure cases.",
        "Return the Jest test cases as a formatted code block enclosed correctly within triple double quotes (\"\"\").",
        "Inside the triple double quotes, use triple backticks (` ```js ... ``` `) to format the Jest test cases as a JavaScript code block.",
    ],
    # debug_mode=True,
    expected_output="Return an object with app_path (str): Path to the root directory of the Next.js app, file_path (str): The original file (page or component) path, test_code (str): The Jest test code to be saved"
)

store_agent = Agent(
    name="StoreAgent",
    model=OpenAIChat(model_name="gpt-4o"),
    description="Stores Jest test cases in the correct file location.",
    tools=[store_jest_test_case_of_file],
    instructions=["Use the `store_jest_test_case_of_file` tool to save test cases in the correct loaction"],
    # debug_mode=True,
)

orchestrator_agent = Agent(
    name="OrchestratorAgent",
    description="Coordinates the test generation workflow.",
    team=[reader_agent, writer_agent, store_agent],
    instructions=[
        "For the given file path, perform the following steps in order:",
        "1. Use `ReaderAgent` to read the file content by using the file_path as the parameter into the tool",
        "2. Use `WriterAgent` to generate test cases by taking the code that we get for a particular file path",
        "3. Use `StoreAgent` to store the respose of the writer agent in the correct location.",
    ],
    # debug_mode=True,
)

# ======================== Runner Functions ========================

def generate_test_cases_for_app(app_path: str):
    """
    Iterates through all Next.js component files and generates Jest test cases.
    """
    file_paths = get_nextjs_file_paths(app_path)
    print("filepaths: ", file_paths)

    for file_path in file_paths.components:
        print(f"\n[PROCESSING] {file_path}")

        response = orchestrator_agent.print_response(file_path)
            # f"This is the filepath: {file_path}. "
            # f"1. Read this file using ReaderAgent, 2. Generate Jest test cases for the content using WriterAgent, "
            # f"3. Store the test cases using StoreAgent. App root is {app_path}."

        print(f"[DEBUG] Processing complete for {file_path}\n")


async def generate_test_cases_for_app_async(app_path: str):
    """
    Asynchronously processes all Next.js component files to generate Jest test cases.
    """
    file_paths = get_nextjs_file_paths(app_path)
    tasks = []
    for file_path in file_paths.components:
        print(f"\n[PROCESSING] {file_path}")

        task = asyncio.create_task(
            orchestrator_agent.arun(
                f"Process the file: {file_path}. "
                f"1. Read using ReaderAgent, 2. Generate Jest test cases using WriterAgent, "
                f"3. Store the test cases using StoreAgent. App root is {app_path}."
            )
        )
        tasks.append(task)

    await asyncio.gather(*tasks)
    print("[DEBUG] All async tasks completed.")

# ======================== Main Execution ========================

if __name__ == "__main__":
    app_root = "/Users/akarshhegde/Documents/Forgd/PESU/4gd-pesu-eval-ui"

    # Run synchronously
    generate_test_cases_for_app(app_root)

    # Run asynchronously
    # asyncio.run(generate_test_cases_for_app_async(app_root))
