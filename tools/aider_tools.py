import os
from typing import Dict, List, Optional

# Set environment variables for aider if not already set, e.g., AIDER_MODEL
# os.environ['AIDER_MODEL'] = os.getenv('GEMINI_MODEL_NAME', 'gemini-1.5-flash') # Example

def add_agent_feature(task_description: str, files_to_edit: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Triggers aider to add or modify features by writing a task to a trigger file.
    This function creates/overwrites 'aider-trigger.py' in the project's root directory.
    The content of this file will be the 'task_description' prefixed with "#AI! ".
    Aider should be running in watch mode (e.g., `aider --watch aider-trigger.py`)
    to detect changes to this file and act upon the task.

    Args:
        task_description (str): The detailed description of the feature or change to implement.
        files_to_edit (Optional[List[str]]): A list of file paths. In this version,
            this list is not directly embedded in the 'aider-trigger.py' file.
            The task_description itself should guide aider regarding which files to edit.
            Aider (in watch mode) should be aware of the relevant files through its
            own context or the description.

    Returns:
        Dict[str, str]: A dictionary containing 'status' ("success" or "error")
                        and 'message' (a descriptive message about the operation).
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    trigger_file_path = os.path.join(project_root, "aider-trigger.py")
    content = f"#AI! {task_description}"

    try:
        with open(trigger_file_path, 'w') as f:
            f.write(content)
        return {"status": "success", "message": f"Task successfully written to {trigger_file_path}. Aider (in watch mode) should pick it up."}
    except IOError as e:
        return {"status": "error", "message": f"Error writing to {trigger_file_path}: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

if __name__ == '__main__':
    # Example usage (for testing locally)
    # Ensure aider is running in watch mode in your project's root directory, for example:
    # aider --watch aider-trigger.py

    print("Testing add_agent_feature by writing to aider-trigger.py...")

    # Test 1: A simple task
    task1 = "Create a new Python file named 'example_module.py' in the 'tools' directory. Add a function called 'greet' that takes a name as an argument and returns 'Hello, {name}!'"
    result1 = add_agent_feature(task_description=task1)
    print(f"\nTest 1: Simple task")
    print(f"Status: {result1['status']}")
    print(f"Message: {result1['message']}")
    if result1['status'] == 'success':
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        trigger_file_path = os.path.join(project_root, "aider-trigger.py")
        print(f"Please check the content of '{trigger_file_path}'.")
        print("Ensure aider is running in watch mode to process this task.")

    # Test 2: A task that might involve existing files (aider should handle context)
    # Assuming you have a file `dummy_test_file.py` in the project root for this test.
    # You might need to create it manually or adjust the task.
    dummy_file_for_test = os.path.join(os.path.dirname(__file__), '..', 'dummy_test_file.py')
    if not os.path.exists(dummy_file_for_test):
        with open(dummy_file_for_test, 'w') as f:
            f.write("# This is a dummy file for aider testing.\n")
            f.write("def existing_function():\n")
            f.write("    pass\n")
        print(f"\nCreated '{dummy_file_for_test}' for Test 2.")


    task2 = "In dummy_test_file.py, add a print statement 'Task 2 processed' inside the existing_function."
    result2 = add_agent_feature(task_description=task2, files_to_edit=[dummy_file_for_test]) # files_to_edit is for context here
    print(f"\nTest 2: Task involving an existing file")
    print(f"Status: {result2['status']}")
    print(f"Message: {result2['message']}")
    if result2['status'] == 'success':
        print(f"The task for 'dummy_test_file.py' was written to the trigger file.")
        print("Aider (in watch mode) should attempt to modify it based on the description.")

    print(f"\nTo run these tests effectively:")
    print(f"1. Open a terminal in the project root ('{os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))}').")
    print(f"2. Start aider in watch mode: aider --watch aider-trigger.py")
    print(f"3. Run this script: python {os.path.join('tools', 'aider_tools.py')}")
    print(f"4. Observe aider's output in its terminal and check for file changes.")
