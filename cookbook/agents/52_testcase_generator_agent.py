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


def generate_test_cases_for_app(app_path: str):
    """
    1. Calls get_nextjs_file_paths(app_path) to get a list of page files and component files.
    2. Loops over all .tsx files found (both pages and components).
    3. For each file, calls the agent with instructions to:
       - Use the get_file_code(file_path) tool to read the code
       - Generate a Jest test case for the file
       - Store the generated Jest test using store_jest_test_case(app_path, file_path, test_code)
    """
    # First, retrieve all .tsx file paths in the given Next.js app
    file_paths_dict = get_nextjs_file_paths(app_path)
    pages = file_paths_dict["pages"]
    components = file_paths_dict["components"]

    # Combine both pages and components
    # all_file_paths = pages + components
    all_file_paths = components
    print(f"Found {len(all_file_paths)} .tsx files in total.")
    # Go through each .tsx file and generate+store tests
    for file_path in all_file_paths:
        print(f"Processing file: {file_path}")
        
        # Instruct the agent on what to do:
        #  - Read the code with get_file_code(file_path)
        #  - Generate a Jest test code
        #  - Store that test code with store_jest_test_case(app_path, file_path, test_code)
        
        create_jest_test_agent = Agent(
        name="JestTestCaseAgent",
        model=OpenAIChat(model_name="gpt-4o"),
        description=(
            "You are a highly skilled JavaScript/TypeScript developer with deep expertise in Next.js and Jest. "
            "You are inside a for loop to generate Jest test cases for Next.js components. The user will provide Next.js component path,"
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
        ],
        # Optional: turn on reasoning if you want step-by-step chain-of-thought logs
        # reasoning=True,
        tools=[
            get_file_code,
            store_jest_test_case_of_file,
            # ... any other tools, if needed
        ],
        show_tool_calls=True,
        # stream=True,
        debug_mode=True,
        # Optional: read from or write to memory, store sessions, etc.
        # memory: AgentMemory = AgentMemory()
        # # add_history_to_messages=true adds the chat history to the messages sent to the Model.
        # add_history_to_messages: True
        # # Number of historical responses to add to the messages.
        # num_history_responses: int = 3
        )
        
        create_jest_test_agent.print_response(f"Generate minimum 50 unit test cases for the code at path {file_path} by calling the tool to get the code and store the test cases in the right location using the store tool")  # Print the response to the user
    
    
if __name__ == "__main__":
    app_path = "/Users/akarshhegde/Documents/Forgd/PESU/4gd-pesu-eval-ui"
    generate_test_cases_for_app(app_path)