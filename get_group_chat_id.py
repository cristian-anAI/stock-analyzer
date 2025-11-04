"""
Script to get Telegram Group Chat ID
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Fix console encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Load environment variables
load_dotenv('.env.prod')

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in .env.prod")
    sys.exit(1)

# Get updates
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()

    if not data.get('result'):
        print("No messages found. Send a message to the group mentioning the bot first!")
        sys.exit(1)

    print("\n=== Available Chats ===\n")

    seen_chats = set()
    for update in data['result']:
        if 'message' in update:
            msg = update['message']
            chat = msg['chat']
            chat_id = chat['id']

            if chat_id not in seen_chats:
                seen_chats.add(chat_id)

                chat_type = chat['type']
                chat_title = chat.get('title', chat.get('first_name', 'Unknown'))

                print(f"Chat ID: {chat_id}")
                print(f"Type: {chat_type}")
                print(f"Title: {chat_title}")
                print("-" * 50)

    print("\n=== Instructions ===")
    print("1. Find your group in the list above")
    print("2. Copy the Chat ID (the negative number for groups)")
    print("3. Update .env.prod:")
    print("   TELEGRAM_CHAT_ID=<your_group_chat_id>")
    print("\nNote: Group chat IDs usually start with a minus sign (e.g., -1001234567890)")

else:
    print(f"ERROR: Failed to get updates. Status code: {response.status_code}")
    print(f"Response: {response.text}")
