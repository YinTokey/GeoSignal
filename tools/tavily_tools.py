import os
from mcp.server.fastmcp import FastMCP
from tavily import AsyncTavilyClient

def register_tavily_tools(mcp: FastMCP):
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    
    @mcp.tool()
    async def search_news(query: str, max_results: int = 5) -> str:
        """
        Search the web for the latest news events based on the query.
        """
        if not tavily_api_key:
            return "Error: TAVILY_API_KEY is not set."
            
        client = AsyncTavilyClient(api_key=tavily_api_key)
        try:
            # We enforce topic="news" to get news specifically if supported
            response = await client.search(query=query, max_results=max_results, search_depth="advanced", topic="news")
            
            results_str = f"News Results for '{query}':\n\n"
            for i, result in enumerate(response.get('results', []), 1):
                results_str += f"{i}. {result.get('title')}\n"
                results_str += f"URL: {result.get('url')}\n"
                results_str += f"Content: {result.get('content')}\n\n"
            return results_str
        except Exception as e:
            return f"Error executing news search: {str(e)}"

    @mcp.tool()
    async def get_market_snapshot(asset_or_market: str) -> str:
        """
        Retrieve a snapshot of the current market state for a given asset or general market.
        """
        if not tavily_api_key:
            return "Error: TAVILY_API_KEY is not set."
            
        client = AsyncTavilyClient(api_key=tavily_api_key)
        try:
            # A focused query for market data
            query = f"current market snapshot price trends sentiment {asset_or_market}"
            response = await client.search(query=query, max_results=3, search_depth="advanced")
            
            results_str = f"Market Snapshot for '{asset_or_market}':\n\n"
            for i, result in enumerate(response.get('results', []), 1):
                results_str += f"- {result.get('content')}\n"
            return results_str
        except Exception as e:
            return f"Error executing market snapshot: {str(e)}"
            
    @mcp.tool()
    async def search_precedents(event_type: str, geography: str = "global") -> str:
        """
        Find historical precedents for a specific type of event in a given geography.
        """
        if not tavily_api_key:
            return "Error: TAVILY_API_KEY is not set."
            
        client = AsyncTavilyClient(api_key=tavily_api_key)
        try:
            query = f"historical precedents past events similar to {event_type} in {geography}"
            response = await client.search(query=query, max_results=5, search_depth="advanced")
            
            results_str = f"Historical Precedents for '{event_type}' ({geography}):\n\n"
            for i, result in enumerate(response.get('results', []), 1):
                results_str += f"{i}. {result.get('title')}\n   {result.get('content')}\n"
            return results_str
        except Exception as e:
            return f"Error executing precedent search: {str(e)}"

    @mcp.tool()
    async def search_recovery_timeline(event_type: str) -> str:
        """
        Search for typical market or asset recovery timelines following a specific event type.
        """
        if not tavily_api_key:
            return "Error: TAVILY_API_KEY is not set."
            
        client = AsyncTavilyClient(api_key=tavily_api_key)
        try:
            query = f"market asset recovery timeline long term effects after {event_type} historical"
            response = await client.search(query=query, max_results=4, search_depth="advanced")
            
            results_str = f"Recovery Timeline estimates for '{event_type}':\n\n"
            for i, result in enumerate(response.get('results', []), 1):
                results_str += f"- {result.get('content')}\n"
            return results_str
        except Exception as e:
            return f"Error executing recovery timeline search: {str(e)}"
