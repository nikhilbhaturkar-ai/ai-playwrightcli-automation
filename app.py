import os
import subprocess
from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, START, END

# --- 1. STATE DEFINITION ---
class AgentState(TypedDict):
    scenario: List[str]
    current_index: int
    library: Dict[str, str]
    retry_count: int
    status: str
    current_command: Optional[str]
    error_message: Optional[str]

LIBRARY_FILE = "playwright-cli-steps-library.txt"

# --- 2. HELPER FUNCTIONS ---
def load_library(filepath: str) -> Dict[str, str]:
    """Reads the text file and parses it into a dictionary."""
    lib = {}
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                # Expecting format: "navigate to google", "npx playwright-cli goto http://google.co.in"
                parts = line.split('","')
                if len(parts) == 2:
                    key = parts[0].strip(' "\n')
                    val = parts[1].strip(' "\n')
                    lib[key] = val
    return lib

def run_cli(command: str) -> bool:
    """Executes a shell command and returns True if successful."""
    print(f"Executing: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            print(f"Command Failed. Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"Execution Exception: {e}")
        return False

# --- 3. GRAPH NODES ---
def setup_step(state: AgentState) -> AgentState:
    """Loads library and resets retry count for the new step."""
    return {
        "library": load_library(LIBRARY_FILE),
        "retry_count": 0,
        "current_command": None,
        "status": "running"
    } # type: ignore

def execute_known(state: AgentState) -> AgentState:
    """Executes a command that is already in the library."""
    step_text = state["scenario"][state["current_index"]]
    command = state["library"][step_text]
    
    success = run_cli(command)
    
    if success:
        return {"current_index": state["current_index"] + 1} # type: ignore
    else:
        return {"status": "failed", "error_message": f"Known step failed: {step_text}"} # type: ignore

def discover_locator(state: AgentState) -> AgentState:
    """Takes a snapshot and uses an LLM to generate the command."""
    step_text = state["scenario"][state["current_index"]]
    
    # 1. Take Snapshot
    print("Step not in library. Taking snapshot...")
    run_cli("npx playwright-cli snapshot")
    
    # 2. Get Snapshot Data (Assuming the CLI saves it to a known file or outputs to stdout)
    # snapshot_data = read_snapshot_file() 
    
    # 3. LLM Integration (Placeholder: Replace with actual LangChain LLM call)
    print(f"Asking LLM for locator for step: '{step_text}'")
    # generated_command = llm.invoke(f"Based on snapshot, write playwright-cli command for: {step_text}")
    
    # Mocking the LLM response for demonstration
    generated_command = f'npx playwright-cli type "mock_locator" "mock_value"'
    
    return {"current_command": generated_command} # type: ignore

def execute_new(state: AgentState) -> AgentState:
    """Executes the newly generated command."""
    command = state["current_command"]
    success = run_cli(command) # type: ignore
    
    if success:
        return {"status": "new_success"} # type: ignore
    else:
        return {"retry_count": state["retry_count"] + 1, "status": "new_failed"} # type: ignore

def save_to_library(state: AgentState) -> AgentState:
    """Saves the successfully executed new command to the library text file."""
    step_text = state["scenario"][state["current_index"]]
    command = state["current_command"]
    
    with open(LIBRARY_FILE, 'a') as f:
        f.write(f'"{step_text}", "{command}"\n')
    
    print(f"Saved new step to library: {step_text}")
    return {"current_index": state["current_index"] + 1, "status": "running"} # type: ignore

def handle_failure(state: AgentState) -> AgentState:
    """Captures a screenshot on final failure and stops execution."""
    print("Max retries reached or critical failure. Capturing error screenshot...")
    run_cli("npx playwright-cli screenshot error_screenshot.png")
    return {"status": "terminated"} # type: ignore

# --- 4. ROUTING LOGIC (CONDITIONAL EDGES) ---
def route_after_setup(state: AgentState) -> str:
    if state["current_index"] >= len(state["scenario"]):
        return "end_scenario"
    
    step_text = state["scenario"][state["current_index"]]
    if step_text in state["library"]:
        return "execute_known"
    return "discover_locator"

def route_after_known(state: AgentState) -> str:
    if state.get("status") == "failed":
        return "handle_failure"
    return "setup_step"

def route_after_new(state: AgentState) -> str:
    if state.get("status") == "new_success":
        return "save_to_library"
    
    # If failed, check retry count (max 2 retries means 1st try + 2 retries = 3 attempts total)
    if state["retry_count"] <= 2:
        print(f"Retrying... Attempt {state['retry_count']}")
        return "discover_locator"
    
    return "handle_failure"


# --- 5. BUILD THE GRAPH ---
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("setup_step", setup_step)
workflow.add_node("execute_known", execute_known)
workflow.add_node("discover_locator", discover_locator)
workflow.add_node("execute_new", execute_new)
workflow.add_node("save_to_library", save_to_library)
workflow.add_node("handle_failure", handle_failure)

# Add Edges
workflow.add_edge(START, "setup_step")

workflow.add_conditional_edges(
    "setup_step",
    route_after_setup,
    {"execute_known": "execute_known", "discover_locator": "discover_locator", "end_scenario": END}
)

workflow.add_conditional_edges(
    "execute_known",
    route_after_known,
    {"setup_step": "setup_step", "handle_failure": "handle_failure"}
)

workflow.add_edge("discover_locator", "execute_new")

workflow.add_conditional_edges(
    "execute_new",
    route_after_new,
    {"save_to_library": "save_to_library", "discover_locator": "discover_locator", "handle_failure": "handle_failure"}
)

workflow.add_edge("save_to_library", "setup_step")
workflow.add_edge("handle_failure", END)

# Compile Graph
app = workflow.compile()

# --- 6. EXECUTION SCRIPT ---
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
    } # type: ignore

    print("--- Starting Automation Scenario ---")
    app.invoke(initial_state) # type: ignore
    print("--- Scenario Execution Finished ---")