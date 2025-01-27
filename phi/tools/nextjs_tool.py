import os
from pathlib import Path
from phi.tools import Toolkit

class NextJsProjectTools(Toolkit):
    def __init__(self, fetch_components: bool = True, fetch_pages: bool = True, enable_all: bool = False):
        super().__init__(name="nextjs_project_tools")

        if fetch_components or enable_all:
            self.register(self.get_nextjs_component_code)
        if fetch_pages or enable_all:
            self.register(self.get_nextjs_page_code)


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
