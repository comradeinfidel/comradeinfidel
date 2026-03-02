import discord
from discord.ext import commands


class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason given."):
        """Kick a member from the server."""
        await member.kick(reason=reason)
        await ctx.send(f"*watches {member.display_name} leave* Kicked. Reason: {reason}")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason given."):
        """Ban a member from the server."""
        await member.ban(reason=reason)
        await ctx.send(f"*golden eyes gleam* {member.display_name} has been banned. Reason: {reason}")

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, username: str):
        """Unban a user by username."""
        bans = [ban async for ban in ctx.guild.bans()]
        for ban_entry in bans:
            user = ban_entry.user
            if str(user) == username:
                await ctx.guild.unban(user)
                await ctx.send(f"*slow blink* {user} has been unbanned.")
                return
        await ctx.send(f"*tilts head* Couldn't find `{username}` in the ban list.")

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Delete a number of messages from the channel."""
        if amount < 1 or amount > 100:
            await ctx.send("*flicks ear* Choose between 1 and 100 messages.")
            return
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"*sweeps paw* Deleted {len(deleted) - 1} messages.")
        await msg.delete(delay=3)

    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        """Set slowmode for the current channel (0 to disable)."""
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send("*nods* Slowmode disabled.")
        else:
            await ctx.send(f"*nods* Slowmode set to {seconds}s.")


async def setup(bot):
    await bot.add_cog(Mod(bot))
