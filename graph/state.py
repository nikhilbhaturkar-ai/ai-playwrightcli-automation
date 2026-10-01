from typing import TypedDict, List, Dict, Optional
class AgentState(TypedDict):
    scenario: List[str]
    current_index: int
    library: Dict[str, str]
    retry_count: int
    status: str
    current_command: Optional[str]
    error_message: Optional[str]
    current_step: Optional[str]  # Added to hold the current step text