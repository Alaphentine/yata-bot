"""
Copyright 2020 kivou.2000607@gmail.com

This file is part of yata-bot.

    yata is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    any later version.

    yata is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with yata-bot. If not, see <https://www.gnu.org/licenses/>.
"""
# import standard modules
import re
import aiohttp
import asyncio
import html
import traceback
import logging

# import discord modules
from discord.ext import commands
from discord.abc import PrivateChannel
from discord.utils import get
from discord.ext import tasks

# import bot functions and classes
from inc.yata_db import set_configuration
from inc.yata_db import get_faction_name
from inc.handy import *


class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dailyVerify.start()
        self.weeklyVerify.start()
        self.dailyCheck.start()
        self.weeklyCheck.start()

    def cog_unload(self):
        self.dailyVerify.cancel()
        self.weeklyVerify.cancel()
        self.weeklyCheck.cancel()
        self.dailyCheck.cancel()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Automatically verify member on join"""
        logging.info(f'[verify/on_member_join] {member.guild}: {member}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(member.guild, "verify")
        if not config:
            return

        # check if bot
        if member.bot:
            return

        # get key
        status, tornId, key = await self.bot.get_master_key(member.guild)
        if status == -1:
            return

        # verify member when he join
        role = self.bot.get_module_role(member.guild.roles, config.get("roles_verified", {}))
        if role is None:
            return
        message, success = await self._member(member, role, discordID=member.id, API_KEY=key, context=False)

        # send message to welcome channel
        channel = self.bot.get_module_channel(member.guild.channels, config.get("channels_welcome", {}))
        if channel is None:
            return
        await channel.send(f'```md\n# Verify\n {message}```')

        # if not Automatically verified send private message
        if not success and config.get("other", {}).get("force_verify", False):
            msg = [f'**Welcome to the {member.guild}\'s discord server {member} o/**']
            msg.append('This server requires that you verify your account in order to identify who you are in Torn.')
            msg.append('There is two ways to do that:')
            msg.append(f'1 - You can go to the official discord server and get verified there: https://torn.com/discord, then come back in the {member.guild} server and type `!verify` in a channel.')
            msg.append('You can also directly use this link if you don\'t want to join the official discord: https://discordapp.com/api/oauth2/authorize?client_id=441210177971159041&redirect_uri=https%3A%2F%2Fwww.torn.com%2Fdiscord.php&response_type=code&scope=identify')
            msg.append('2 - Or you can type **in this channel**: `!verifyKey YOURAPIKEY` *(the api key is 16 random letters that can be found here: https://www.torn.com/preferences.php#tab=api)*')
            msg.append(f'Either way, this process changes your nickname to your Torn name, gives you the {role} role and roles corresponding to your faction (depending on the server configuration).')
            msg.append(f'If you change your name or faction you can repeat this verification whenever you want.')

            await member.send('\n'.join(msg))

    @commands.command(aliases=["v"])
    @commands.bot_has_permissions(send_messages=True, manage_nicknames=True, manage_roles=True)
    @commands.guild_only()
    async def verify(self, ctx, *args):
        """Verify member based on discord ID"""
        logging.info(f'[verify/verify] {ctx.guild}: {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "verify")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
            return

        # get key
        status, tornId, key = await self.bot.get_master_key(ctx.guild)
        if status == -1:
            await ctx.send('```md\n# verify\n< error > No master key given```')
            return

        # Get Verified role
        role = self.bot.get_module_role(ctx.guild.roles, config.get("roles_verified", {}))
        if role is None:
            await ctx.send('```md\n# verify\n< error > No verified role given```')
            return

        if len(args) == 1:  # with one arg (torn id or discord mention)
            logging.debug(f'[verify/verify] {ctx.guild}: 1 argument {args}')

            if args[0].isdigit():
                userID = int(args[0])
                logging.debug(f'[verify/verify] {ctx.guild}: user ID {userID}')

                message, _ = await self._member(ctx, role, userID=userID, API_KEY=key)

            # check if arg is a mention of a discord user ID
            elif re.match(r'<@!?\d+>', args[0]):
                discordID = re.findall(r'\d+', args[0])

                if len(discordID) and discordID[0].isdigit():
                    logging.debug(f'[verify/verify] {ctx.guild}: discord ID {discordID[0]}')
                    message, _ = await self._member(ctx, role, discordID=discordID[0], API_KEY=key)
                else:
                    logging.debug(f'[verify/verify] {ctx.guild}: discord ID unreadable {discordID}')
                    message = f"< error > Could not find discord ID in mention {args[0]}... Either I'm stupid or somthing very wrong is going on."

            else:
                message = "< error > Use !verify tornId or !verify @Kivou [2000607]"

        else:  # no args
            message, _ = await self._member(ctx, role, API_KEY=key)

        await ctx.send(f'```md\n# Verify\n{message}```')

    # @commands.command(aliases=['addkey'])
    # async def verifyKey(self, ctx, key):
    #     """Verify member with API key"""
    #     if ctx.guild is None:
    #         logging.info(f'[verify/verifyKey] DM: {ctx.author}')
    #     else:
    #         logging.info(f'[verify/verifyKey] {ctx.guild}: {ctx.author.display_name} / {ctx.author}')
    #
    #     if not isinstance(ctx.channel, PrivateChannel):
    #         await ctx.message.delete()
    #         await ctx.send(f'{ctx.author.mention}, you have to type your API key in a private chat with me...')
    #         await ctx.author.send('Type your API key here!')
    #         return
    #
    #     url = "https://api.torn.com/user/?selections=profile&key={}".format(key)
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(url) as r:
    #             user = await r.json()
    #
    #     # deal with api error
    #     if "error" in user:
    #         await ctx.author.send(f'I\'m sorry but an error occured with your API key `{key}`: *{user["error"]["error"]}*')
    #         return
    #
    #     # loop over bot guilds and lookup of the discord user
    #     for guild in self.bot.guilds:
    #         # continue if author not in the guild
    #         if ctx.author not in guild.members:
    #             continue
    #
    #         await ctx.author.send(f'Verification for server **{guild}**')
    #
    #         # return if verify not active
    #         if not self.bot.check_module(guild, "verify"):
    #             await ctx.author.send(":x: Verify module not activated")
    #             continue
    #
    #         # get verified role
    #         role = get(guild.roles, name="Verified")
    #
    #         # get member of server from author id
    #         member = guild.get_member(ctx.author.id)
    #
    #         # skip verification if member not part of the guild
    #         if member is None:
    #             continue
    #
    #         # get config
    #         config = self.bot.get_config(guild)
    #
    #         # get verify channel and send message
    #         verify_channel = get(guild.channels, name=config["verify"].get("channels", ["verify-id"])[0])
    #
    #         # try to modify the nickname
    #         try:
    #             nickname = "{} [{}]".format(user["name"], user["player_id"])
    #             await member.edit(nick=nickname)
    #             await ctx.author.send(f':white_check_mark: Your name as been changed to {member.display_name}')
    #         except BaseException:
    #             await ctx.author.send(f'*I don\'t have the permission to change your nickname.*')
    #             # continue
    #
    #         # assign verified role
    #         try:
    #             await member.add_roles(role)
    #             await ctx.author.send(f':white_check_mark: You\'ve been assigned the role {role.name}')
    #         except BaseException as e:
    #             await ctx.author.send(f':x: Something went wrong when assigning you the {role} role ({hide_key(e)}).')
    #             continue
    #
    #         # Set Faction role
    #         fId = str(user['faction']['faction_id'])
    #         if fId in config["factions"]:
    #             faction_name = f'{config["factions"][fId]} [{fId}]' if config["verify"].get("id", False) else f'{config["factions"][fId]}'
    #         else:
    #             faction_name = "{faction_name} [{faction_id}]".format(**user["faction"]) if config["verify"].get("id", False) else "{faction_name}".format(**user["faction"])
    #
    #         faction_role = get(guild.roles, name=faction_name)
    #         if faction_role is not None:
    #             # add faction role if role exists
    #             await member.add_roles(faction_role)
    #             await ctx.author.send(f':white_check_mark: You\'ve been assigned the role {faction_role}')
    #             # add a common faction role
    #             common_role = get(guild.roles, name=config["verify"].get("common"))
    #             if common_role is not None and str(user['faction']['faction_id']) in config.get("factions"):
    #                 await member.add_roles(common_role)
    #                 if verify_channel is not None:
    #                     await verify_channel.send(f":white_check_mark: **{member}**, has been verified and is now known as **{member.display_name}** from *{faction_name}* which is part of *{common_role}*. o7")
    #                 await ctx.author.send(f':white_check_mark: You\'ve been assigned the role {common_role}')
    #             else:
    #                 if verify_channel is not None:
    #                     await verify_channel.send(f":white_check_mark: **{member}**, has been verified and is now known as **{member.display_name}** from *{faction_name}*. o7")
    #         else:
    #             if verify_channel is not None:
    #                 await verify_channel.send(f":white_check_mark: **{member}**, has been verified and is now known as **{member.display_name}**. o/")
    #             await ctx.author.send(f':grey_question: You haven\'t been assigned any faction role. If you think you should, ask the owner of this server if it\'s normal.')
    #
    #         # final message to member
    #         await ctx.author.send(f':white_check_mark: All good for me!\n**Welcome to {guild}** o/')

    @commands.command(aliases=["verifyall"])
    @commands.bot_has_permissions(send_messages=True, manage_nicknames=True, manage_roles=True)
    @commands.guild_only()
    async def verifyAll(self, ctx, *args):
        """Verify all members based on discord ID"""
        logging.info(f'[verify/verifyAll] {ctx.guild}: {ctx.author} / {ctx.channel}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "verify")
        if not config:
            return

        # check if admin channel
        if not await self.bot.check_channel_admin(ctx):
            return

        force = True if len(args) and args[0] == "force" else False

        await self._loop_verify(ctx.guild, ctx.channel, ctx=ctx, force=force)

    @commands.command(aliases=["checkfactions"])
    @commands.bot_has_permissions(send_messages=True, manage_nicknames=True, manage_roles=True)
    @commands.guild_only()
    async def checkFactions(self, ctx, *args):
        """ Check faction role of members"""
        logging.info(f'[verify/checkFactions] {ctx.guild}: {ctx.author.display_name} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "verify")
        if not config:
            return

        # check if admin channel
        if not await self.bot.check_channel_admin(ctx):
            return

        force = True if len(args) and args[0] == "force" else False

        await self._loop_check(ctx.guild, ctx.channel, ctx=ctx, force=force)

    async def _member(self, ctx, verified_role, userID=None, discordID=None, API_KEY="", context=True):
        """ Verifies one member
            Returns what the bot should say
        """
        try:

            # WARNING: ctx is most of the time a discord context
            # But when using this function inside on_member_join ctx is a discord member
            # Thus ctx.author will fail in this case

            # WARNING: if discordID corresponds to a userID it will be considered as a user ID

            # cast userID and discordID into int if not none
            discordID = int(discordID) if str(discordID).isdigit() else None
            userID = int(userID) if str(userID).isdigit() else None

            # check userID and discordID > 0 otherwise api call will be on the key owner
            if discordID is not None:
                discordID = None if discordID < 1 else discordID

            if userID is not None:
                userID = None if userID < 1 else userID

            # works for both ctx as a context and as a member
            guild = ctx.guild

            # get configuration
            config = self.bot.get_guild_configuration_by_module(ctx.guild, "verify")
            if not config:
                return

            # boolean that check if the member is verifying himself with no id given
            author_verif = userID is None and discordID is None
            # logging.debug(f"[verify/_member] author_verif {author_verif}")
            # case no userID and no discordID is given (author verify itself)
            if author_verif:
                author = ctx.author
                url = f"https://api.torn.com/user/{author.id}?selections=discord&key={API_KEY}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as r:
                        try:
                            req = await r.json()
                        except BaseException:
                            req = {'error': {'error': 'API is talking shit... #blameched', 'code': -1}}

                if not isinstance(req, dict):
                    req = {'error': {'error': 'API is talking shit... #blameched', 'code': -1}}

                if 'error' in req:
                    return "< error > There is an API key problem ({}).".format(req['error']['error']), False
                userID = req['discord'].get("userID")
                if userID == '':
                    return f"{author}, you are not officially verified by Torn", False

            # case discordID is given
            # if discordID is not None and userID is None:  # use this condition to skip API call if userID is given
            if discordID is not None:  # use this condition to force API call to check userID even if it is given
                url = f"https://api.torn.com/user/{discordID}?selections=discord&key={API_KEY}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as r:
                        try:
                            req = await r.json()
                        except BaseException:
                            req = {'error': {'error': 'API is talking shit... #blameched', 'code': -1}}

                if not isinstance(req, dict):
                    req = {'error': {'error': 'API is talking shit... #blameched', 'code': -1}}

                if 'error' in req:
                    return ":x: There is an API key problem ({}).".format(req['error']['error']), False
                if req['discord'].get("userID") == '':
                    return f"{guild.get_member(discordID)} is not officially verified by Torn", False
                else:
                    userID = int(req['discord'].get("userID"))

            logging.info(f"[verify/_member] verifying userID = {userID}")

            # api call request
            url = f"https://api.torn.com/user/{userID}?selections=profile,discord&key={API_KEY}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    try:
                        req = await r.json()
                    except BaseException:
                        req = {'error': {'error': 'API is talking shit... #blameched', 'code': -1}}

            if not isinstance(req, dict):
                req = {'error': {'error': 'API is talking shit... #blameched', 'code': -1}}

            # check api error
            if 'error' in req:
                if int(req['error']['code']) == 6:
                    return f"< error > Torn ID {userID} is not known. Please check again.", False
                else:
                    return "< error > There is a API key problem ({}).".format(req['error']['error']), False

            # check != id shouldn't append or problem in torn API
            dis = req.get("discord")
            if int(dis.get("userID")) != userID:
                return "< error >  That's odd... {} != {}.".format(userID, dis.get("userID")), False

            # check if registered in torn discord
            discordID = None if dis.get("discordID") in [''] else int(dis.get("discordID"))
            name = req.get("name", "???")
            nickname = f"{name} [{userID}]"

            if discordID is None:
                # the guy did not log into torn discord
                return f"{nickname} is not officially verified by Torn", False

            # the guy already log in torn discord
            if author_verif:
                author = ctx.author
                try:
                    await author.edit(nick=nickname)
                except BaseException:
                    if context:
                        # only send this message if ctx is a context (context=True)
                        # await ctx.send(f":no_entry: I don't have the permission to change your nickname.")
                        pass
                await author.add_roles(verified_role)

                # Get faction roles
                fId = str(req['faction']['faction_id'])
                fNa = str(req['faction']['faction_name'])
                faction_roles_id = config.get("factions", {}).get(fId, {})
                faction_roles = [_ for _ in self.bot.get_module_role(ctx.guild.roles, faction_roles_id, all=True) if _ is not None]

                roles_list = [f'@{html.unescape(verified_role.name)}']
                for faction_role in faction_roles:
                    # add faction role if role exists
                    await author.add_roles(faction_role)
                    roles_list.append(f'@{html.unescape(faction_role.name)}')

                if fId in config.get("factions", {}) and fId in config.get("positions", {}):
                    try:
                        position_name = f'{html.unescape(req.get("faction", {}).get("position"))} of {html.unescape(fNa)}'
                        position_role = get(ctx.guild.roles, name=position_name)
                        if position_role is None:
                            position_role = await ctx.guild.create_role(name=position_name)
                            position_role = get(ctx.guild.roles, name=position_name)
                        for r in [r for r in author.roles if " of " in r.name and r.name.split(" of ")[-1] == html.unescape(fNa)]:
                            await author.remove_roles(r)
                        await author.add_roles(position_role)
                        roles_list.append(f'@{html.unescape(position_role.name)}')
                    except BaseException as e:
                        logging.error(f'[verify/_member] {guild} [{guild.id}]: positions {hide_key(e)}')

                nl = '\n- '
                return f'< {author} >\nYou have been verified and are now known as < {author.display_name} >. You have been given the role{"s" if len(roles_list)>1 else ""}:{nl}{nl.join(roles_list)}', True

            else:
                # loop over all members to check if the id exists
                for member in ctx.guild.members:
                    if int(member.id) == discordID:
                        try:
                            await member.edit(nick=nickname)
                        except BaseException:
                            if context:
                                # only send this message if ctx is a context (context=True)
                                # await ctx.send(f":no_entry: I don't have the permission to change {member.display_name}'s nickname.")
                                pass
                        await member.add_roles(verified_role)

                        # Get faction roles
                        fId = str(req['faction']['faction_id'])
                        fNa = str(req['faction']['faction_name'])
                        faction_roles_id = config.get("factions", {}).get(fId, {})
                        faction_roles = [_ for _ in self.bot.get_module_role(ctx.guild.roles, faction_roles_id, all=True) if _ is not None]

                        roles_list = [f'@{verified_role}']
                        for faction_role in faction_roles:
                            # add faction role if role exists
                            await member.add_roles(faction_role)
                            roles_list.append(f'@{faction_role}')

                        if fId in config.get("factions", {}) and fId in config.get("positions", {}):
                            try:
                                position_name = f'{html.unescape(req.get("faction", {}).get("position"))} of {html.unescape(fNa)}'
                                position_role = get(ctx.guild.roles, name=position_name)
                                if position_role is None:
                                    position_role = await ctx.guild.create_role(name=position_name)
                                    position_role = get(ctx.guild.roles, name=position_name)
                                for r in [r for r in member.roles if " of " in r.name and r.name.split(" of ")[-1] == html.unescape(fNa)]:
                                    await member.remove_roles(r)
                                await member.add_roles(position_role)
                                roles_list.append(f'@{html.unescape(position_role.name)}')
                            except BaseException as e:
                                logging.error(f'[verify/_member] {guild} [{guild.id}]: positions {hide_key(e)}')

                        nl = '\n- '
                        return f'< {member} >\nThey have been verified and are now known as < {member.display_name} >. They have been given the role{"s" if len(roles_list)>1 else ""}:{nl}{nl.join(roles_list)}', True

                # if no match in this loop it means that the member is not in this server
                return f"You are trying to verify < {nickname} > but they didn't join this server... Maybe they are using a different discord account on the official Torn discord server.", False

        except BaseException as e:
            logging.error(f'[verify/_member] {guild} [{guild.id}]: {hide_key(e)}')
            return f"< error > while doing the verification: {hide_key(e)}", False

        return "< error > Weird... I didn't do anything...", False

    async def _loop_verify(self, guild, channel, ctx=False, force=False):

        # get configuration
        config = self.bot.get_guild_configuration_by_module(guild, "verify")
        if not config:
            return

        # get key
        status, tornId, key = await self.bot.get_master_key(guild)
        if status == -1:
            await channel.send(f'```md\n# Verifying all members of {guild}\n< Force > {force}\n< error > no master key```')
            return

        # Get Verified role
        role = self.bot.get_module_role(guild.roles, config.get("roles_verified", {}))
        if role is None:
            await channel.send(f'```md\n# Verifying all members of {guild}\n< Force > {force}\n< error > no verified roles set```')
            return

        await channel.send(f'```md\n# Verifying all members of {guild}\n< Force > {force}\n< Verified role > @{role}```')

        # loop over members
        members = guild.members
        for i, member in enumerate(members):
            if member.bot:
                continue

            if force:
                if ctx:
                    message, _ = await self._member(ctx, role, discordID=member.id, API_KEY=key)
                else:
                    message, _ = await self._member(member, role, discordID=member.id, API_KEY=key, context=False)

                if not _:
                    await channel.send(f"```md\n< {i+1:03d}/{len(members):03d} > {member.display_name}: {message}```")
                continue

            elif role in member.roles:
                pass
            else:
                if ctx:
                    message, _ = await self._member(ctx, role, discordID=member.id, API_KEY=key)
                else:
                    message, _ = await self._member(member, role, discordID=member.id, API_KEY=key, context=False)

                await channel.send(f"```md\n< {i+1:03d}/{len(members):03d} > {message}```")

        await channel.send(f"```md\n# done verifying```")

    async def _loop_check(self, guild, channel, ctx=False, force=False):

        # get configuration
        config = self.bot.get_guild_configuration_by_module(guild, "verify")
        if not config:
            return

        # get verified role
        vrole = self.bot.get_module_role(guild.roles, config.get("roles_verified", {}))

        # get unique faction_roles
        all_faction_roles = [id for faction_id, faction_roles_id in config.get("factions", {}).items() for id in faction_roles_id]

        # loop over factions
        for faction_id, faction_roles_id in config.get("factions", {}).items():

            # Get faction roles
            faction_roles = [_ for _ in self.bot.get_module_role(guild.roles, faction_roles_id, all=True) if _ is not None]
            faction_roles_unique = [_ for _ in faction_roles if all_faction_roles.count(str(_.id)) == 1]
            roles_list = ", ".join([f'@{html.unescape(faction_role.name)}' for faction_role in faction_roles])
            faction_name = await get_faction_name(faction_id)

            if not len(faction_roles_unique):
                await channel.send(f'```md\n# Checking {faction_name}\n< Force > {force}\n< Roles > {roles_list}\n< error > None of the following roles are unique```')
                continue

            await channel.send(f'```md\n# Checking {faction_name}\n< Force > {force}\n< Roles > {roles_list}\n< Unique role > @{html.unescape(faction_roles_unique[0].name)}```')

            # api call with members list from torn
            status, tornIdForKey, key = await self.bot.get_master_key(guild)
            if status == -1:
                msg = "No master key given"
                await channel.send(f"```md\n< error >{msg}```")
                continue

            url = f'https://api.torn.com/faction/{faction_id}?selections=basic&key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    try:
                        req = await r.json()
                    except BaseException:
                        req = {'error': {'error': 'API is talking shit... #blameched', 'code': -1}}

            if not isinstance(req, dict):
                req = {'error': {'error': 'API is talking shit... #blameched', 'code': -1}}

            # deal with api error
            if "error" in req:
                msg = f'API key error for master key [{tornIdForKey}]: *{req["error"]["error"]}*'
                await channel.send(f"```md\n< error >{msg}```")
                return

            members_torn = req.get("members", dict({}))

            # loop over the members with this role
            members_with_role = [m for m in guild.members if faction_roles_unique[0] in m.roles]
            for i, m in enumerate(members_with_role):
                if m.bot:
                    continue

                # try to parse Torn user ID
                regex = re.findall(r'\[(\d{1,7})\]', m.display_name)
                if len(regex) == 1 and regex[0].isdigit():
                    tornId = int(regex[0])
                else:
                    await channel.send(f"```md\n< {i+1:03d}/{len(members_with_role):03d} > {m.display_name} could not find torn ID within their display name (not checking them)```")
                    continue

                # check if member still in faction
                if str(tornId) in members_torn:
                    # await channel.send(f":white_check_mark: `{m.display_name} still in {faction_role.name}`")
                    continue
                else:
                    if force:
                        for faction_role in faction_roles:
                            await m.remove_roles(faction_role)

                        await channel.send(f'```md\n< {i+1:03d}/{len(members_with_role):03d} > {m.display_name} is not part of {html.unescape(faction_name)} anymore: role{"s" if len(faction_roles)>1 else ""} {roles_list} has been removed```')

                        # verify him again see if he has a new faction on the server
                        if ctx:
                            message, success = await self._member(ctx, vrole, discordID=m.id, API_KEY=key)
                        else:
                            message, success = await self._member(m, vrole, discordID=m.id, API_KEY=key, context=False)
                        await channel.send(f'```md\n< {i+1:03d}/{len(members_with_role):03d} > {message}```')

                    else:
                        await channel.send(f'```md\n< {i+1:03d}/{len(members_with_role):03d} > {m.display_name} is not part of {html.unescape(faction_name)} anymore: role{"s" if len(faction_roles)>1 else ""} {roles_list} has been removed```')

        await channel.send(f"```md\n# done checking```")

    @tasks.loop(hours=1)
    async def dailyVerify(self):
        logging.debug("[verify/dailyVerify] start task")

        # iteration over all guilds
        async for guild in self.bot.fetch_guilds(limit=250):
            try:
                # get configuration
                config = self.bot.get_guild_configuration_by_module(guild, "verify")
                if not config:
                    continue

                # ignore servers with no option daily check
                if not config.get("other", {}).get("daily_verify", False):
                    continue

                try:
                    last_update = int(config["other"]["daily_verify"])
                except BaseException as e:
                    logging.error(f'[verify/dailyVerify] Failed to cast last update into int guild {guild}: {config["other"]["daily_verify"]}')
                    last_update = 1
                if ts_now() - last_update < 24 * 3600:
                    continue

                # update time
                config["other"]["daily_verify"] = ts_now()
                self.bot.configurations[guild.id]["verify"] = config
                await set_configuration(self.bot.bot_id, guild.id, guild.name, self.bot.configurations[guild.id])

                # get full guild (async iterator doesn't return channels)
                guild = self.bot.get_guild(guild.id)
                logging.debug(f"[verify/dailyVerify] verifying all {guild}: start")
                # get channel
                channel = self.bot.get_guild_admin_channel(guild)
                if channel is None:
                    logging.debug(f"[verify/dailyVerify] {guild}: no admin channel found")
                    continue
                await channel.send("```md\nDaily verification of your members < START >```")
                await self._loop_verify(guild, channel, force=True)
                await channel.send("```md\nDaily verification of your members < DONE >```")
                logging.debug(f"[verify/dailyVerify] verifying all {guild}: end")

            except BaseException as e:
                logging.error(f'[verify/dailyVerify] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(e, guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on daily verify"}
                await self.bot.send_log_main(e, headers=headers, full=True)

        logging.debug("[verify/dailyVerify] end task")

    @tasks.loop(hours=1)
    async def weeklyVerify(self):
        logging.debug("[verify/weeklyVerify] start task")

        # iteration over all guilds
        async for guild in self.bot.fetch_guilds(limit=250):
            try:
                # get configuration
                config = self.bot.get_guild_configuration_by_module(guild, "verify")
                if not config:
                    continue

                # ignore servers with no option weekly check
                if not config.get("other", {}).get("weekly_verify", False):
                    continue

                try:
                    last_update = int(config["other"]["weekly_verify"])
                except BaseException as e:
                    logging.error(f'[verify/weeklyVerify] Failed to cast last update into int guild {guild}: {config["other"]["weekly_verify"]}')
                    last_update = 1
                if ts_now() - last_update < 7 * 24 * 3600:
                    continue

                # update time
                config["other"]["weekly_verify"] = ts_now()
                self.bot.configurations[guild.id]["verify"] = config
                await set_configuration(self.bot.bot_id, guild.id, guild.name, self.bot.configurations[guild.id])

                # get full guild (async iterator doesn't return channels)
                guild = self.bot.get_guild(guild.id)
                logging.debug(f"[verify/weeklyVerify] verifying all {guild}: start")
                # get channel
                channel = self.bot.get_guild_admin_channel(guild)
                if channel is None:
                    continue
                await channel.send("```md\nWeekly verification of your members < START >```")
                await self._loop_verify(guild, channel, force=True)
                await channel.send("```md\nWeekly verification of your members < DONE >```")
                logging.debug(f"[verify/weeklyVerify] verifying all {guild}: end")

            except BaseException as e:
                logging.error(f'[verify/weeklyVerify] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(e, guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on weekly verify"}
                await self.bot.send_log_main(e, headers=headers, full=True)

        logging.debug("[verify/weeklyVerify] end task")

    @tasks.loop(hours=1)
    async def dailyCheck(self):
        logging.debug("[verify/dailyCheck] start task")

        # iteration over all guilds
        async for guild in self.bot.fetch_guilds(limit=250):
            try:
                # get configuration
                config = self.bot.get_guild_configuration_by_module(guild, "verify")
                if not config:
                    continue

                # ignore servers with no option daily check
                if not config.get("other", {}).get("daily_check", False):
                    continue

                try:
                    last_update = int(config["other"]["daily_check"])
                except BaseException as e:
                    logging.error(f'[verify/dailyCheck] Failed to cast last update into int guild {guild}: {config["other"]["daily_check"]}')
                    last_update = 1
                if ts_now() - last_update < 24 * 3600:
                    continue

                # update time
                config["other"]["daily_check"] = ts_now()
                self.bot.configurations[guild.id]["verify"] = config
                await set_configuration(self.bot.bot_id, guild.id, guild.name, self.bot.configurations[guild.id])

                # get full guild (async iterator doesn't return channels)
                guild = self.bot.get_guild(guild.id)
                logging.debug(f"[check/dailyCheck] checking all {guild}: start")
                # get channel
                channel = self.bot.get_guild_admin_channel(guild)
                if channel is None:
                    continue
                await channel.send("```md\nDaily check of your factions members < START >```")
                await self._loop_check(guild, channel, force=True)
                await channel.send("```md\nDaily check of your factions members < DONE >```")
                logging.debug(f"[check/dailyCheck] checking all {guild}: end")

            except BaseException as e:
                logging.error(f'[check/dailyCheck] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(e, guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on daily check"}
                await self.bot.send_log_main(e, headers=headers, full=True)

        logging.debug("[verify/dailyCheck] end task")

    @tasks.loop(hours=1)
    async def weeklyCheck(self):
        logging.debug("[verify/weeklyCheck] start task")

        # iteration over all guilds
        async for guild in self.bot.fetch_guilds(limit=250):
            try:
                # get configuration
                config = self.bot.get_guild_configuration_by_module(guild, "verify")
                if not config:
                    continue

                # ignore servers with no option weekly check
                if not config.get("other", {}).get("weekly_check", False):
                    continue

                try:
                    last_update = int(config["other"]["weekly_check"])
                except BaseException as e:
                    logging.error(f'[verify/weeklyCheck] Failed to cast last update into int guild {guild}: {config["other"]["weekly_check"]}')
                    last_update = 1
                if ts_now() - last_update < 7 * 24 * 3600:
                    continue

                # update time
                config["other"]["weekly_check"] = ts_now()
                self.bot.configurations[guild.id]["verify"] = config
                await set_configuration(self.bot.bot_id, guild.id, guild.name, self.bot.configurations[guild.id])

                # get full guild (async iterator doesn't return channels)
                guild = self.bot.get_guild(guild.id)
                logging.debug(f"[check/weeklyCheck] checking all {guild}: start")
                # get channel
                channel = self.bot.get_guild_admin_channel(guild)
                if channel is None:
                    continue
                await channel.send("```md\nWeekly check of your factions members < START >```")
                await self._loop_check(guild, channel, force=True)
                await channel.send("```md\nWeekly check of your factions members < DONE >```")
                logging.debug(f"[check/weeklyCheck] checking all {guild}: end")

            except BaseException as e:
                logging.error(f'[check/weeklyCheck] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(e, guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on weekly check"}
                await self.bot.send_log_main(e, headers=headers, full=True)

        logging.debug("[verify/weeklyCheck] end task")

    @dailyVerify.before_loop
    async def before_dailyVerify(self):
        await self.bot.wait_until_ready()

    @weeklyVerify.before_loop
    async def before_weeklyVerify(self):
        await self.bot.wait_until_ready()

    @dailyCheck.before_loop
    async def before_dailyCheck(self):
        await self.bot.wait_until_ready()

    @weeklyCheck.before_loop
    async def before_weeklyCheck(self):
        await self.bot.wait_until_ready()
