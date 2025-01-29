import os
import asyncio
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat
from phi.tools import tool
import re  # Import regular expressions module
import json  # Import JSON module

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


writer_agent = Agent(
    name="WriterAgent",
    model=OpenAIChat(model_name="gpt-4o"),
    description="Generates Jest test cases for Next.js components given as input.",
    instructions=[
        "Given the content of a Next.js component, generate Jest test cases.",
        "Ensure test coverage includes both success and failure cases.",
        "Return the Jest test cases inside a structured JSON object.",
        "The response should be a valid JSON object, **not** a stringified JSON.",
        "The object should have the following keys:",
        "- `app_path` (str): The root directory of the Next.js app (D:\\ShopLC\\shop-lc-ui).",
        "- `file_path` (str): The full path of the component file being tested.",
        "- `test_code` (str): The Jest test code formatted as a raw JavaScript string.",
        "The `test_code` should be a valid JavaScript test file without surrounding triple backticks or special formatting."
    ],
    response_model=JestTestCase,
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
        content = get_file_code(file_path)

        response = writer_agent.run(content)
        print(f"[DEBUG] Raw response from WriterAgent: {response.content}")

        store_jest_test_case_of_file(response.content)
        print(f"[DEBUG] Test case stored for {file_path}\n")

# ======================== Main Execution ========================

if __name__ == "__main__":
    app_root = r"D:\ShopLC\shop-lc-ui"  

    # Run synchronously
    generate_test_cases_for_app(app_root)

