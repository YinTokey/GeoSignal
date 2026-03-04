from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda

from agents.state import AgentState
from agents.nodes import (
    orchestrator_node,
    news_agent_node,
    route_after_news,
    market_agent_node,
    websearch_agent_node,
    synthesis_agent_node,
    log_and_stop_node,
    scheduler_agent_node,
    general_query_node
)

def route_after_orchestrator(state: AgentState):
    intent = state.get("intent")
    if intent == "schedule":
        return ["SchedulerAgent"]
    elif intent == "general_query":
        return ["GeneralQueryAgent"]
    return ["NewsAgent"]

def build_agent_graph(llm: ChatOpenAI, raw_tools: list):
    """
    Builds the state graph mapping Orchestrator -> News -> Market/WebSearch -> Synthesis.
    
    `raw_tools` is a list of langchain tool objects retrieved from the MCP adapter.
    We convert them into a mapping so nodes can easily trigger the ones they need.
    """
    # Create a quick dictionary mapping for tools
    tool_map = {tool.name: tool for tool in raw_tools}
    
    # We bind dependencies to our node functions using Functools or RunnableLambda
    # In Langchain, we can just pass them as constants if wrapped with lambdas
    
    # Define our graph structure using the explicitly typed AgentState
    builder = StateGraph(AgentState)
    
    from functools import partial
    
    # 1. Add Nodes
    builder.add_node("Orchestrator", partial(orchestrator_node, llm=llm))
    builder.add_node("NewsAgent", partial(news_agent_node, llm=llm, tools=tool_map))
    builder.add_node("MarketAgent", partial(market_agent_node, llm=llm, tools=tool_map))
    builder.add_node("WebSearchAgent", partial(websearch_agent_node, llm=llm, tools=tool_map))
    builder.add_node("SynthesisAgent", partial(synthesis_agent_node, llm=llm, tools=tool_map))
    builder.add_node("LogAndStop", partial(log_and_stop_node, tools=tool_map))
    builder.add_node("SchedulerAgent", partial(scheduler_agent_node, llm=llm, tools=tool_map))
    builder.add_node("GeneralQueryAgent", partial(general_query_node, llm=llm, tools=tool_map))
    
    # 2. Add Flow Edges
    builder.add_edge(START, "Orchestrator")
    builder.add_conditional_edges("Orchestrator", route_after_orchestrator, ["SchedulerAgent", "GeneralQueryAgent", "NewsAgent"])
    
    builder.add_edge("SchedulerAgent", END)
    builder.add_edge("GeneralQueryAgent", END)
    
    # The NewsAgent branches conditionally based on severity and duplicates
    # route_after_news now returns ["MarketAgent", "WebSearchAgent"] or ["LogAndStop"] directly
    builder.add_conditional_edges("NewsAgent", route_after_news, ["MarketAgent", "WebSearchAgent", "LogAndStop"])
    
    # If it routed to LogAndStop, we end.
    builder.add_edge("LogAndStop", END)
    
    # Parallel edges from Market and WebSearch converge to Synthesis
    builder.add_edge("MarketAgent", "SynthesisAgent")
    builder.add_edge("WebSearchAgent", "SynthesisAgent")
    
    # Synthesis ends the flow
    builder.add_edge("SynthesisAgent", END)
    
    return builder.compile()
