import os
from typing import List

from phi.agent.agent import Agent
from phi.model.openai import OpenAIChat
from phi.workflow.workflow import Workflow
from pydantic import BaseModel, Field

###################################################################
# 1) Define pydantic models for the data we want agents to exchange
###################################################################

class NextJsFilePaths(BaseModel):
    """Represents the list of pages and components in a Next.js app."""
    pages: List[str] = Field(..., description="List of all page.tsx file paths")
    components: List[str] = Field(..., description="List of all other .tsx file paths")

class FileCode(BaseModel):
    """Represents the code content of a Next.js file."""
    code: str = Field(..., description="The raw code of the file")

class TestCode(BaseModel):
    """Represents the generated Jest test code for a file."""
    test_code: str = Field(..., description="The Jest test code for the given file")

###################################################################
# 2) Define the "tools" as Python functions
#    They must be orchestrated by Agents inside the Workflow.
###################################################################

def get_nextjs_file_paths(app_path: str) -> NextJsFilePaths:
    """
    Recursively find all .tsx files in the Next.js app, separating out 'page.tsx'
    from the rest (treated as components).
    """
    pages = []
    components = []
    for root, dirs, files in os.walk(app_path):
        # Skip node_modules or any other folders to exclude
        if "node_modules" in root:
            continue

        for file in files:
            if file.endswith(".tsx"):
                full_path = os.path.join(root, file)
                if file == "page.tsx":
                    pages.append(full_path)
                else:
                    components.append(full_path)

    print(f"Found {len(pages)} page files and {len(components)} component files under {app_path}.")
    return NextJsFilePaths(pages=pages, components=components)


def get_file_code(file_path: str) -> FileCode:
    """
    Read the contents of a Next.js .tsx file and return it.
    """
    with open(file_path, "r") as f:
        print(f"Reading file: {file_path}")
        return FileCode(code=f.read())


def store_jest_test_case_of_file(app_path: str, file_path: str, test_code: str) -> str:
    """
    Store the generated Jest test code in a `__tests__` folder structure
    mirroring the original file path.
    """
    relative_path = os.path.relpath(file_path, app_path)
    test_file_path = os.path.join(app_path, "__tests__", relative_path)
    os.makedirs(os.path.dirname(test_file_path), exist_ok=True)

    final_test_path = test_file_path + ".test.js"
    print(f"Writing test file: {final_test_path}")
    with open(final_test_path, "w") as f:
        f.write(test_code)

    return f"Test file stored: {final_test_path}"

###################################################################
# 3) Build a Workflow with Agents—each has exactly ONE tool.
#    They communicate with each other by passing typed data.
###################################################################

class TestCaseWorkflow(Workflow):
    """
    Multi-agent workflow to:
      1. Scan the Next.js app to find .tsx files (ScanAgent).
      2. For each file, read its code (ReadAgent).
      3. Generate a Jest test suite with at least 50 test cases (GenerateTestAgent).
      4. Store the tests in a mirrored __tests__ folder (StoreAgent).
    """

    description: str = "Generate and store Jest test cases for all .tsx files in a Next.js app."

    # --- Agent 1: ScanAgent (one tool: get_nextjs_file_paths) ---
    scan_agent: Agent = Agent(
        name="ScanAgent",
        model=OpenAIChat(model_name="gpt-3.5-turbo"),  # or 'gpt-4'
        instructions=[
            "You are the ScanAgent. Your job: Given the path to a Next.js application, "
            "call the 'get_nextjs_file_paths' tool to obtain all page and component .tsx files. "
            "Return the result as NextJsFilePaths."
        ],
        tools=[get_nextjs_file_paths],  # exactly one tool
        response_model=NextJsFilePaths,
    )

    # --- Agent 2: ReadAgent (one tool: get_file_code) ---
    read_agent: Agent = Agent(
        name="ReadAgent",
        model=OpenAIChat(model_name="gpt-3.5-turbo"),
        instructions=[
            "You are the ReadAgent. Given a single .tsx file path, call the 'get_file_code' tool "
            "to read the file and return its contents as FileCode."
        ],
        tools=[get_file_code],  # exactly one tool
        response_model=FileCode,
    )

    # --- Agent 3: GenerateTestAgent (no external tool calls—just generate the test code) ---
    generate_test_agent: Agent = Agent(
        name="GenerateTestAgent",
        model=OpenAIChat(model_name="gpt-4"),
        instructions=[
            "You are the GenerateTestAgent, a seasoned Next.js/Jest testing pro. "
            "Given the raw code of a .tsx file, produce a Jest test suite with at least 50 test cases. "
            "Focus on meaningful coverage, use @testing-library/react if appropriate, and thoroughly test major logic paths. "
            "Return your output as a single string in the TestCode model's 'test_code' field.",
            "Your output must be valid JavaScript or TypeScript Jest tests. Please do not wrap it in triple backticks."
        ],
        tools=[],  # no tools here—pure generation
        response_model=TestCode,
    )

    # --- Agent 4: StoreAgent (one tool: store_jest_test_case_of_file) ---
    store_agent: Agent = Agent(
        name="StoreAgent",
        model=OpenAIChat(model_name="gpt-3.5-turbo"),
        instructions=[
            "You are the StoreAgent. Given the Next.js app path, the file path, and the generated test code, "
            "call the 'store_jest_test_case_of_file' tool to write the test code. Return a summary message."
        ],
        tools=[store_jest_test_case_of_file],  # exactly one tool
        response_model=str,  # We'll just store a success message or final path
    )

    def run(self, app_path: str) -> None:
        """
        Orchestrates the 4 agents to:
          1. Scan for .tsx files
          2. For each .tsx file, read the code
          3. Generate test code
          4. Store the generated test code
        """
        # Step 1: Scan
        scan_response = self.scan_agent.run(
            f"Scan the Next.js app at path: {app_path}"
        )
        if not scan_response or not isinstance(scan_response.content, NextJsFilePaths):
            print("Failed to retrieve Next.js file paths.")
            return

        nextjs_file_paths: NextJsFilePaths = scan_response.content
        all_paths = nextjs_file_paths.pages + nextjs_file_paths.components
        print(f"Processing a total of {len(all_paths)} .tsx files...")

        # Step 2..4: For each file, read -> generate -> store
        for file_path in all_paths:
            print(f"\n=== Processing file: {file_path} ===")

            # 2) Read the file
            read_response = self.read_agent.run(
                f"Read the file at path: {file_path}"
            )
            if not read_response or not isinstance(read_response.content, FileCode):
                print(f"Failed to read file: {file_path}")
                continue

            file_code: FileCode = read_response.content

            # 3) Generate test code
            generate_response = self.generate_test_agent.run(
                f"Generate 50 or more Jest tests for the following code:\n{file_code.code}"
            )
            if not generate_response or not isinstance(generate_response.content, TestCode):
                print(f"Failed to generate test code for file: {file_path}")
                continue

            test_code: TestCode = generate_response.content

            # 4) Store the test code
            store_response = self.store_agent.run(
                f"Store test code for file {file_path} in app path {app_path}. Test code is:\n{test_code.test_code}"
            )
            if not store_response:
                print(f"Failed to store test code for file: {file_path}")
            else:
                print(store_response.content)

        print("\nAll done generating and storing tests!")

###################################################################
# 4) Example usage (if running as a script)
###################################################################

if __name__ == "__main__":
    app_path = "/Users/akarshhegde/Documents/Forgd/PESU/4gd-pesu-eval-ui"
    workflow = TestCaseWorkflow(session_id="test-generation")
    workflow.run(app_path)