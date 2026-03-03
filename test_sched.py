import asyncio
from agent import run_agent

async def main():
    print("Testing schedule interaction...")
    await run_agent(chat_id=7311476856, message="Can you set up a schedule to alert me about oil prices every 5 minutes?")

if __name__ == "__main__":
    asyncio.run(main())
