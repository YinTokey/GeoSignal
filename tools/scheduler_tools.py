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
    def get_active_schedule(chat_id: int) -> str:
        """
        Check if the user already has an active schedule.
        Returns a description of the schedule if it exists, otherwise 'None'.
        """
        try:
            collection = get_schedules_collection()
            doc = collection.find_one({"chat_id": chat_id, "is_active": True})
            if doc:
                return f"Active Schedule Found: Monitoring '{doc['query']}' with cron '{doc['cron_expr']}'."
            return "None"
        except Exception as e:
            return f"Error checking schedule: {str(e)}"

    @mcp.tool()
    def set_schedule(chat_id: int, query: str, cron_expr: str) -> str:
        """
        Set a new scheduled task for the user.
        """
        try:
            from datetime import datetime, timezone
            from croniter import croniter
            collection = get_schedules_collection()
            
            now = datetime.now(timezone.utc)
            
            # Since the LLM just generated the initial baseline response for the user synchronously,
            # we calculate the *next* immediate cron run edge and set THAT as the 'last_run' timestamp. 
            # This causes the background loop to naturally skip the very first trigger boundary and wait 
            # for a full cron cycle, preventing back-to-back messages (e.g. 7:29 and 7:31).
            try:
                itr = croniter(cron_expr, now)
                next_boundary = itr.get_next(datetime)
                if next_boundary.tzinfo is None:
                     next_boundary = next_boundary.replace(tzinfo=timezone.utc)
            except Exception:
                next_boundary = now
            
            doc = {
                "chat_id": chat_id,
                "query": query,
                "cron_expr": cron_expr,
                "is_active": True,
                "last_run": next_boundary
            }
            # Uniqueness enforced on chat_id. Overwrite the whole doc if it exists.
            collection.update_one(
                {"chat_id": chat_id},
                {"$set": doc},
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
                {"chat_id": chat_id},
                {"$set": {"is_active": False}}
            )
            if result.modified_count > 0:
                return f"Successfully paused schedule for '{query}'."
            return "No active schedule found for that query."
        except Exception as e:
            return f"Error pausing schedule: {str(e)}"
