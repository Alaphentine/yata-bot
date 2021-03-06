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
import aiohttp
import asyncio
import asyncpg
import json
import re
import os
import html
import logging

# import discord modules
import discord
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get

# import bot functions and classes
from inc.yata_db import reset_notifications
from inc.handy import *


class API(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if self.bot.bot_id == 3:
            self.notify.start()

    def cog_unload(self):
        self.notify.cancel()

    @commands.command(aliases=['we'])
    @commands.guild_only()
    async def weaponexp(self, ctx, *args):
        """DM weaponexp to author"""
        logging.info(f'[api/weaponexp] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        await ctx.message.delete()

        # get user key
        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            return

        # make api call
        url = f"https://api.torn.com/user/?selections=discord,weaponexp&key={key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if "error" in req:
            await ctx.author.send(f'```md\n# {name} [{id}]: weapon experience\n< error > {req["error"]["error"]}```')
            return

        # if no weapon exp
        if not len(req.get("weaponexp", [])):
            await ctx.author.send(f"```md\n# {name} [{id}]: weapon experience\n< error > no weapon exp```")
            return

        # send list
        maxed = []
        tomax = []
        for w in req.get("weaponexp", []):
            if w["exp"] == 100:
                maxed.append(w)
            elif w["exp"] > 4:
                tomax.append(w)

        lst = [f"# {name} [{id}]: weapon experience and remaining hits\n"]

        if len(maxed):
            lst.append("# weapon maxed")

        # convert exp to hits remainings
        def exp_to_hits(exp):
            if exp < 25:
                return (25 - exp) * 8 + 1800
            elif exp < 50:
                return (50 - exp) * 12 + 1500
            elif exp < 75:
                return (75 - exp) * 20 + 1000
            else:
                return (100 - exp) * 40

        n = 1
        for w in maxed:
            lst.append(f'< {n: >2} > {w["name"]}: {w["exp"]}%')
            n += 1

        if len(tomax):
            lst.append("# experience > 5%")

        for w in tomax:
            lst.append(f'< {n: >2} > {w["name"]}: {w["exp"]}% ({exp_to_hits(int(w["exp"]))} hits)')
            n += 1

        await send_tt(ctx.author, lst)
        return

    @commands.command(aliases=['fh'])
    @commands.guild_only()
    async def finishing(self, ctx, *args):
        """DM number of finishing hits to author"""
        logging.info(f'[api/finishing] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        await ctx.message.delete()

        # get user key
        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            return

        # make api call
        url = f"https://api.torn.com/user/?selections=discord,personalstats&key={key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if "error" in req:
            await ctx.author.send(f'```md\n# {name} [{id}]: finishing hits\n< error > {req["error"]["error"]}```')
            return

        bridge = {"heahits": "Heavy artillery",
                  "chahits": "Mechanical guns",
                  "axehits": "Clubbin weapons",
                  "grehits": "Temporary weapons",
                  "machits": "Machine guns",
                  "pishits": "Pistols",
                  "rifhits": "Rifles",
                  "shohits": "Shotguns",
                  "smghits": "Sub machin guns",
                  "piehits": "Piercing weapons",
                  "slahits": "Slashing weapons",
                  "h2hhits": "Hand to hand"}

        finishingHits = []
        for k, v in bridge.items():
            finishingHits.append([v, req.get("personalstats", dict({})).get(k, 0)])

        lst = [f"# {name} [{id}]: finishing hits\n"]
        # send list
        for fh in sorted(finishingHits, key=lambda x: -x[1]):
            lst.append(f"< {fh[0]: <17} > {fh[1]: >6,d}")

        await send_tt(ctx.author, lst)
        return

    @commands.command(aliases=['net'])
    @commands.guild_only()
    async def networth(self, ctx, *args):
        """DM your networth breakdown (in case you're flying)"""
        logging.info(f'[api/networth] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        await ctx.message.delete()

        # get user key
        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            return

        # make api call
        url = f"https://api.torn.com/user/?selections=discord,networth&key={key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if "error" in req:
            await ctx.author.send(f'```md\n# {name} [{id}]: networth breakdown\n< error > {req["error"]["error"]}```')
            return

        # send list
        lst = [f"# {name} [{id}]: Networth breakdown\n"]
        for k, v in req.get("networth", dict({})).items():
            if k in ['total']:
                lst += ['', '---', '']
            if int(v):
                a = f"{k}"
                b = f"${v:,.0f}"
                lst.append(f'< {a: <13} > {b: >16}')

        await send_tt(ctx.author, lst)
        return

    @commands.command(aliases=['profile', 'p'])
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def who(self, ctx, *args):
        """Gives information on a user"""
        logging.info(f'[api/who] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # init variables
        helpMsg = f":x: You have to mention a member `!who @Kivou [2000607]` or enter a Torn ID or `!who 2000607`."

        logging.debug(f'[api/who] args: {args}')

        # send error message if no arg (return)
        if not len(args):
            logging.debug(f'[api/who] no args given')
            await ctx.send(helpMsg)
            return

        # check if arg is int
        elif args[0].isdigit():
            logging.debug(f'[api/who] 1 int given -> torn user')
            tornId = int(args[0])

        # check if arg is a mention of a discord user ID
        elif re.match(r'<@!?\d+>', args[0]):
            discordId = re.findall(r'\d+', args[0])
            logging.debug(f'[api/who] 1 mention given -> discord member')

            if len(discordId) and discordId[0].isdigit():
                member = ctx.guild.get_member(int(discordId[0]))
            else:
                await ctx.send(helpMsg)
                return

            # check if member
            if member is None:
                await ctx.send(f"```md\n# who\nCouldn't find discord member: {discordId}. Try !who < torn ID >```")
                return

            # try to parse Torn user ID
            regex = re.findall(r'\[(\d{1,7})\]', member.display_name)
            if len(regex) == 1 and regex[0].isdigit():
                tornId = int(regex[0])
            else:
                status, tornId, _, _ = await self.bot.get_user_key(ctx, member, needPerm=False)
                if status in [-1, -2, -3]:
                    await ctx.send(f"```md\n# who\nCould not find Torn ID within their display name and verification failed. Try !who < Torn ID >```")
                    return

        # other cases I didn't think of
        else:
            await ctx.send(helpMsg)
            return

        # at this point tornId should be a interger corresponding to a torn ID

        # get configuration for guild
        # status, _, key = await self.bot.get_master_key(ctx.guild)
        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            await ctx.send("```md\n# who\n< error > key not found```")
            return

        # Torn API call
        url = f'https://api.torn.com/user/{tornId}?selections=profile,personalstats&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                r = await r.json()

        if 'error' in r:
            await ctx.send(f'Error code {r["error"]["code"]}: {r["error"]["error"]}')
            await ctx.send(f'Check the profile by yourself https://www.torn.com/profiles.php?XID={tornId}')
            return

        links = {}
        linki = 1
        lst = []

        # status
        lst.append(f'< Name > {r["name"]} [{r["player_id"]}]    <{linki}>')
        links[linki] = f'https://www.torn.com/profiles.php?XID={tornId}'
        linki += 1
        lst.append(f'< Action > {r["last_action"]["relative"]} ({r["last_action"]["status"]})')
        s = r["status"]
        # lst.append(f'State: {s["state"]}')
        lst.append(f'< Status > {s["description"]}')
        if s["details"]:
            lst.append(f'< Details > {cleanhtml(s["details"])}')
        p = 100 * r['life']['current'] // r['life']['maximum']
        i = int(p * 20 / 100)
        lst.append(f'< Life > {r["life"]["current"]:,d}/{r["life"]["maximum"]:,d} [{"+" * i}{"-" * (20 - i)}]')
        lst += ['', '---', '']

        # levels
        lst.append(f'< Level > {r["level"]}')
        lst.append(f'< Rank > {r["rank"]}')
        lst.append(f'< Age > {r["age"]:,d} days old')
        lst.append(f'< Networth > ${r["personalstats"].get("networth", 0):,d}')
        lst.append(f'< X-R-SE > {r["personalstats"].get("xantaken", 0):,d} {r["personalstats"].get("refills", 0):,d} {r["personalstats"].get("statenhancersused", 0):,d}')
        lst += ['', '---', '']

        # faction
        if int(r["faction"]["faction_id"]):
            f = r["faction"]
            lst.append(f'< Faction > {f["position"]} of {html.unescape(f["faction_name"])} [{f["faction_id"]}]    <{linki}>')
            links[linki] = f'https://www.torn.com/factions.php?&step=profile&ID={f["faction_id"]}'
            linki += 1
            lst.append(f'< Days > In faction since {f["days_in_faction"]} days')
            lst += ['', '---', '']

        # company
        if int(r["job"]["company_id"]):
            j = r["job"]
            lst.append(f'< Company > {html.unescape(j["company_name"])} [{j["company_id"]}]    <{linki}>')
            lst.append(f'< Position > {j["position"]}')
            links[linki] = f'https://www.torn.com/joblist.php?#!p=corpinfo&ID={j["company_id"]}'
            linki += 1
            lst += ['', '---', '']

        # social
        lst.append(f'< Friends > {r["friends"]:,d}')
        lst.append(f'< Enemies > {r["enemies"]:,d}')
        if r["forum_posts"]:
            lst.append(f'< Karma > {r["karma"]:,d} ({100 * r["karma"] // r["forum_posts"]}%)')
        else:
            lst.append(f'< Karma > No forum post')

        s = r["married"]
        if s["spouse_id"]:
            lst.append(f'< Married > {s["spouse_name"]} [{s["spouse_id"]}] for {s["duration"]:,d} days    <{linki}>')
            links[linki] = f'https://www.torn.com/profiles.php?&XID={s["spouse_id"]}'
            linki += 1

        await send_tt(ctx, lst)
        for k, v in links.items():
            await ctx.send(f'<{k}> {v}')

    @tasks.loop(minutes=1)
    async def notify(self):
        logging.debug("[api/notifications] start task")

        # main guild
        guild = get(self.bot.guilds, id=self.bot.main_server_id)

        # connect to YATA database of notifiers
        db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
        dbname = db_cred["dbname"]
        del db_cred["dbname"]
        sql = 'SELECT "tId", "dId", "notifications", "value" FROM player_view_player_key WHERE "activateNotifications" = True;'
        con = await asyncpg.connect(database=dbname, **db_cred)

        # async loop over notifiers
        async with con.transaction():
            async for record in con.cursor(sql, prefetch=100, timeout=2):
                # get corresponding discord member
                member = get(guild.members, id=record["dId"])
                if member is None:
                    logging.warning(f'[api/notifications] reset notifications for discord [{record["dId"]}] torn [{record["tId"]}]')
                    # headers = {"error": "notifications", "discord": record["dId"], "torn": record["tId"]}
                    # await self.bot.send_log_main("member not found", headers=headers)
                    await reset_notifications(record["tId"])
                    continue

                try:

                    # get notifications preferences
                    logging.debug(f'[api/notifications] {member.nick} / {member}')
                    notifications = json.loads(record["notifications"])

                    # get selections for Torn API call
                    keys = []
                    if "event" in notifications:
                        keys.append("events")
                        keys.append("notifications")
                    if "message" in notifications:
                        keys.append("messages")
                        keys.append("notifications")
                    if "award" in notifications:
                        keys.append("notifications")
                    if "energy" in notifications:
                        keys.append("bars")
                    if "nerve" in notifications:
                        keys.append("bars")
                    if "chain" in notifications:
                        keys.append("bars")
                    if "education" in notifications:
                        keys.append("education")
                    if "bank" in notifications:
                        keys.append("money")
                    if "drug" in notifications:
                        keys.append("cooldowns")
                    if "medical" in notifications:
                        keys.append("cooldowns")
                    if "booster" in notifications:
                        keys.append("cooldowns")
                    if "travel" in notifications:
                        keys.append("travel")

                    # make Torn API call
                    url = f'https://api.torn.com/user/?selections={",".join(list(set(keys)))}&key={record["value"]}'
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as r:
                            req = await r.json()

                    if 'error' in req:
                        logging.warning(f'[api/notifications] {member.nick} / {member} error in api payload: {req["error"]["code"]}: {req["error"]["error"]}')
                        continue

                    # notify event
                    if "event" in notifications:
                        if not req["notifications"]["events"]:
                            notifications["event"] = dict({})
                        else:
                            # loop over events
                            for k, v in req["events"].items():
                                # if new event not notified -> notify
                                if not v["seen"] and k not in notifications["event"]:
                                    await member.send(cleanhtml(v["event"]).replace(" [View]", ""))
                                    notifications["event"][k] = True

                                # if seen even already notified -> clean table
                                elif v["seen"] and k in notifications["event"]:
                                    del notifications["event"][k]

                    # notify message
                    if "message" in notifications:
                        if not req["notifications"]["messages"]:
                            notifications["messages"] = dict({})
                        else:
                            # loop over messages
                            for k, v in req["messages"].items():
                                # if new event not notified -> notify
                                if not v["seen"] and k not in notifications["message"]:
                                    await member.send(f'New message from {v["name"]}: {v["title"]}')
                                    notifications["message"][k] = True

                                # if seen even already notified -> clean table
                                elif v["seen"] and k in notifications["message"]:
                                    del notifications["message"][k]

                    # notify awards
                    if "award" in notifications:
                        if req["notifications"]["awards"]:
                            # if new award or different number of awards
                            if not notifications["award"].get("notified", False) or notifications["award"].get("notified") != req["notifications"]["awards"]:
                                s = "s" if req["notifications"]["awards"] > 1 else ""
                                await member.send(f'You have {req["notifications"]["awards"]} new award{s}')
                                notifications["award"]["notified"] = req["notifications"]["awards"]

                        else:
                            notifications["award"] = dict({})

                    # notify energy
                    if "energy" in notifications:
                        if req["energy"]["fulltime"] < 90:
                            if not notifications["energy"].get("notified", False):
                                await member.send(f'Energy at {req["energy"]["current"]} / {req["energy"]["maximum"]}')
                            notifications["energy"]["notified"] = True

                        else:
                            notifications["energy"] = dict({})

                    # notify nerve
                    if "nerve" in notifications:
                        if req["nerve"]["fulltime"] < 90:
                            if not notifications["nerve"].get("notified", False):
                                await member.send(f'Nerve at {req["nerve"]["current"]} / {req["nerve"]["maximum"]}')
                            notifications["nerve"]["notified"] = True

                        else:
                            notifications["nerve"] = dict({})

                    # notify chain
                    if "chain" in notifications:
                        if req["chain"]["timeout"] < 90 and req["chain"]["current"] > 10:
                            if not notifications["chain"].get("notified", False):
                                await member.send(f'Chain timeout in {req["chain"]["timeout"]} seconds')
                            notifications["chain"]["notified"] = True

                        else:
                            notifications["chain"] = dict({})

                    # notify education
                    if "education" in notifications:
                        if req["education_timeleft"] < 90:
                            if not notifications["education"].get("notified", False):
                                await member.send(f'Education ends in {req["education_timeleft"]} seconds')
                            notifications["education"]["notified"] = True

                        else:
                            notifications["education"] = dict({})

                    # notify bank
                    if "bank" in notifications:
                        if req["city_bank"]["time_left"] < 90:
                            if not notifications["bank"].get("notified", False):
                                await member.send(f'Bank investment ends in {req["city_bank"]["time_left"]} seconds (${req["city_bank"]["amount"]:,.0f})')
                            notifications["bank"]["notified"] = True

                        else:
                            notifications["bank"] = dict({})

                    # notify drug
                    if "drug" in notifications:
                        if req["cooldowns"]["drug"] < 90:
                            if not notifications["drug"].get("notified", False):
                                await member.send(f'Drug cooldown ends in {req["cooldowns"]["drug"]} seconds')
                            notifications["drug"]["notified"] = True

                        else:
                            notifications["drug"] = dict({})

                    # notify medical
                    if "medical" in notifications:
                        if req["cooldowns"]["medical"] < 90:
                            if not notifications["medical"].get("notified", False):
                                await member.send(f'Medical cooldown ends in {req["cooldowns"]["medical"]} seconds')
                            notifications["medical"]["notified"] = True

                        else:
                            notifications["medical"] = dict({})

                    # notify booster
                    if "booster" in notifications:
                        if req["cooldowns"]["booster"] < 90:
                            if not notifications["booster"].get("notified", False):
                                await member.send(f'Booster cooldown ends in {req["cooldowns"]["booster"]} seconds')
                            notifications["booster"]["notified"] = True

                        else:
                            notifications["booster"] = dict({})

                    # notify travel
                    if "travel" in notifications:
                        if req["travel"]["time_left"] < 90:
                            if not notifications["travel"].get("destination", False):
                                await member.send(f'Landing in {req["travel"]["destination"]} in {req["travel"]["time_left"]} seconds')
                            notifications["travel"] = req["travel"]

                        else:
                            notifications["travel"] = dict({})

                    # update notifications in YATA's database
                    await con.execute('UPDATE player_player SET "notifications"=$1 WHERE "dId"=$2', json.dumps(notifications), member.id)

                except BaseException as e:
                    logging.error(f'[api/notifications] {member.nick} / {member}: {hide_key(e)}')
                    # headers = {"guild": guild, "guild_id": guild.id, "member": f'{member.nick} / {member}', "error": "personal notification error"}
                    # await self.bot.send_log_main(e, headers=headers, full=True)

        await con.close()

    @notify.before_loop
    async def before_notify(self):
        await self.bot.wait_until_ready()
