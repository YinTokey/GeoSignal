from typing import TypedDict, Optional, List
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # Base inputs from Telegram
    chat_id: int
    user_message: str
    
    # Internal message history for the orchestrator (if needed)
    messages: List[BaseMessage]
    
    # News Agent outputs
    event_type: Optional[str]
    severity: Optional[int]
    headline: Optional[str]
    affected_assets: Optional[str]
    is_duplicate: Optional[bool]
    
    # Market Agent outputs
    market_snapshot: Optional[str]
    
    # WebSearch Agent outputs
    historical_precedents: Optional[str]
    recovery_timeline: Optional[str]
    
    # Final Result
    final_response: Optional[str]
