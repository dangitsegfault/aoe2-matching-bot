import asyncio
from database_handler import db
from discord_bot import bot
from datetime import datetime

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
        # }
        self.matches = {}

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

    async def extract_target_matches(self, ongoing_matches):
        for match in ongoing_matches:
            match_data = match["data"]
            match_id = match_data["matchId"]
            event_type = match["type"]

            match event_type:
                case "matchAdded":
                    # Is anyone in this match one of our registered players?
                    if match_id in self.matches:
                        # Existing match: update its data but preserve message_id.
                        self.matches[match_id]["data"] = match_data
                        continue

                    # New match.
                    # send a message to the server and store its message id
                    content = self.make_match_message(match_data)

                    guild_ids = set()

                    for player in match_data["players"]:
                        player_guilds = db.get_guilds_by_profile_id(
                            player["profileId"]
                        )

                        for guild_id in player_guilds:
                            guild_ids.add(guild_id)

                    if not guild_ids:
                        continue

                    self.matches[match_id] = {
                        "data": match_data,
                        "messages": {}
                    }

                    for guild_id in guild_ids:
                        message_id = await bot.send_match_message(
                            content,
                            match_id,
                            guild_id,
                        )
                        self.matches[match_id]["messages"][guild_id] = message_id

                case "matchRemoved":
                    if match_id not in self.matches:
                        continue

                    # update the message on discord to tell the match has ended and delete the match from your lisr

                    match_data = self.matches[match_id]["data"]
                    content = self.make_match_ended_message(match_data)

                    for guild_id, message_id in self.matches[match_id]["messages"].items():
                        await bot.update_match_message(
                            message_id,
                            guild_id,
                            content,
                        )

                    del self.matches[match_id]

                case _:
                    print ("Unknown event_type: {}" . format (event_type))
                    
    def has_member(self, match_data):
        return any(
            db.is_profile_registered(player["profileId"])
            for player in match_data["players"]
        )

    def make_match_message(self, match_data):
        players = match_data["players"]

        teams = {}

        for player in players:
            team = player["team"]
            teams.setdefault(team, []).append(player)


        dt = datetime.fromisoformat(
            match_data["started"].replace("Z", "+00:00")
        )

        discord_timestamp = int(dt.timestamp())

        lines = [
            f"Game started <t:{discord_timestamp}:F>",
            "",
            f"**{match_data['name']}**",
            "",
            f"Map: {match_data['mapName']}",
            "",
        ]

        # Unassigned players first
        if "-" in teams:
            lines.append("**Team -**")
            for player in teams["-"]:
                emoji = self.PLAYER_EMOJIS[player["color"]]

                lines.append(
                    f"{emoji} {player['name']} — {player['civName']}"
                )
                lines.append("")

        # Teams 1 through 8
        for team_number in range(1, 9):
            if team_number not in teams:
                continue

            lines.append(f"**Team {team_number}**")

            for player in teams[team_number]:
                emoji = self.PLAYER_EMOJIS[player["color"]]

                lines.append(
                    f"{emoji} {player['name']} — {player['civName']}"
                )

            lines.append("")

        lines.append("")

        return "\n".join(lines).rstrip()

    def make_match_ended_message(self, match_data):
        return f"Match `{match_data['matchId']}` has ended."
