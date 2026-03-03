from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from agents.state import AgentState

# -----------------
# Agent Output Models
# -----------------

class AffectedAsset(BaseModel):
    asset_name: str = Field(description="Name of the asset (e.g. 'oil', 'BTC')")
    impact_description: str = Field(description="How it is impacted (e.g. 'DIRECT - spike')")

class NewsOutput(BaseModel):
    is_significant: bool
    is_duplicate: bool
    severity: float         
    headline: str            
    what_happened: str       
    why_it_matters: str      
    event_type: str          
    affected_assets: List[AffectedAsset]
    escalation_signals: List[str] 

class MarketAsset(BaseModel):
    asset_name: str = Field(description="Name of the asset (e.g. 'BTC', 'oil')")
    price: str = Field(description="Current price string")
    change_1h: str = Field(description="1 hour change percentage")
    signal: str = Field(description="What this means (e.g. 'dumping hard')")

class MarketOutput(BaseModel):
    snapshot_time: str = Field(description="ISO timestamp of the snapshot")
    market_mood: str = Field(description="Overall sentiment description")
    assets: List[MarketAsset] = Field(default_factory=list, description="List of key assets and their market state")
    fear_greed: str = Field(description="Estimated fear/greed metric")
    liquidations: str = Field(description="Info on liquidations if available")
    volume_anomaly: str = Field(description="Any notable volume anomalies")
    summary: str = Field(description="Overall interpretation of what the market is doing right now")

class WebSearchMatch(BaseModel):
    event: str = Field(description="Name of the historical event")
    similarity_reason: str = Field(description="Why it is similar to the current event")
    key_difference: str = Field(description="Crucial differences to keep in mind")
    what_happened_to_markets: str = Field(description="Factual breakdown of asset reactions")
    recovery_trigger: str = Field(description="What caused the market to recover")

class WebSearchOutput(BaseModel):
    best_match: WebSearchMatch = Field(description="The closest historical precedent")
    second_match: Optional[WebSearchMatch] = Field(None, description="A secondary precedent")
    pattern_insight: str = Field(description="What both precedents teach us about this situation")
    key_unknown: str = Field(description="What is missing from history that we don't know yet")

# -----------------
# Node: Orchestrator
# -----------------
async def orchestrator_node(state: AgentState):
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
async def news_agent_node(state: AgentState, llm: ChatOpenAI, tools: dict):
    """
    The News Agent calls `search_news` and `check_duplicate`.
    """
    print("[News Agent] Analyzing news for message...")
    search_news_tool = tools.get("search_news")
    check_duplicate_tool = tools.get("check_duplicate")
    if not search_news_tool or not check_duplicate_tool:
        raise RuntimeError("Required tools missing: search_news and/or check_duplicate")
    
    # Let the LLM use the tools to find out what's going on
    system_prompt = SystemMessage(content='''You are a Financial News Agent. 
    1. Use the search_news tool to find out what the user is talking about.
    2. Then, use the check_duplicate tool to see if the headline has already been processed.
    
    You must figure out:
    1. What happened (fact)
    2. Why it matters (context)
    3. What it means (interpretation)
    
    Return your final understanding so it can be extracted into the detailed schema.
    ''')
    
    # We bind tools
    agent_llm = llm.bind_tools([search_news_tool, check_duplicate_tool])
    
    # This is a simple 1-step call. For a true ReAct agent, you'd use a sub-graph or create_react_agent.
    # For brevity in this implementation, we will use a small inline tool-calling loop.
    messages = [system_prompt, HumanMessage(content=state['user_message'])]
    
    duplicate_result = None
    while True:
        response = await agent_llm.ainvoke(messages)
        messages.append(response)
        
        if not response.tool_calls:
            break
            
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            print(f"[News Agent] Calling {tool_name} with {tool_args}")
            
            if tool_name == "search_news":
                tool_msg = await search_news_tool.ainvoke(tool_args)
            elif tool_name == "check_duplicate":
                tool_msg = await check_duplicate_tool.ainvoke(tool_args)
                duplicate_result = str(tool_msg).strip().lower()
            else:
                tool_msg = f"Unknown tool: {tool_name}"

            messages.append(
                ToolMessage(
                    content=str(tool_msg),
                    name=tool_name,
                    tool_call_id=tool_call["id"],
                )
            )

    # Now we extract the structured output from the final text
    extractor_llm = llm.with_structured_output(NewsOutput)
    structured_news: NewsOutput = await extractor_llm.ainvoke(
        [SystemMessage(content="Extract the detailed event information into the required schema. Ensure you answer what happened, why it matters, and what it means."), messages[-1]]
    )
    
    # Determine duplicate directly from tool response (not LLM text heuristics).
    is_dupe = duplicate_result == "true"
    if is_dupe:
        structured_news.is_duplicate = True
    
    return {
        "severity": structured_news.severity,
        "is_duplicate": structured_news.is_duplicate,
        "news_data": structured_news.model_dump()
    }

# -----------------
# Edge: Route after News
# -----------------
def route_after_news(state: AgentState) -> list[str]:
    print(f"[Router] Severity is {state['severity']}, Duplicate: {state.get('is_duplicate')}")
    if state.get("is_duplicate", False):
        print("[Router] Duplicate detected. Stopping.")
        return ["LogAndStop"]
        
    severity = state.get("severity", 0)
    if severity >= 1:
         print("[Router] High severity. Proceeding to Market & WebSearch.")
         return ["MarketAgent", "WebSearchAgent"]
    else:
         print("[Router] Low severity. Stopping.")
         return ["LogAndStop"]

# -----------------
# Node: Market Agent
# -----------------
async def market_agent_node(state: AgentState, llm: ChatOpenAI, tools: dict):
    print("[Market Agent] Fetching market snapshot...")
    market_tool = tools.get("get_market_snapshot")
    if not market_tool:
        raise RuntimeError("Required tool missing: get_market_snapshot")
    
    assets_list = state.get("news_data", {}).get("affected_assets", [])
    assets_str = ", ".join([a.get("asset_name", "") for a in assets_list]) if assets_list else "general market"
    
    result = await market_tool.ainvoke({"asset_or_market": assets_str})
    
    # Synthesize the raw output into the clean structured MarketOutput model
    extract_llm = llm.with_structured_output(MarketOutput)
    structured_market: MarketOutput = await extract_llm.ainvoke([
        SystemMessage(content="""You are a market analyst. Summarize current conditions based on the tool data.
        You must ensure you answer:
        1. What happened to these assets (fact)
        2. Why it matters (context)
        3. What it means (interpretation in the summary)"""),
        HumanMessage(content=str(result))
    ])
    
    print("[Market Agent] Complete.")
    return {"market_data": structured_market.model_dump()}

# -----------------
# Node: WebSearch Agent
# -----------------
async def websearch_agent_node(state: AgentState, llm: ChatOpenAI, tools: dict):
    print("[WebSearch Agent] Finding historical precedents...")
    precedents_tool = tools.get("search_precedents")
    recovery_tool = tools.get("search_recovery_timeline")
    if not precedents_tool or not recovery_tool:
        raise RuntimeError("Required tools missing: search_precedents and/or search_recovery_timeline")
    
    event_type = state.get("news_data", {}).get("event_type", "market event")
    
    p_result = await precedents_tool.ainvoke({"event_type": event_type, "geography": "global"})
    r_result = await recovery_tool.ainvoke({"event_type": event_type})
    
    # Synthesize into structured output
    extract_llm = llm.with_structured_output(WebSearchOutput)
    structured_web: WebSearchOutput = await extract_llm.ainvoke([
        SystemMessage(content="""You are a historical event analyst. Find historical precedents and timelines matching this context.
        Filter the data to answer:
        1. What happened before (fact)
        2. Why it is similar/matters (context)
        3. What it means for the current pattern (interpretation)"""),
        HumanMessage(content=f"Precedents:\n{p_result}\n\nRecovery:\n{r_result}")
    ])
    
    print("[WebSearch Agent] Complete.")
    return {"websearch_data": structured_web.model_dump()}

# -----------------
# Node: Synthesis Agent
# -----------------
async def synthesis_agent_node(state: AgentState, llm: ChatOpenAI, tools: dict):
    print("[Synthesis Agent] Synthesizing final report...")
    telegram_tool = tools.get("send_telegram")
    log_tool = tools.get("log_event")
    if not log_tool:
        raise RuntimeError("Required tool missing: log_event")
    
    import json
    news_json = json.dumps(state.get("news_data", {}), indent=2)
    market_json = json.dumps(state.get("market_data", {}), indent=2)
    web_json = json.dumps(state.get("websearch_data", {}), indent=2)
    
    # Build context
    context = f"""
    Original Request: {state['user_message']}
    
    --- NEWS CONTEXT ---
    {news_json}
    
    --- MARKET CONTEXT ---
    {market_json}
    
    --- HISTORICAL PRECEDENTS ---
    {web_json}
    """
    
    response = await llm.ainvoke([
        SystemMessage(content="""You are GeoSignal's synthesis agent.
Write a Telegram alert. STRICT rules:
- MAX 150 words total
- No preamble, no sign-off
- Use this exact structure, nothing else:

🚨 [EVENT TYPE] - Severity [X]/10

[1 concise sentence about what happened]

[1 concise sentence about why it matters]

📊 Asset Impact:
[List up to 4 affected assets based on context: [Asset]: [▲/▼] [reason, 5 words max]]

"""),
        HumanMessage(content=context)
    ])
    
    final_text = response.content
    chat_id = state.get("chat_id")
    
    # Fire tools
    print("[Synthesis Agent] Dispatching tools...")
    if chat_id and telegram_tool:
        await telegram_tool.ainvoke({"chat_id": chat_id, "message": final_text})
        
    try:
        dump = json.dumps({
            "market_data": state.get('market_data'), 
            "websearch_data": state.get('websearch_data')
        })
        n_data = state.get("news_data", {})
        await log_tool.ainvoke({
            "headline": n_data.get('headline', 'Unknown'),
            "severity": n_data.get('severity', 0),
            "event_type": n_data.get('event_type', 'Unknown'),
            "raw_data_json": dump
        })
    except Exception as e:
         print("Log failed:", e)
         
    print("[Synthesis Agent] Complete.")
    return {"final_response": final_text}

# -----------------
# Node: Log and Stop
# -----------------
async def log_and_stop_node(state: AgentState, tools: dict):
    print("[Terminal Node] Logging minor/duplicate event and stopping.")
    log_tool = tools.get("log_event")
    if not log_tool:
        raise RuntimeError("Required tool missing: log_event")
    
    try:
        n_data = state.get("news_data", {})
        await log_tool.ainvoke({
            "headline": n_data.get('headline', 'Unknown'),
            "severity": n_data.get('severity', 0),
            "event_type": n_data.get('event_type', 'Unknown'),
            "raw_data_json": "{}"
        })
    except:
        pass
        
    # Send a small message back via telegram to let user know it was ignored
    telegram_tool = tools.get("send_telegram")
    chat_id = state.get('chat_id')
    msg = f"Event logged but not escalated (Severity {state.get('severity')})."
    if chat_id:
        if state.get("is_duplicate", False):
             msg = "Event is a duplicate, ignoring."
        if telegram_tool:
            await telegram_tool.ainvoke({"chat_id": chat_id, "message": msg})
        
    return {"final_response": "Stopped. " + msg}
