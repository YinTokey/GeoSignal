import asyncio
import os
from datetime import datetime, timezone
from pymongo import MongoClient
from croniter import croniter

from agent import run_agent

def get_schedules_collection():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    client = MongoClient(mongo_uri)
    db = client["geosignal"]
    return db["schedules"]

async def start_scheduler():
    print("Starting background scheduler...")
    while True:
        try:
            collection = get_schedules_collection()
            now = datetime.now(timezone.utc)
            schedules = collection.find({"is_active": True})
            for sched in schedules:
                try:
                    last_run = sched.get("last_run")
                    chat_id = sched["chat_id"]
                    query = sched["query"]
                    cron_expr = sched["cron_expr"]
                    
                    if last_run:
                        if last_run.tzinfo is None:
                            last_run = last_run.replace(tzinfo=timezone.utc)
                    
                    should_run = False
                    if not last_run:
                        should_run = True
                    else:
                        itr = croniter(cron_expr, last_run)
                        next_run = itr.get_next(datetime)
                        # Ensure next_run has timezone
                        if next_run.tzinfo is None:
                            next_run = next_run.replace(tzinfo=timezone.utc)
                            
                        if now >= next_run:
                            should_run = True

                    if should_run:
                        # run agent
                        print(f"Executing scheduled task for chat {chat_id}: {query}")
                        collection.update_one({"_id": sched["_id"]}, {"$set": {"last_run": now}})
                        
                        # run async task in background
                        asyncio.create_task(run_agent(chat_id=chat_id, message=query))
                        
                except Exception as loop_e:
                    print(f"Error in schedule loop for {sched}: {loop_e}")
                    
        except Exception as e:
            print(f"Scheduler failed: {e}")
        
        await asyncio.sleep(60) # Run every minute

if __name__ == "__main__":
    asyncio.run(start_scheduler())
