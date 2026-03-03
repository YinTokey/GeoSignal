from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field

from agents.state import AgentState

# We will define what the News Agent should return
class NewsOutput(BaseModel):
    event_type: str = Field(description="The type of event (e.g. 'earn_miss', 'geopolitical', 'macro', 'company_scandal')")
    severity: int = Field(description="Integer severity from 1 to 10")
    headline: str = Field(description="A concise 1-sentence headline of the event")
    affected_assets: str = Field(description="Assets or sectors primarily affected by the news")

# -----------------
# Node: Orchestrator
# -----------------
def orchestrator_node(state: AgentState):
    """
    The Orchestrator doesn't call tools itself. Its job is to figure out to launch the News Agent initially.
    In our static graph, the flow automatically goes from Orchestrator -> News,
    so this node essentially just normalizes the input if needed.
    """
    print(f"[Orchestrator] Received user message: {state['user_message']}")
    return state

# -----------------
# Node: News Agent
# -----------------
def news_agent_node(state: AgentState, llm: ChatOpenAI, tools: dict):
    """
    The News Agent calls `search_news` and `check_duplicate`.
    """
    print("[News Agent] Analyzing news for message...")
    search_news_tool = tools.get("search_news")
    check_duplicate_tool = tools.get("check_duplicate")
    
    # Let the LLM use the tools to find out what's going on
    system_prompt = SystemMessage(content='''You are a Financial News Agent. 
    1. Use the search_news tool to find out what the user is talking about.
    2. Then, use the check_duplicate tool to see if the headline has already been processed.
    Return your final understanding.
    ''')
    
    # We bind tools
    agent_llm = llm.bind_tools([search_news_tool, check_duplicate_tool])
    
    # This is a simple 1-step call. For a true ReAct agent, you'd use a sub-graph or create_react_agent.
    # For brevity in this implementation, we will use a small inline tool-calling loop.
    messages = [system_prompt, HumanMessage(content=state['user_message'])]
    
    while True:
        response = agent_llm.invoke(messages)
        messages.append(response)
        
        if not response.tool_calls:
            break
            
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            print(f"[News Agent] Calling {tool_name} with {tool_args}")
            
            if tool_name == "search_news":
                tool_msg = search_news_tool.invoke(tool_args)
            elif tool_name == "check_duplicate":
                tool_msg = check_duplicate_tool.invoke(tool_args)
            else:
                tool_msg = f"Unknown tool: {tool_name}"
                
            messages.append({"role": "tool", "name": tool_name, "content": str(tool_msg), "tool_call_id": tool_call["id"]})

    # Now we extract the structured output from the final text
    extractor_llm = llm.with_structured_output(NewsOutput)
    structured_news = extractor_llm.invoke(
        [SystemMessage(content="Extract the event details from the context."), messages[-1]]
    )
    
    # Heuristic for duplicate (if the LLM determined it was in the text)
    is_dupe = "True" in str(messages) # simplistic check
    
    return {
        "event_type": structured_news.event_type,
        "severity": structured_news.severity,
        "headline": structured_news.headline,
        "affected_assets": structured_news.affected_assets,
        "is_duplicate": is_dupe
    }

# -----------------
# Edge: Route after News
# -----------------
def route_after_news(state: AgentState) -> Literal["market", "log_and_stop"]:
    print(f"[Router] Severity is {state['severity']}, Duplicate: {state.get('is_duplicate')}")
    if getattr(state, 'is_duplicate', False):
        print("[Router] Duplicate detected. Stopping.")
        return "log_and_stop"
        
    severity = state.get("severity", 0)
    if severity >= 5:
         print("[Router] High severity. Proceeding to Market & WebSearch.")
         return "market" # We will route to a parallel node
    else:
         print("[Router] Low severity. Stopping.")
         return "log_and_stop"

# -----------------
# Node: Market Agent
# -----------------
def market_agent_node(state: AgentState, llm: ChatOpenAI, tools: dict):
    print("[Market Agent] Fetching market snapshot...")
    market_tool = tools.get("get_market_snapshot")
    
    assets = state.get("affected_assets", "general market")
    result = market_tool.invoke({"asset_or_market": assets})
    
    # Synthesize the raw output into a clean string
    response = llm.invoke([
        SystemMessage(content="You are a market analyst. Summarize current conditions based on the tool data."),
        HumanMessage(content=str(result))
    ])
    
    print("[Market Agent] Complete.")
    return {"market_snapshot": response.content}

# -----------------
# Node: WebSearch Agent
# -----------------
def websearch_agent_node(state: AgentState, llm: ChatOpenAI, tools: dict):
    print("[WebSearch Agent] Finding historical precedents...")
    precedents_tool = tools.get("search_precedents")
    recovery_tool = tools.get("search_recovery_timeline")
    
    event_type = state.get("event_type", "market event")
    
    p_result = precedents_tool.invoke({"event_type": event_type, "geography": "global"})
    r_result = recovery_tool.invoke({"event_type": event_type})
    
    # Synthesize
    p_summary = llm.invoke([
        SystemMessage(content="Summarize historical precedents."),
        HumanMessage(content=str(p_result))
    ])
    r_summary = llm.invoke([
        SystemMessage(content="Summarize recovery timelines."),
        HumanMessage(content=str(r_result))
    ])
    
    print("[WebSearch Agent] Complete.")
    return {
        "historical_precedents": p_summary.content,
        "recovery_timeline": r_summary.content
    }

# -----------------
# Node: Synthesis Agent
# -----------------
def synthesis_agent_node(state: AgentState, llm: ChatOpenAI, tools: dict):
    print("[Synthesis Agent] Synthesizing final report...")
    telegram_tool = tools.get("send_telegram")
    log_tool = tools.get("log_event")
    
    # Build context
    context = f"""
    Original Request: {state['user_message']}
    
    News Event: {state['headline']} (Severity: {state['severity']}, Assets: {state['affected_assets']})
    
    Market Snapshot:
    {state.get('market_snapshot', 'N/A')}
    
    Historical Precedents:
    {state.get('historical_precedents', 'N/A')}
    
    Recovery Timeline:
    {state.get('recovery_timeline', 'N/A')}
    """
    
    response = llm.invoke([
        SystemMessage(content="You are the lead Synthesis Agent. Read the compiled data from sub-agents and formulate a cohesive, professional 2-3 paragraph telegram message for the user. Do format it nicely with bolding or emojis."),
        HumanMessage(content=context)
    ])
    
    final_text = response.content
    chat_id = state.get("chat_id")
    
    # Fire tools
    print("[Synthesis Agent] Dispatching tools...")
    if chat_id:
        telegram_tool.invoke({"chat_id": chat_id, "message": final_text})
        
    try:
        import json
        dump = json.dumps({"market": state.get('market_snapshot'), "history": state.get('historical_precedents')})
        log_tool.invoke({
            "headline": state.get('headline', 'Unknown'),
            "severity": state.get('severity', 0),
            "event_type": state.get('event_type', 'Unknown'),
            "raw_data_json": dump
        })
    except Exception as e:
         print("Log failed:", e)
         
    print("[Synthesis Agent] Complete.")
    return {"final_response": final_text}

# -----------------
# Node: Log and Stop
# -----------------
def log_and_stop_node(state: AgentState, tools: dict):
    print("[Terminal Node] Logging minor/duplicate event and stopping.")
    log_tool = tools.get("log_event")
    
    try:
        log_tool.invoke({
            "headline": state.get('headline', 'Unknown'),
            "severity": state.get('severity', 0),
            "event_type": state.get('event_type', 'Unknown'),
            "raw_data_json": "{}"
        })
    except:
        pass
        
    # Send a small message back via telegram to let user know it was ignored
    telegram_tool = tools.get("send_telegram")
    chat_id = state.get('chat_id')
    if chat_id:
        msg = f"Event logged but not escalated (Severity {state.get('severity')})."
        if getattr(state, 'is_duplicate', False):
             msg = "Event is a duplicate, ignoring."
        telegram_tool.invoke({"chat_id": chat_id, "message": msg})
        
    return {"final_response": "Stopped. " + msg}
