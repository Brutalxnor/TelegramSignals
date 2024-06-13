

import configparser
import json
import asyncio
from datetime import datetime
import os
import requests
from telethon import TelegramClient, events, types
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import PeerChannel

# Some functions to parse JSON date
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, bytes):
            return list(o)
        return json.JSONEncoder.default(self, o)

# Reading Configs
config = configparser.ConfigParser()
config.read("telethon.config")

# Setting configuration values
api_id = config["telethon_credentials"]["api_id"]
api_hash = config["telethon_credentials"]["api_hash"]
phone = config["telethon_credentials"]["phone_number"]
username = config["telethon_credentials"]["username"]

api_hash = str(api_hash)

# Telegram Bot credentials
TOKEN = '7463987435:AAF7xskJNHpPs1jvBGAysk3p6CJkmQWqfHU'  # Replace with your bot token

# Define source and target groups
source_groups = [
    '1556717257',   # Elite 
    '1861765467',   # 99%
    '@forex_factory_signals1',   # Elite Free
    '@fxgolden_trades1'    # 99% free
]
target_groups = [
    '-1002193517351',  # signal vip for Elite
    '-1002167695020',   # GolD Pioneer for 99%
    '@GoldGuruSignalFREE',
    '@TakeProfitSignalFREE'
]

## Snip Prive 2176378686
## @tessbta3y1
## @tessbta3y2
## Guru 2195133544

# Function to send text message
async def send_text_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    parameters = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    response = requests.post(url, data=parameters)
    response_json = response.json()
    print(f"Send text message response: {response_json}")  # Debug statement
    return response_json

# Function to send media message
async def send_media_message(token, chat_id, message, media_path, media_type):
    url = f"https://api.telegram.org/bot{token}/send{media_type.capitalize()}"
    parameters = {
        "chat_id": chat_id,
        "caption": message,
        "parse_mode": "HTML"
    }
    files = {media_type: open(media_path, "rb")}

    response = requests.post(url, data=parameters, files=files)
    response_json = response.json()
    print(f"Send media message response: {response_json}")  # Debug statement
    return response_json

# Function to send a sticker
async def send_sticker(token, chat_id, sticker_file_id):
    url = f"https://api.telegram.org/bot{token}/sendSticker"
    parameters = {
        "chat_id": chat_id,
        "sticker": sticker_file_id
    }
    response = requests.post(url, data=parameters)
    response_json = response.json()
    print(f"Send sticker response: {response_json}")  # Debug statement
    return response_json

# Create the client and connect
client = TelegramClient(username, api_id, api_hash)

# Create a lock for handling messages sequentially
message_lock = asyncio.Lock()

async def fetch_and_post_messages(phone, source_group, target_group):
    await client.start()
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
        print(f"Error fetching source entity: {e}")
        return

    try:
        if target_group.startswith('-100'):
            target_entity = PeerChannel(int(target_group))
        elif "t.me/" in target_group:
            target_entity = await client.get_entity(target_group.split('/')[-1])
        else:
            target_entity = await client.get_entity(target_group)
    except Exception as e:
        print(f"Error fetching target entity: {e}")
        return

    my_channel = await client.get_entity(source_entity)
    target_channel = await client.get_entity(target_entity)

    async def process_message(event, edited=False):
        async with message_lock:
            message = event.message
            message_text = message.message or ''
            response = None  # Initialize response to None

            # Handle replies
            if message.reply_to:
                replied_message = await message.get_reply_message()
                if replied_message:
                    reply_text = f"Reply to {replied_message.sender.username or replied_message.sender.id}:\n{replied_message.message}"
                    message_text = f"{reply_text}\n\n{message_text}"

            if message_text and not message.media:  # Handle text messages separately
                response = await send_text_message(TOKEN, target_group, message_text)
            elif message.media:  # Ensure the media is not empty
                media_type = None
                if isinstance(message.media, types.MessageMediaPhoto):
                    media_path = await client.download_media(message.media)
                    media_type = 'photo'
                elif isinstance(message.media, types.MessageMediaDocument):
                    mime_type = message.media.document.mime_type
                    if mime_type.startswith('video/') or mime_type == 'image/gif':
                        media_path = await client.download_media(message.media)
                        media_type = 'video'
                    elif mime_type == 'application/x-tgsticker':  # For stickers
                        sticker_file_id = message.media.document.id
                        response = await send_sticker(TOKEN, target_group, sticker_file_id)
                    else:
                        media_path = await client.download_media(message.media)
                        media_type = 'document'
                else:
                    media_path = await client.download_media(message.media)
                    media_type = 'document'
                
                if media_type:
                    response = await send_media_message(TOKEN, target_group, message_text, media_path, media_type)
                    os.remove(media_path)  # Remove the media after sending
            else:
                response = await send_text_message(TOKEN, target_group, message_text)
                
            if response and not response['ok']:
                print(f"Error sending message: {response}")
                
            if edited:
                print(f"Sent edited message: {message_text}\nResponse: {response}")
            else:
                print(f"Sent message: {message_text}\nResponse: {response}")

    # Listen for new messages and post them live
    @client.on(events.NewMessage(chats=my_channel))
    async def handler(event):
        await process_message(event)

    # Listen for edited messages and post them live
    @client.on(events.MessageEdited(chats=my_channel))
    async def handler_edit(event):
        await process_message(event, edited=True)

    print(f"Listening for new messages and edited messages from: {source_group} to post in {target_group}...")
    await client.run_until_disconnected()

async def main():
    tasks = []
    for source_group, target_group in zip(source_groups, target_groups):
        tasks.append(fetch_and_post_messages(phone, source_group, target_group))
    await asyncio.gather(*tasks)

with client:
    client.loop.run_until_complete(main())
