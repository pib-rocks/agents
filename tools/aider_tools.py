import subprocess
import os
import threading
from typing import Dict, List, Optional

# Set environment variables for aider if not already set, e.g., AIDER_MODEL
# os.environ['AIDER_MODEL'] = os.getenv('GEMINI_MODEL_NAME', 'gemini-1.5-flash') # Example

def add_agent_feature(task_description: str, files_to_edit: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Interactively adds or modifies features in the agent system using the 'aider' CLI tool.
    You provide a task description (e.g., "add a new function to tools/example.py that does X").
    You can also specify a list of files that aider should focus on.
    The tool will run aider with your task. Aider might ask for clarifications or approval.
    The output from aider, including any questions, will be returned.
    If aider asks a question (e.g., "Proceed? (y/n)"), you may need to run this tool again
    with a more specific instruction or use a different tool to apply changes if aider
    cannot proceed automatically.

    Args:
        task_description (str): The detailed description of the feature or change to implement.
        files_to_edit (Optional[List[str]]): A list of file paths that aider should primarily work with.

    Returns:
        Dict[str, str]: A dictionary containing the 'status' ("success", "error", "requires_input")
                        and 'output' (the console output from aider, which might include its questions).
    """
    try:
        aider_cmd = ["aider"]
        if files_to_edit:
            aider_cmd.extend(files_to_edit)
        aider_cmd.append(f"--message \"{task_description}\"") # Pass the task as a message
        # Using --yes to attempt auto-applying, but aider might still ask questions for complex changes.
        # For truly interactive sessions, a more complex setup (e.g., web sockets, long-polling + session state)
        # would be needed, which is beyond a single tool call.
        # This approach tries to get as much done as possible in one go.
        # Consider removing --yes if you want to see all prompts.
        aider_cmd.append("--yes")


        # Ensure API keys are available in the environment for aider
        # Aider typically picks up OPENAI_API_KEY, GEMINI_API_KEY etc. from the environment.
        env = os.environ.copy()

        # We use Popen to manage the process.
        # For a truly interactive CLI tool within a web request/response cycle,
        # this is a simplified approach. Aider might have its own interactive prompts
        # that are hard to manage without a persistent terminal connection.
        # This function will send the initial command and capture the output.
        # If aider prompts for input (e.g., y/n), that prompt will be in the output.

        process = subprocess.Popen(
            " ".join(aider_cmd),
            shell=True, # Using shell=True because aider_cmd is joined into a string. Be cautious with user input.
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE, # Allow sending input if we extend this later
            text=True,
            env=env,
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Run from project root
        )

        # For this version, we are not sending further interactive input.
        # We read the output until aider exits or a timeout (optional, not implemented here for simplicity).
        stdout, stderr = process.communicate() # No input sent after initial command

        output = ""
        if stdout:
            output += f"Aider STDOUT:\n{stdout}\n"
        if stderr:
            output += f"Aider STDERR:\n{stderr}\n"

        if process.returncode != 0:
            # Check if stderr contains typical prompts for user input
            if "Proceed?" in stderr or "Apply this change?" in stderr:
                 return {"status": "requires_input", "output": output or "Aider process ended with an error or requires input."}
            return {"status": "error", "output": output or f"Aider process exited with code {process.returncode}."}

        # If aider ran and exited cleanly (e.g. after applying a change with --yes)
        return {"status": "success", "output": output or "Aider process completed."}

    except FileNotFoundError:
        return {"status": "error", "output": "Error: 'aider' command not found. Please ensure it is installed and in your PATH."}
    except Exception as e:
        return {"status": "error", "output": f"An unexpected error occurred: {str(e)}"}

if __name__ == '__main__':
    # Example usage (for testing locally)
    # Ensure your Gemini API key is set in your environment if aider uses it.
    # For example: export GEMINI_API_KEY="your_key_here"
    # And aider is configured to use gemini, e.g. via --model gemini/gemini-1.5-pro-latest or .aider.conf.yaml

    # Test 1: Ask aider to do something simple (e.g., add a comment to a test file)
    # Create a dummy file for aider to edit if it doesn't exist
    dummy_file = os.path.join(os.path.dirname(__file__), '..', 'dummy_test_file.py')
    if not os.path.exists(dummy_file):
        with open(dummy_file, 'w') as f:
            f.write("# This is a dummy file for aider testing.\n")
            f.write("def hello():\n")
            f.write("    print('hello')\n")


    print("Testing add_agent_feature...")
    # result = add_agent_feature(task_description="Add a print statement inside the hello function in dummy_test_file.py saying 'aider was here'", files_to_edit=[dummy_file])
    # print(f"Status: {result['status']}")
    # print(f"Output:\n{result['output']}")

    # Test 2: A task that might require confirmation if --yes is not used or is insufficient
    # result_complex = add_agent_feature(task_description="Refactor the hello function in dummy_test_file.py to take a name argument and print 'hello, {name}'")
    # print(f"\nStatus (complex): {result_complex['status']}")
    # print(f"Output (complex):\n{result_complex['output']}")

    # To run this test, you would typically execute:
    # python tools/aider_tools.py
    # from the project root, after setting necessary environment variables.
    # And ensure 'aider' is installed and configured.
    print(f"Please run this test manually from the project root: python {os.path.join('tools', 'aider_tools.py')}")
    print("Ensure 'aider' is installed and configured, and any necessary API keys (e.g., GEMINI_API_KEY) are set in your environment.")
    print(f"A dummy file '{dummy_file}' will be created/used for the test.")
    print("Uncomment the test calls in the if __name__ == '__main__': block to run.")
