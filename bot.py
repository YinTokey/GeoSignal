import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from dotenv import load_dotenv

# We will later import the agent here
from agent import run_agent

load_dotenv()

bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
if not bot_token:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in the environment.")

bot = Bot(token=bot_token)
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await message.answer(f"Hello, {message.from_user.full_name}! I am your AI assistant. Send me a message and I'll process it.")

@dp.message()
async def process_message(message: Message) -> None:
    """
    Handler for all other messages. It will pass the message to the AI agent.
    """
    if not message.text:
        return
    
    # Send a temporary "thinking" message or chat action
    processing_msg = await message.answer("Thinking...")
    print("Processing message: ", message.text)
    await message.answer(f"This is testing")

    # try:
    #     # Call the tool-enabled agent.
    #     response_text = await run_agent(message.text)
    #     await processing_msg.edit_text(response_text)
    # except Exception as e:
    #     await processing_msg.edit_text(f"Sorry, an error occurred: {e}")

async def start_telegram_bot():
    """Starts the bot polling. To be run as a background task."""
    print("Starting Telegram Bot long pulling...")
    await dp.start_polling(bot)

async def stop_telegram_bot():
    """Stops the bot."""
    print("Stopping Telegram Bot...")
    await bot.session.close()
