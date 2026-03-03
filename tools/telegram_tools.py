import os
from mcp.server.fastmcp import FastMCP
from aiogram import Bot
import asyncio

def register_telegram_tools(mcp: FastMCP):
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    @mcp.tool()
    async def send_telegram(chat_id: int, message: str) -> str:
        """
        Sends a Telegram message to a specific chat_id.
        """
        if not telegram_bot_token:
            return "Error: TELEGRAM_BOT_TOKEN is not set."
            
        try:
            # We initialize a temporary bot session just to send the message
            bot = Bot(token=telegram_bot_token)
            await bot.send_message(chat_id=chat_id, text=message)
            await bot.session.close()
            return f"Successfully sent message to chat {chat_id}"
        except Exception as e:
            return f"Error sending telegram message: {str(e)}"
