import contextlib
import asyncio
from fastapi import FastAPI
from dotenv import load_dotenv

from bot import start_telegram_bot, stop_telegram_bot
from agent import init_agent, close_agent
from scheduler_loop import start_scheduler
from dotenv import load_dotenv

load_dotenv()

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs on startup
    print("Starting FastAPI app...")
    # Initialize the local MCP Server and Agent
    await init_agent()
    # Start the bot as a background task
    bot_task = asyncio.create_task(start_telegram_bot())
    sched_task = asyncio.create_task(start_scheduler())
    
    yield
    
    # This runs on shutdown
    print("Shutting down FastAPI app...")
    bot_task.cancel()
    sched_task.cancel()
    try:
        await bot_task
        await sched_task
    except asyncio.CancelledError:
        pass
    await stop_telegram_bot()
    await close_agent()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Agent Server is running!", "status": "ok"}
