import os
from mcp.server.fastmcp import FastMCP
from pymongo import MongoClient

def get_schedules_collection():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    client = MongoClient(mongo_uri)
    db = client["geosignal"]
    return db["schedules"]

def register_scheduler_tools(mcp: FastMCP):

    @mcp.tool()
    def set_schedule(chat_id: int, query: str, cron_expr: str) -> str:
        """
        Set a new scheduled task for the user.
        cron_expr MUST be a standard 5-part cron string (e.g. '*/5 * * * *' for every 5 minutes).
        """
        try:
            collection = get_schedules_collection()
            
            doc = {
                "chat_id": chat_id,
                "query": query,
                "cron_expr": cron_expr,
                "is_active": True
            }
            collection.update_one(
                {"chat_id": chat_id, "query": query},
                {"$set": doc, "$setOnInsert": {"last_run": None}},
                upsert=True
            )
            return f"Successfully scheduled query '{query}' with cron '{cron_expr}'."
        except Exception as e:
            return f"Error scheduling task: {str(e)}"

    @mcp.tool()
    def pause_schedule(chat_id: int, query: str) -> str:
        """
        Pause an existing scheduled task.
        """
        try:
            collection = get_schedules_collection()
            result = collection.update_one(
                {"chat_id": chat_id, "query": query},
                {"$set": {"is_active": False}}
            )
            if result.modified_count > 0:
                return f"Successfully paused schedule for '{query}'."
            return "No active schedule found for that query."
        except Exception as e:
            return f"Error pausing schedule: {str(e)}"
