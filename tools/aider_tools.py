import os
from typing import Dict, List, Optional

# Set environment variables for aider if not already set, e.g., AIDER_MODEL
# os.environ['AIDER_MODEL'] = os.getenv('GEMINI_MODEL_NAME', 'gemini-1.5-flash') # Example

def add_agent_feature(task_description: str, files_to_edit: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Triggers aider to add or modify features by writing a task to a trigger file.
    This function creates/overwrites 'aider-trigger.py' in the project's root directory.
    The content of this file will be the 'task_description'.
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
    formatted_task_description = f"""{task_description}"""
    content = f"{formatted_task_description}"

    try:
        with open(trigger_file_path, 'w') as f:
            f.write(content)
        return {"status": "success", "message": f"Task successfully written to {trigger_file_path}. Aider (in watch mode) should pick it up."}
    except IOError as e:
        return {"status": "error", "message": f"Error writing to {trigger_file_path}: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

