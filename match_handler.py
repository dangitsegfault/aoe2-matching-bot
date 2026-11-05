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
                            continue

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

                            print ("sending queue message")

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
                                    print (f"sent queue message [{message_id}] to {guild_id}")
                                    self.queues[queue_id]["messages"][guild_id] = message_id
                        case _:
                            print(
                                "unknown queueing status: {}".format(queue_status)
                            )

                case "queueingUpdated":
                    if queue_id in self.queues:
                        self.queues[queue_id]["data"].update(queue_data)

                case "queueingRemoved":
                    removal_reason = queue_data["reason"]

                    match removal_reason:
                        case "matched" | "left" | "cancelled":
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

                        case "started":
                            # check if a message has been sent to the discord related to the queue id
                            # if yes, then transfer the control of updating that match id to self.matches
                            # if not, remove the match informaton from self.queues
                            # when handeling control over, if the self.matches already have an item containing same match id, update its messages field with the one in the queue, if not then make a new item in self.matches using match id as the key then delete the item from self.queues
                            queue = self.queues.get(queue_id)

                            if queue is None:
                                continue

                            if not queue.get("messages"):
                                self.queues.pop(queue_id, None)
                                continue

                            match_id = queue["data"]["matchId"]
                            paired_match = self.matches.get (match_id)

                            if paired_match:
                                paired_match["messages"] = queue["messages"].copy()
                                paired_match["update-messages"] = True
                                self.queues.pop(queue_id, None)

                            else:
                                self.matches[match_id] = {
                                    "data": {},
                                    "messages": queue["messages"].copy(),
                                    "update-messages": True,
                                }
                                self.queues.pop(queue_id, None)

                        case _:
                            print(
                                "unknown queueing removal reason: {}".format(removal_reason)
                            )

                case _:
                    print(
                        "Unknown queueing event_type: {}".format(event_type)
                    )

        # await self.print_interested_queues()

    async def print_interested_queues(self):
        for queue_id, queue in self.queues.items():
            players = ", ".join(
                player.get("name") or "Unknown"
                for player in queue["data"]["players"]
            )
            interest = (
                "an interesting player"
                if self.queue_has_member(queue)
                else "no interesting player"
            )

            print(
                f"Match [{queue['data']['matchId']}] is in queue "
                f"with players {players} and contains {interest}"
            )

    def queue_has_member(self, queue):
        return any(
            db.is_profile_registered(player.get("profileId"))
            for player in queue["data"]["players"]
        )

    async def parse_matches_started(self, started_matches):
        for match_data in started_matches:
            match_id = match_data.get("matchId")

            if match_id is None:
                print ("Match id is none")
                continue

            if match_id in self.matches:
                # Existing match: update its data but preserve message_id.
                self.matches[match_id]["data"] = match_data

            else:
                self.matches[match_id] = {
                    "data": match_data,
                    "messages": {},
                    "update-messages": True,
                }

            # check if self.queues have data related to this match
            for queue_id, queue in self.queues.items():
                if queue["data"]["matchId"] == match_id:
                    self.matches[match_id]["update-messages"] = False
                    continue


            # send a message to the server and store its message id
            match_pointer = self.matches.get (match_id)
            if match_pointer.get("messages") and match_pointer.get("update-messages"):
                await self.update_match_message (match_id, match_data)
                match_pointer["update-messages"] = False               

            elif not match_pointer.get("messages") and match_pointer.get("update-messages"):
                await self.send_new_match_message (match_id, match_data)
                match_pointer["update-messages"] = False

    async def send_new_match_message (self, match_id, match_data):
        guild_ids = set()

        # Is anyone in this match one of our registered players?
        for team in match_data.get("teams") or []:
            for player in team.get("players") or []:
                player_guilds = db.get_guilds_by_profile_id(
                    player["profileId"]
                )

                guild_ids.update(player_guilds)

        if not guild_ids:
            del self.matches[match_id]
            return

        content = self.make_match_content(match_data)
        image = make_match_image(match_data)

        for guild_id in guild_ids:
            message_id = await bot.send_match_message(
                content,
                image,
                match_id,
                guild_id,
            )

            if message_id is not None:
                self.matches[match_id]["messages"][guild_id] = message_id


        self.matches[match_id]["update-messages"] = False
        
    async def update_match_message (self, match_id, match_data):
        content = self.make_match_content(match_data)
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

        return all_updated
    
    async def parse_matches_finished(self, started_matches):
        for match_data in started_matches:
            match_id = match_data.get("matchId")

            if match_id is None:
                continue

            if match_id not in self.matches:
                continue

            # update the message on discord to tell the match has finished and delete the match from your lisr

            self.matches[match_id]["data"] = match_data 
            all_updated = await self.update_match_message (match_id, match_data)

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

        
    def make_match_content(self, match_data):
        match_finished = match_data.get("finished")

        if match_finished:
            timestamp = self.get_discord_timestamp(
                match_data.get("finished")
            )

            lines = [
                f"Game finished <t:{timestamp}:F>",
                ""
            ]

            return "\n".join(lines).rstrip()

        else:
            timestamp = self.get_discord_timestamp(
                match_data.get("started")
            )

            lines = [
                f"Game started <t:{timestamp}:F>",
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
