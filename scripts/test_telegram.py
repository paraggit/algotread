#!/usr/bin/env python3
"""
Test Telegram configuration and get chat ID.

This script helps you:
1. Test if your bot token is valid
2. Get your chat ID
3. Test sending a message

Usage:
    uv run -m scripts.test_telegram
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# Load environment variables
load_dotenv()


async def test_bot_token(bot_token: str):
    """Test if bot token is valid."""
    print("\n" + "="*60)
    print("Testing Bot Token...")
    print("="*60)
    
    try:
        bot = Bot(token=bot_token)
        me = await bot.get_me()
        print(f"✅ Bot token is valid!")
        print(f"   Bot username: @{me.username}")
        print(f"   Bot name: {me.first_name}")
        print(f"   Bot ID: {me.id}")
        return bot
    except TelegramError as e:
        print(f"❌ Invalid bot token: {e}")
        return None


async def get_updates(bot: Bot):
    """Get recent updates to find chat ID."""
    print("\n" + "="*60)
    print("Getting Recent Messages...")
    print("="*60)
    print("\n📱 Please send a message to your bot now!")
    print("   (Send any message like 'hello' or '/start')")
    print("\nWaiting for message...")
    
    for i in range(30):  # Wait up to 30 seconds
        try:
            updates = await bot.get_updates(timeout=1)
            if updates:
                print(f"\n✅ Found {len(updates)} message(s)!")
                for update in updates:
                    if update.message:
                        chat = update.message.chat
                        print(f"\n📋 Chat Information:")
                        print(f"   Chat ID: {chat.id}")
                        print(f"   Chat Type: {chat.type}")
                        if chat.username:
                            print(f"   Username: @{chat.username}")
                        if chat.title:
                            print(f"   Title: {chat.title}")
                        
                        print(f"\n💡 Use this in your .env file:")
                        print(f"   TELEGRAM_CHAT_ID={chat.id}")
                return updates
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(1)
    
    print("\n❌ No messages received in 30 seconds")
    print("   Make sure you've sent a message to your bot!")
    return None


async def test_send_message(bot: Bot, chat_id: str):
    """Test sending a message."""
    print("\n" + "="*60)
    print("Testing Message Sending...")
    print("="*60)
    
    try:
        # Try to parse chat_id as int
        try:
            chat_id_int = int(chat_id)
        except ValueError:
            print(f"❌ Chat ID must be a number, got: {chat_id}")
            print(f"   Current value looks like a username, not a chat ID")
            return False
        
        message = await bot.send_message(
            chat_id=chat_id_int,
            text="🎉 *Test Message from AlgoTread*\n\nYour Telegram configuration is working correctly!",
            parse_mode='Markdown'
        )
        print(f"✅ Message sent successfully!")
        print(f"   Message ID: {message.message_id}")
        return True
    except TelegramError as e:
        print(f"❌ Failed to send message: {e}")
        if "Not Found" in str(e):
            print(f"\n💡 The chat ID '{chat_id}' is incorrect.")
            print(f"   This usually means:")
            print(f"   1. You haven't sent a message to the bot yet")
            print(f"   2. The chat ID is wrong")
            print(f"   3. You're using a username instead of a numeric ID")
        return False


async def main():
    """Main function."""
    print("="*60)
    print("AlgoTread Telegram Configuration Tester")
    print("="*60)
    
    # Get configuration
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    
    if not bot_token:
        print("\n❌ TELEGRAM_BOT_TOKEN not found in .env file")
        print("\n📝 To fix:")
        print("   1. Get a bot token from @BotFather on Telegram")
        print("   2. Add to .env: TELEGRAM_BOT_TOKEN=your_token_here")
        sys.exit(1)
    
    print(f"\n📋 Current Configuration:")
    print(f"   Bot Token: {bot_token[:10]}...{bot_token[-10:]}")
    print(f"   Chat ID: {chat_id}")
    
    # Test bot token
    bot = await test_bot_token(bot_token)
    if not bot:
        sys.exit(1)
    
    # If chat_id is not numeric, try to get it
    if not chat_id or not chat_id.lstrip('-').isdigit():
        print(f"\n⚠️  Chat ID '{chat_id}' doesn't look like a numeric ID")
        updates = await get_updates(bot)
        if not updates:
            print("\n💡 Alternative methods to get your chat ID:")
            print("   1. Message @userinfobot on Telegram (for personal chat)")
            print("   2. Add @getidsbot to your channel/group")
            print("   3. Visit: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates")
    else:
        # Test sending message
        await test_send_message(bot, chat_id)
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
