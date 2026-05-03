import aiohttp
import discord
from discord.ext import tasks, commands
import os

API_KEY = os.getenv("API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
ROLE_ID = int(os.getenv("ROLE_ID"))


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

USERNAMES = os.getenv("USERNAMES", "").split(",")

# Store last known status to avoid spam
last_status = {}

# Cache UUIDs so we don't request them every time
uuid_cache = {}

# ==================

async def get_uuid(session, username):
    if username in uuid_cache:
        return uuid_cache[username]

    url = f"https://api.mojang.com/users/profiles/minecraft/{username}"

    async with session.get(url) as resp:
        if resp.status != 200:
            return None

        data = await resp.json(content_type=None)

        if "id" not in data:
            return None

        uuid_cache[username] = data["id"]
        return data["id"]


@tasks.loop(seconds=60)
async def OnlineCheck():
    channel = bot.get_channel(CHANNEL_ID)

    async with aiohttp.ClientSession() as session:
        for username in USERNAMES:
            try:
                uuid = await get_uuid(session, username)

                if not uuid:
                    await channel.send(f"{username}: Invalid username")
                    continue

                url = f"https://api.hypixel.net/status?key={API_KEY}&uuid={uuid}"
                async with session.get(url) as resp:
                    data = await resp.json()

                if not data.get("success"):
                    await channel.send(f"{username}: API error - {data.get('cause')}")
                    continue

                online = data.get("session", {}).get("online", False)

                # Only send message if status changed
                if username not in last_status or last_status[username] != online:
                    last_status[username] = online

                    if online:
                        await channel.send(f"🟢 <@&{ROLE_ID}> {username} logged on")
                    else:
                        await channel.send(f"🔴 {username} logged off")

            except Exception as e:
                await channel.send(f"{username}: Error - {str(e)}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    OnlineCheck.start()

bot.run(DISCORD_TOKEN)