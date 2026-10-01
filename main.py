import os
from graph.workflow import app

LIBRARY_FILE = "pwer-cli-steps-library/playwright-cli-steps-library.txt"

if __name__ == "__main__":
    # Create a dummy library file if it doesn't exist to prevent file errors
    if not os.path.exists(LIBRARY_FILE):
        open(LIBRARY_FILE, 'w').close()

    test_scenario = [
        "navigate to google.co.in",
        "enter username in username textbox",
        "click the login button"
    ]

    initial_state = {
        "scenario": test_scenario,
        "current_index": 0,
        "library": {},
        "retry_count": 0,
        "status": "starting",
        "current_command": None,
        "error_message": None
    } 

    print("--- Starting Automation Scenario ---")
    app.invoke(initial_state)  # type: ignore
    print("--- Scenario Execution Finished ---")
