from typing import Any
from graph.state import AgentState
from graph.tool import load_pw_cli_steps_library, run_cli, read_snapshot_file
from llm import graqllm
from langchain_core.prompts import ChatPromptTemplate

try:
    llm = graqllm.get_llm_model()
except Exception as e:
    print(f"LLM initialization failed: {e}")
    llm = None


def _extract_ai_content(resp: Any) -> str:
    """Return the textual content from various AI response shapes.

    Supports dicts with 'messages' or 'content', objects with `.content` or `.messages`,
    and falls back to str(resp).
    """
    if resp is None:
        return ""
    if isinstance(resp, dict):
        msgs = resp.get("messages") or resp.get("choices")
        if isinstance(msgs, list) and msgs:
            last = msgs[-1]
            if isinstance(last, dict):
                return last.get("content") or last.get("message") or str(last)
        return resp.get("content") or resp.get("message") or str(resp)
    # object-like responses
    if hasattr(resp, "content"):
        return getattr(resp, "content") or ""
    if hasattr(resp, "messages"):
        msgs = getattr(resp, "messages")
        if isinstance(msgs, list) and msgs:
            last = msgs[-1]
            if hasattr(last, "content"):
                return last.content or ""
            if isinstance(last, dict):
                return last.get("content") or str(last)
    return str(resp)

def check_and_retrieve_existing_step(state: AgentState) -> dict:
    """Loads library and resets retry count for the new step."""
    
    step_text = state["current_step"]
    
    # Prompt
    system = """You a playwright-cli automation assistant. Your task is to search a library of playwright-cli commands for a command that matches the given step description. 
    If a matching command is found, return it; otherwise, return 'NOT_FOUND'."""
    search_step_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        (
            "human",
            "Here is the current step: \n\n {step_text} \n Search the {LIBRARY_FILE}.",
        ),
    ])

    cli_step = search_step_prompt | llm | StrOutputParser()
    step_searcher.invoke({"current_step": step_text})
    
    return {
        "cli_step_to_execute": {step_text: cli_step}
    } 

def execute_known_pw_cli_steps(state: AgentState) -> dict:
    """Executes a command that is already in the library (playwright-cli steps)."""
    step_text = state["scenario"][state["current_index"]]
    LIBRARY_FILE = state.get("library_file", "pw-cli-steps-library/playwright-cli-steps-library.txt")
    if llm is None:
        return {"status": "failed", "error_message": "LLM not configured (GROQ_API_KEY missing)"}

    ai_message = llm.invoke(f"Based on the {step_text}, search the {LIBRARY_FILE} and search the command for it")
    command_text = _extract_ai_content(ai_message)

    if command_text:
        success = run_cli(command_text)
    else:
        return {"status": "failed", "error_message": f"command not found in library file: {step_text}"}  # type: ignore

    if success:
        return {"current_index": state["current_index"] + 1} # type: ignore
    else:
        return {"status": "failed", "error_message": f"Known step failed: {step_text}"} # type: ignore

def discover_locator(state: AgentState) -> dict:
    """Takes a snapshot and uses an LLM to generate the command."""
    step_text = state["scenario"][state["current_index"]]
    
    # 1. Take Snapshot
    print("Step not in library. Taking snapshot...")
    snapshot_result = run_cli("npx playwright-cli snapshot")
    # If the CLI returned a file path (string), use it; otherwise derive a page key from the step text
    if isinstance(snapshot_result, str):
        snapshot_file_key = snapshot_result
    else:
        # fall back to a simplified page name derived from the step text
        snapshot_file_key = step_text.split()[0] if step_text else ""

    # 2. Get Snapshot Data (Assuming the CLI saves it to a known file or outputs to stdout)
    snapshot_data = read_snapshot_file(snapshot_file_key)

    # 3. LLM Integration
    LIBRARY_FILE = state.get("library_file", "pw-cli-steps-library/playwright-cli-steps-library.txt")
    if llm is None:
        return {"status": "failed", "error_message": "LLM not configured (GROQ_API_KEY missing)"}

    print(f"Asking LLM for locator for step: '{step_text}'")
    generated = llm.invoke(f"Based on snapshot data as {snapshot_data}, write playwright-cli command for: {step_text}")
    generated_command = _extract_ai_content(generated)
    
    # Mocking the LLM response for demonstration
    # generated_command = f'npx playwright-cli type "mock_locator" "mock_value"'
    
    return {"current_command": generated_command} # type: ignore

def execute_new(state: AgentState) -> dict:
    """Executes the newly generated command."""
    command = state["current_command"]
    success = run_cli(command) # type: ignore
    
    if success:
        return {"status": "new_success"} # type: ignore
    else:
        return {"retry_count": state["retry_count"] + 1, "status": "new_failed"} # type: ignore

def save_to_library(state: AgentState) -> dict:
    """Saves the successfully executed new command to the library text file."""
    step_text = state["scenario"][state["current_index"]]
    command = state["current_command"]
    
    LIBRARY_FILE= state.get("library_file", "pw-cli-steps-library/playwright-cli-steps-library.txt")
    with open(LIBRARY_FILE, 'a') as f:
        f.write(f'"{step_text}", "{command}"\n')
    
    print(f"Saved new step to library: {step_text}")
    return {"current_index": state["current_index"] + 1, "status": "running"} # type: ignore

def handle_failure(state: AgentState) -> dict:
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
        return "execute_known_pw_cli_steps"
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