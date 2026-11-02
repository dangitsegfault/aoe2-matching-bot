import asyncio
from database_handler import db
from discord_bot import bot
from datetime import datetime, timezone
import discord
import io
import os
from png_renderer import make_match_image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class MatchHandler:
    def __init__(self):
        # Only matches involving registered players.
        #
        # {
        #     match_id: {
        #         "data": match_data,
        #         "messages": {
        #             guild_id: discord_message_id,
        #         }

        #     queue_id: {
        #         "data": queue_data,
        #         "messages": {
        #             guild_id: discord_message_id,
        #         }
        # }
        self.matches = {}
        self.queues = {}

        self.PLAYER_EMOJIS = {
            1: "<:player1:1540294289710522430>",
            2: "<:player2:1540294287772885022>",
            3: "<:player3:1540294285839171594>",
            4: "<:player4:1540294283670855700>",
            5: "<:player5:1540294281540141066>",
            6: "<:player6:1540294279698710578>",
            7: "<:player7:1540294277782048808>",
            8: "<:player8:1540294275890417744>",
        }

        self.PLAYER_COLORS = {
            1: "#4A6FE3", 2: "#E34A4A", 3: "#4AE36F", 4: "#E3D14A",
            5: "#4AD1E3", 6: "#E34AC9", 7: "#9A9A9A", 8: "#E38A4A",
        }

    async def parse_matches_queued(self, queued_matches):
        for queue in queued_matches:
            queue_data = queue["data"]
            queue_id = queue_data["id"]
            event_type = queue["type"]

            match event_type:
                case "queueingAdded":
                    queue_status = queue_data["status"]

                    match queue_status:
                        case "queueing":
                            self.queues[queue_id] = {
                            "data": queue_data,
                            "messages": {},
                            }

                        case "matched":
                            if queue_id not in self.queues:
                                self.queues[queue_id] = {
                                "data": queue_data,
                                "messages": {},
                                }

                            # check if the any player in the matched players are a registered player
                            # if yes send a message to the server similar to when match starts

                            guild_ids = set()

                            # Is anyone in this match one of our registered players?
                            for player in queue_data.get("players") or []:
                                player_guilds = db.get_guilds_by_profile_id(
                                    player["profileId"]
                                )

                                guild_ids.update(player_guilds)

                            if not guild_ids:
                                continue

                            content = self.make_match_queued_content(queue_data)
                            match_id = queue_data["matchId"]

                            for guild_id in guild_ids:
                                message_id = await bot.send_match_message(
                                    content,
                                    None,
                                    match_id,
                                    guild_id,
                                )

                                if message_id is not None:
                                    self.queues[queue_id]["messages"][guild_id] = message_id
                        case _:
                            print(
                                "unknown queueing status: {}".format(queue_status)
                            )

                case "queueUpdated":
                    if queue_id in self.queues:
                        self.queues[queue_id]["data"].update(queue_data)

                case "queueRemoved":
                    removal_reason = queue_data["reason"]

                    match removal_reason:
                        case "started" | "left" | "cancelled":
                            # check if a message has been sent to the discord related to the queue id
                            # if yes, then delete that message
                            # and after that

                            all_deleted = True

                            queue = self.queues.get(queue_id)

                            if queue is None:
                                continue

                            match_id = queue["data"].get("matchId")
                            for guild_id, message_id in self.queues[queue_id]["messages"].items():
                                if message_id is None:
                                    continue

                                message_delete_status = await bot.delete_match_message(
                                    message_id,
                                    guild_id,
                                    match_id
                                )

                                if message_delete_status is not True:
                                    all_deleted = False

                            if all_deleted:
                                self.queues.pop(queue_id, None)

                        case "matched":
                            # check if a message has been sent to the discord related to the queue id
                            # if yes, then transfer the control of updating that match id to self.matches
                            continue # let the match started function handle this


                        case _:
                            print(
                                "unknown queueing removal reason: {}".format(removal_reason)
                            )

                case _:
                    print(
                        "Unknown queueing event_type: {}".format(event_type)
                    )

        # await self.print_interested_queues()

    async def parse_matches_started(self, started_matches):
        for match_data in started_matches:
            match_id = match_data.get("matchId")

            if match_id is None:
                print ("Match id is none")
                continue

            if match_id in self.matches:
                # Existing match: update its data but preserve message_id.
                self.matches[match_id]["data"] = match_data
                continue

            # New match.

            # check if self.queues have data related to this match
            queue_id = None
            for queue_id, queue in self.queues.items():
                if not queue["data"]["matchId"] == match_id:
                    continue
                
                messages = queue["messages"]

                if messages:
                    queue_id = queue["data"]["id"]
                    break

            if queue_id:
                self.matches[match_id] = {
                    "data": match_data,
                    "messages": self.queues[queue_id]["messages"].copy()
                }
                self.queues.pop(queue_id, None)

                content = self.make_match_started_content(match_data)
                image = make_match_image(match_data)

                all_updated = True
                for guild_id, message_id in self.matches[match_id]["messages"].items():
                    if message_id is None:
                        continue

                    message_update_status = await bot.update_match_message(
                        message_id,
                        guild_id,
                        content,
                        image,
                        match_id
                    )

                    if message_update_status is not True:
                        all_updated = False

                continue

                

            # send a message to the server and store its message id

            guild_ids = set()

            # Is anyone in this match one of our registered players?
            for team in match_data.get("teams") or []:
                for player in team.get("players") or []:
                    player_guilds = db.get_guilds_by_profile_id(
                        player["profileId"]
                    )

                    guild_ids.update(player_guilds)

            if not guild_ids:
                continue

            content = self.make_match_started_content(match_data)
            image = make_match_image(match_data)

            self.matches[match_id] = {
                "data": match_data,
                "messages": {}
            }

            for guild_id in guild_ids:
                message_id = await bot.send_match_message(
                    content,
                    image,
                    match_id,
                    guild_id,
                )

                if message_id is not None:
                    self.matches[match_id]["messages"][guild_id] = message_id

            if not self.matches[match_id]["messages"]:
                del self.matches[match_id]

    async def parse_matches_finished(self, started_matches):
        for match_data in started_matches:
            match_id = match_data.get("matchId")

            if match_id is None:
                continue

            if match_id not in self.matches:
                continue

            # update the message on discord to tell the match has finished and delete the match from your lisr

            self.matches[match_id]["data"] = match_data 
            content = self.make_match_finished_content(match_data)
            image = make_match_image(match_data)

            all_updated = True

            for guild_id, message_id in self.matches[match_id]["messages"].items():
                if message_id is None:
                    continue

                message_update_status = await bot.update_match_message(
                    message_id,
                    guild_id,
                    content,
                    image,
                    match_id
                )
                
                if message_update_status is not True:
                    all_updated = False

            if all_updated:
                del self.matches[match_id]

    def make_match_queued_content (self, queue_data):
        timestamp = self.get_discord_timestamp(
            queue_data.get("matchedAt")
        )

        lines = [
            f"Game queued <t:{timestamp}:F> on {queue_data.get('server')}",
            ""
        ]

        return "\n".join(lines).rstrip()

        
    def make_match_started_content(self, match_data):
        timestamp = self.get_discord_timestamp(
            match_data.get("started")
        )

        lines = [
            f"Game started <t:{timestamp}:F>",
            ""
        ]

        return "\n".join(lines).rstrip()

    def make_match_finished_content(self, match_data):
        timestamp = self.get_discord_timestamp(
            match_data.get("finished")
        )

        lines = [
            f"Game finished <t:{timestamp}:F>",
            ""
        ]

        return "\n".join(lines).rstrip()

    def get_discord_timestamp(self, value):
        if value is None:
            dt = datetime.now(timezone.utc)
        else:
            dt = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

        return int(dt.timestamp())
