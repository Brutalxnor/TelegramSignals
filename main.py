import os
import configparser
import json
import asyncio
from datetime import datetime, timedelta, timezone
import requests
import time
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl import types
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel

# Some functions to parse JSON date
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, bytes):
            return list(o)
        return json.JSONEncoder.default(self, o)

# Reading Configs from environment variables
api_id = os.getenv("TELETHON_API_ID")
api_hash = os.getenv("TELETHON_API_HASH")
phone = os.getenv("TELETHON_PHONE_NUMBER")
username = os.getenv("TELETHON_USERNAME")

api_hash = str(api_hash)

# Telegram Bot credentials
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Define source and target groups
source_groups = [
    '2176378686',  # Source Group 1 ID
    '@tessbta3y1',   # Source Group 2 ID
    '2195133544', #tessprivate2
    '2202517103' #tess2
]
target_groups = [
    '2193517351',  # Target Group 1 ID
    '2167695020',   # Target Group 2 ID
    '@GoldGuruSignalFREE',
    '@TakeProfitSignalFREE'
]

# Function to send message
def send_message(token, chat_id, message, media_path=None, media_type='photo'):
    if media_path:
        url = f"https://api.telegram.org/bot{token}/send{media_type.capitalize()}"
        parameters = {
            "chat_id": chat_id,
            "caption": message,
            "parse_mode": "HTML"
        }
        files = {media_type: open(media_path, "rb")}
        response = requests.post(url, data=parameters, files=files)
    else:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        parameters = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.get(url, params=parameters)
    
    response_json = response.json()
    print(f"Send message response: {response_json}")  # Debug statement
    return response_json

# Function to send a sticker
def send_sticker(token, chat_id, sticker_file_id):
    url = f"https://api.telegram.org/bot{token}/sendSticker"
    parameters = {
        "chat_id": chat_id,
        "sticker": sticker_file_id
    }
    response = requests.get(url, params=parameters)
    response_json = response.json()
    print(f"Send sticker response: {response_json}")  # Debug statement
    return response_json

# Create the client and connect
client = TelegramClient(username, api_id, api_hash)

async def fetch_and_post_messages(phone, source_group, target_group):
    await client.start(phone=lambda: phone)
    print(f"Client Created for source: {source_group} and target: {target_group}")
    # Ensure you're authorized
    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        try:
            await client.sign_in(phone, input('Enter the code: '))
        except SessionPasswordNeededError:
            await client.sign_in(password=input('Password: '))

    try:
        if source_group.isdigit():
            source_entity = PeerChannel(int(source_group))
        elif "t.me/" in source_group:
            source_entity = await client.get_entity(source_group.split('/')[-1])
        else:
            source_entity = await client.get_entity(source_group)
    except Exception as e:
        print(f"Error fetching entity: {e}")
        return

    my_channel = await client.get_entity(source_entity)

    one_hour_ago = (datetime.now() - timedelta(hours=1)).replace(tzinfo=timezone.utc)

    offset_id = 0
    limit = 50
    message_count = 0

    # Fetch and post messages one by one
    while True:
        print(f"Current Offset ID for {source_group} is:", offset_id)
        history = await client(GetHistoryRequest(
            peer=my_channel,
            offset_id=offset_id,
            offset_date=None,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0
        ))
        if not history.messages:
            print("No more messages to fetch.")
            break
        for message in history.messages:
            print(f"Fetched message ID: {message.id} Date: {message.date}")  # Debug statement
            if message.date > one_hour_ago:
                message_text = message.message
                if message_text or message.media:  # Ensure the message or media is not empty
                    if message.media:
                        if isinstance(message.media, types.MessageMediaPhoto):
                            media_path = await client.download_media(message.media)
                            response = send_message(TOKEN, target_group, message_text, media_path, 'photo')
                            os.remove(media_path)  # Remove the media after sending
                        elif isinstance(message.media, types.MessageMediaDocument):
                            if message.media.document.mime_type.startswith('video/') or message.media.document.mime_type == 'image/gif':
                                media_path = await client.download_media(message.media)
                                response = send_message(TOKEN, target_group, message_text, media_path, 'video')
                                os.remove(media_path)  # Remove the media after sending
                            elif message.media.document.mime_type == 'application/x-tgsticker':  # For stickers
                                sticker_file_id = message.media.document.id
                                response = send_sticker(TOKEN, target_group, sticker_file_id)
                            else:
                                response = send_message(TOKEN, target_group, message_text)
                    else:
                        response = send_message(TOKEN, target_group, message_text)
                    print(f"Sent message: {message_text}\nResponse: {response}")

                message_count += 1
                if message_count >= 50:
                    print("Cooldown for 10 seconds...")
                    time.sleep(10)
                    message_count = 0
            
            offset_id = message.id

    # Listen for new messages and post them live
    @client.on(events.NewMessage(chats=my_channel))
    async def handler(event):
        message = event.message
        message_text = message.message
        if message_text or message.media:  # Ensure the message or media is not empty
            if message.media:
                if isinstance(message.media, types.MessageMediaPhoto):
                    media_path = await client.download_media(message.media)
                    response = send_message(TOKEN, target_group, message_text, media_path, 'photo')
                    os.remove(media_path)  # Remove the media after sending
                elif isinstance(message.media, types.MessageMediaDocument):
                    if message.media.document.mime_type.startswith('video/') or message.media.document.mime_type == 'image/gif':
                        media_path = await client.download_media(message.media)
                        response = send_message(TOKEN, target_group, message_text, media_path, 'video')
                        os.remove(media_path)  # Remove the media after sending
                    elif message.media.document.mime_type == 'application/x-tgsticker':  # For stickers
                        sticker_file_id = message.media.document.id
                        response = send_sticker(TOKEN, target_group, sticker_file_id)
                    else:
                        response = send_message(TOKEN, target_group, message_text)
                else:
                    response = send_message(TOKEN, target_group, message_text)
            else:
                response = send_message(TOKEN, target_group, message_text)
            print(f"Sent message: {message_text}\nResponse: {response}")

    print(f"Listening for new messages from: {source_group} to post in {target_group}...")
    await client.run_until_disconnected()

async def main():
    tasks = []
    for source_group, target_group in zip(source_groups, target_groups):
        tasks.append(fetch_and_post_messages(phone, source_group, target_group))
    await asyncio.gather(*tasks)

with client:
    client.loop.run_until_complete(main())
