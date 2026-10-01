from langgraph.graph import StateGraph, START, END
from graph.state import AgentState
from graph.node import check_and_retrieve_existing_step, route_after_known, route_after_new, route_after_setup, setup_step, execute_know_pw_cli_steps, discover_locator, execute_new, save_to_library, handle_failure
from graph.tool import execute_known_pw_cli_steps, run_cli

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("check_and_retrieve_existing_step", check_and_retrieve_existing_step)
workflow.add_node("execute_known_pw_cli_steps", execute_known_pw_cli_steps)
workflow.add_node("discover_locator", discover_locator)
workflow.add_node("execute_new", execute_new)
workflow.add_node("save_to_library", save_to_library)
workflow.add_node("handle_failure", handle_failure)

# Add Edges
workflow.add_edge(START, "check_and_retrieve_existing_step")

workflow.add_conditional_edges(
    "setup_step",
    route_after_setup,
    {"execute_known_pw_cli_steps": "execute_known_pw_cli_steps", "discover_locator": "discover_locator", "end_scenario": END}
)

workflow.add_conditional_edges(
    "execute_know_pw_cli_steps",
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