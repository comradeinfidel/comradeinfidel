import discord
from discord.ext import commands
import random


CLAWD_RESPONSES = [
    "*narrows golden eyes* ...What do you want?",
    "*stares at you silently*",
    "I'm watching.",
    "*twitches ear* Go on...",
    "Bold of you to speak to me.",
]


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help(self, ctx):
        """Shows all available commands."""
        embed = discord.Embed(
            title="ClawdBot — Commands",
            description="*The golden eyes blink at you slowly.*",
            color=0xF5C518,
        )
        embed.set_thumbnail(url="attachment://avatar.png")
        embed.add_field(
            name="General",
            value=(
                "`!help` — Show this menu\n"
                "`!clawd` — Get a response from Clawd\n"
                "`!ping` — Check bot latency\n"
                "`!8ball <question>` — Ask the oracle\n"
                "`!roll <dice>` — Roll dice (e.g. `2d6`)"
            ),
            inline=False,
        )
        embed.set_footer(text="ClawdBot | Watching always.")
        await ctx.send(embed=embed)

    @commands.command(name="ping")
    async def ping(self, ctx):
        """Check bot latency."""
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"*blinks* Pong. `{latency}ms`")

    @commands.command(name="clawd")
    async def clawd(self, ctx):
        """Get a reaction from Clawd."""
        response = random.choice(CLAWD_RESPONSES)
        await ctx.send(response)

    @commands.command(name="8ball")
    async def eight_ball(self, ctx, *, question: str):
        """Ask the oracle a yes/no question."""
        answers = [
            "It is certain.",
            "Without a doubt.",
            "You may rely on it.",
            "Yes, definitely.",
            "Outlook good.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful.",
        ]
        embed = discord.Embed(color=0xF5C518)
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=random.choice(answers), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="roll")
    async def roll(self, ctx, dice: str = "1d6"):
        """Roll dice in NdN format (e.g. 2d6)."""
        import re

        match = re.fullmatch(r"(\d+)d(\d+)", dice.lower())
        if not match:
            await ctx.send("*tilts head* Use format like `2d6`.")
            return
        num, sides = int(match.group(1)), int(match.group(2))
        if num < 1 or num > 100 or sides < 2 or sides > 1000:
            await ctx.send("*narrows eyes* Keep it reasonable.")
            return
        rolls = [random.randint(1, sides) for _ in range(num)]
        total = sum(rolls)
        roll_str = ", ".join(str(r) for r in rolls)
        await ctx.send(f"Rolling `{dice}`: [{roll_str}] = **{total}**")


async def setup(bot):
    await bot.add_cog(General(bot))
