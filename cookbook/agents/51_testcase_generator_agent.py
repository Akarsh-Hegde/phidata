from phi.agent.agent import Agent
from phi.model.openai import OpenAIChat
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import os

class NextJsFilePaths(BaseModel):
    pages: List[str] = Field(..., description="List of all page.tsx file paths")
    components: List[str] = Field(..., description="List of all other .tsx file paths")


def get_file_code(file_path: str):
    """
    Use this function to read the contents of each Next.js component file.

    Args:
        file_path (str): Path to the component file

    Returns:
        str: The contents of the component file
    """
    with open(file_path, "r") as f:
        print(f"Reading component file: {file_path}")
        return f.read()
    
# def generate_and_store_test_cases(pages: List, components: List):
    

def store_jest_test_case_of_file(app_path: str, file_path: str, test_code: str):
    """
    Use this function to store the generated Jest test code in a '__tests__' folder structure
    mirroring the original file path.

    By default, the test file will have the same name + '.test'
    and will be placed under app_path/__tests__/...

    Args:
        app_path (str): Path to the root directory of the Next.js app
        original_file_path (str): The original file (page or file) path
        test_code (str): The Jest test code to be saved
    """
    # Calculate the relative path to keep the folder structure
    relative_path = os.path.relpath(file_path, app_path)

    # Build the path under the '__tests__' directory
    test_file_path = os.path.join(app_path, "__tests__", relative_path)

    # Make sure the directory exists
    os.makedirs(os.path.dirname(test_file_path), exist_ok=True)

    # Write the test code to the file
    with open(test_file_path + ".test.js", "w") as f:
        print(f"Writing test file: {test_file_path}.test.js")
        f.write(test_code)


def get_nextjs_file_paths(app_path: str):
    """
    Use this function to recursively find all .tsx files in the Next.js app, separating out 'page.tsx'
    from the rest (treated as "components").

    This approach is useful when your Next.js (App Router) project has a complex
    structure of nested directories, and you just want:
      - A list of 'page.tsx' files
      - A list of all other .tsx files (assumed to be components or other special files)

    Args:
        app_path (str): Path to the root directory of the Next.js app

    Returns:
        dict: {
            "pages": [<list of page.tsx file paths>],
            "components": [<list of other .tsx file paths>]
        }
    """
    pages = []
    components = []

    for root, dirs, files in os.walk(app_path):
        # Skip node_modules or any other folders you want to exclude
        if "node_modules" in root:
            continue

        for file in files:
            if file.endswith(".tsx"):
                full_path = os.path.join(root, file)

                # If it's specifically named 'page.tsx', treat it as a page file
                if file == "page.tsx":
                    pages.append(full_path)
                else:
                    # All other .tsx files go into the "components" list
                    components.append(full_path)
    print(f"Found {len(pages)} page files and {len(components)} component files.")
    return {"pages": pages, "components": components}

def store_jest_test_case(app_path: str, original_file_path: str, test_code: str):
    """
    Use this function to store the generated Jest test code in a '__tests__' folder structure
    mirroring the original file path.

    By default, the test file will have the same name + '.test'
    and will be placed under app_path/__tests__/...

    Args:
        app_path (str): Path to the root directory of the Next.js app
        original_file_path (str): The original file (page or component) path
        test_code (str): The Jest test code to be saved
    """
    # Calculate the relative path to keep the folder structure
    relative_path = os.path.relpath(original_file_path, app_path)

    # Build the path under the '__tests__' directory
    test_file_path = os.path.join(app_path, "__tests__", relative_path)

    # Make sure the directory exists
    os.makedirs(os.path.dirname(test_file_path), exist_ok=True)

    # Replace the extension with '.test.<ext>'
    base, ext = os.path.splitext(test_file_path)
    test_file_path = base + ".test" + ext

    # Write the Jest test code
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_code)

create_jest_test_agent = Agent(
        name="JestTestCaseAgent",
        model=OpenAIChat(model_name="gpt-4o-mini"),
        description=(
            "You are a highly skilled JavaScript/TypeScript developer with deep expertise in Next.js and Jest. "
            "You generate Jest test cases for Next.js applications. The user will provide Next.js component or API code, "
            "and you will provide a Jest test suite."
        ),
        instructions=[
             "**Your goal**: Produce Jest tests that thoroughly cover the provided Next.js functionality.",
            "Make sure to:\n"
            "  - Include meaningful test names.\n"
            "  - Test both success and failure paths if relevant.\n"
            "  - Use @testing-library/react or relevant frameworks if requested.\n"
            "  - Provide helpful comments where necessary.\n"
            "**Output**:\n"
            "  - Return the Jest test file as a code block. "
            "  - For instance, use triple backticks with js or ts syntax.\n"
        # """
        # 1. Call the `get_nextjs_file_paths` tool with the user-provided Next.js root path.
        # 2. You will receive a JSON with { "pages": [...], "components": [...] }.
        # 3. For each file_path in pages:
        #    - Call `get_file_code(file_path)` to read the code
        #    - Generate a Jest test suite for that page
        #    - Call `store_jest_test_case(<app_path>, file_path, <test_code>)` to store the test
        # 4. Repeat for each file_path in components
        # 5. Return a summary message, or simply re-return the {pages, components} to confirm completion.
        # """
        ],
        # Optional: turn on reasoning if you want step-by-step chain-of-thought logs
        tools=[
            # get_nextjs_file_paths,
            get_file_code,
            store_jest_test_case_of_file,
            # ... any other tools, if needed
        ],
        show_tool_calls=True,
        debug_mode=True,
        # Optional: read from or write to memory, store sessions, etc.
    )

# Create the specialized agent instance
# create_jest_test_agent.print_response("Get the file paths of all .tsx files for the app at path `/Users/akarshhegde/Documents/Forgd/PESU/4gd-pesu-eval-ui`. Generate the unit test cases by calling the tool to get the code for each file and store the test cases in the right location using the store tool, repeat it for all the files")  # Print the response to the user
create_jest_test_agent.print_response("Generate the unit test cases for the app at path /Users/akarshhegde/Documents/Forgd/PESU/4gd-pesu-eval-ui/src/app/admin/components/dashboard/setup/resultsComponents/adminListView.tsx by calling `get_file_code` tool to get the code, and then store the test cases in the right location using `store_jest_test_case` tool")  # Print the response to the user


# def run_agents():
#     try:
#         file_path = "/Users/akarshhegde/Documents/Forgd/PESU/4gd-pesu-eval-ui/src/app/admin/components/dashboard/setup/resultsComponents/adminListView.tsx"
#         app_path = "/Users/akarshhegde/Documents/Forgd/PESU/4gd-pesu-eval-ui"

#         # Step 1: Read File Content
#         # display_header("Running ReaderAgent: Fetching Code", panel_title="Step 1: Read Code")
#         with console.status("Fetching code...", spinner="dots"):
#             file_content_response: RunResponse = create_jest_test_agent.run(file_path)
        
#         if not file_content_response or not file_content_response.content.strip():
#             console.print("[bold red]Error: Failed to read the component file.[/bold red]")
#             return
        
#         display_content(file_content_response.content, title="Component Code")

#     except Exception as e:
#         console.print(f"[bold red]Error occurred while running agents: {e}[/bold red]")