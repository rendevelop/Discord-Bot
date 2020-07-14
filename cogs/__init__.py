from discord.ext import commands
import discord
import datetime
import config
import asyncio
import re

# list of role permission required to run a certain command
cmd_role_permissions = {
    "ping": None,
    "announce": [467908458944004106, 467908507832942593, 467908276185726976, 467908604641411073],
    "submitbill": [467908717346816001]
}

class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_messages(self, message, embed, users):
        loop = asyncio.get_event_loop()

        for user in users:
            if user.dm_channel is None:
                await user.create_dm()

            asyncio.ensure_future(user.dm_channel.send(content=message, embed=embed), loop=loop)

    async def delete_messages(self, messages, delay):
        loop = asyncio.get_event_loop()
        for message in messages:
            asyncio.ensure_future(message.delete(delay=delay), loop=loop)

    async def hasPermission(ctx):
        if ctx.author.bot: # if is a bot, cannot run command
            return False

        if cmd_role_permissions[str(ctx.command)] is None: # if no permissions required, can run command
            return True

        # otherwise only those with the allowed roles can run command
        return any(ctx.message.guild.get_role(role_id) in ctx.author.roles for role_id in cmd_role_permissions[str(ctx.command)])
    
    @commands.command(name="ping", description=config.prefix+"ping")
    @commands.check(hasPermission)
    async def ping(self, ctx):
        await ctx.send("Pong! Responded within {0} ms!".format(self.bot.latency))
    
    @commands.command(name="announce", description=config.prefix+"announce <content>")
    @commands.check(hasPermission)
    async def announce(self, ctx):
        # message, channel and command details
        cmd = config.prefix + str(ctx.command)
        message = ctx.message.content[len(cmd)+1:]
        author = ctx.message.author
        channel = ctx.message.channel
        guild = ctx.message.guild

        # announcement channel, roles to dm, list of members, and command messages to be deleted
        announcements_channel_id = 467900156004663306
        announcements_channel = self.bot.get_channel(announcements_channel_id)
        roles = [467908717346816001]
        members = set()
        cmd_messages = [ctx.message]

        loop = asyncio.get_event_loop()

        # if there is no message, abort
        if len(message) < 1:
            bot_msg = await ctx.send("Too few arguments.")
            bot_msg.delete(delay=3)
            return
        
        # create a discord embed for the announcement
        embed = discord.Embed(
            title = "Announcement by `{0}`".format(ctx.message.author),
            description = message,
            timestamp = datetime.datetime.utcnow(),
            colour = discord.Colour.dark_gold()
        )
        embed.set_footer(text='Melty-Chan')

        # confirmation message
        bot_msg = await ctx.send(content="Are you sure? (Y/N)", embed=embed)
        cmd_messages.append(bot_msg)

        # check for whether message sent is in same channel and same author
        def check(message):
            return message.channel == channel and message.author == author

        confirmation = None

        try:
            confirmation = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            bot_msg = await ctx.send("Command cancelled.")
            bot_msg.delete(delay=3)
            return
        
        if confirmation != None:
            cmd_messages.append(confirmation)
            if confirmation.content.lower() == 'y':
                await announcements_channel.send("<@&{}>".format(roles[0]), embed=embed)

                # gather up the members and direct message them
                for role_id in roles:
                    role = guild.get_role(role_id)
                    members = members.union(role.members)
                
                asyncio.ensure_future(self.send_messages('', embed, members), loop=loop)

                bot_msg = await ctx.send("Announced!")
                cmd_messages.append(bot_msg)
            else:
                bot_msg = await ctx.send("Command cancelled.")
                bot_msg.delete(delay=3)
                return

        asyncio.ensure_future(self.delete_messages(cmd_messages, 3), loop=loop)

    @commands.command(name="submitbill", description=config.prefix+"submitbill <google drive link>")
    @commands.check(hasPermission)
    async def submitbill(self, ctx):
        # message, channel and command details
        cmd = config.prefix + str(ctx.command)
        message = ctx.message.content[len(cmd)+1:]
        author = ctx.message.author
        channel = ctx.message.channel
        guild = ctx.message.guild

        # roles to dm, list of members, and command messages to be deleted
        roles = [467908507832942593, 467908458944004106]
        members = set()
        cmd_messages = [ctx.message]

        # check if google drive link
        rgx = re.compile("(https?:\/\/(.+?\.)?drive.google\.com(\/[A-Za-z0-9\-\._~:\/\?#\[\]@!$&'\(\)\*\+,;\=]*)?)")

        if re.match(rgx, message) is None:
            bot_msg = await ctx.send("Must be Google Drive link. Command cancelled.")
            await bot_msg.delete(delay=3)
            return
        
        # gather up the members and direct message them
        for role_id in roles:
            role = guild.get_role(role_id)
            members = members.union(role.members)
        
        submission_msg = "Bill submitted by {0}:\n{1}".format(str(author), message)
        self.send_messages(submission_msg, None, members)

        bot_msg = await ctx.send("Submitted!")
        await bot_msg.delete(delay=3)
        

def setup(bot):
    bot.add_cog(Basic(bot))