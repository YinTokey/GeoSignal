from typing import TypedDict, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # Base inputs from Telegram
    chat_id: int
    user_message: str
    
    # Internal message history for the orchestrator (if needed)
    messages: List[BaseMessage]
    
    # Orchestrator routing helper
    intent: Optional[str]
    severity: Optional[float]
    is_duplicate: Optional[bool]
    
    # Agent Outputs stored as structured dictionaries
    news_data: Optional[Dict[str, Any]]
    market_data: Optional[Dict[str, Any]]
    websearch_data: Optional[Dict[str, Any]]
    
    # Final Result
    final_response: Optional[str]
