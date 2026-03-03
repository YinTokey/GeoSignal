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
    log_and_stop_node
)

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
    
    # 1. Add Nodes
    builder.add_node("Orchestrator", lambda s: orchestrator_node(s))
    builder.add_node("NewsAgent", lambda s: news_agent_node(s, llm, tool_map))
    builder.add_node("MarketAgent", lambda s: market_agent_node(s, llm, tool_map))
    builder.add_node("WebSearchAgent", lambda s: websearch_agent_node(s, llm, tool_map))
    builder.add_node("SynthesisAgent", lambda s: synthesis_agent_node(s, llm, tool_map))
    builder.add_node("LogAndStop", lambda s: log_and_stop_node(s, tool_map))
    
    # 2. Add Flow Edges
    builder.add_edge(START, "Orchestrator")
    builder.add_edge("Orchestrator", "NewsAgent")
    
    # The NewsAgent branches conditionally based on severity and duplicates
    builder.add_conditional_edges(
        "NewsAgent",
        route_after_news,
        {
            "market": ["MarketAgent", "WebSearchAgent"],
            "log_and_stop": "LogAndStop"
        }
    )
    
    # If it routed to LogAndStop, we end.
    builder.add_edge("LogAndStop", END)
    
    # Parallel edges from Market and WebSearch converge to Synthesis
    builder.add_edge(["MarketAgent", "WebSearchAgent"], "SynthesisAgent")
    
    # Synthesis ends the flow
    builder.add_edge("SynthesisAgent", END)
    
    return builder.compile()
