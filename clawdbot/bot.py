import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"ClawdBot is online as {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, name="over the server 👁️"
        )
    )
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
    print("All cogs loaded.")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("*flicks ear* That command doesn't exist. Try `!help`.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"*tilts head* You're missing an argument: `{error.param}`")
    else:
        await ctx.send(f"Something went wrong: {error}")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN not set in .env file")
    bot.run(token)
