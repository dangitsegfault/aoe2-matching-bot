import asyncio
from database_handler import db
from discord_bot import bot
from datetime import datetime
import discord

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
                    content = self.make_match_content(match_data)
                    embed = self.make_match_embedd(match_data)

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
                            embed,
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

    def make_match_content(self, match_data):
        dt = datetime.fromisoformat(
            match_data["started"].replace("Z", "+00:00")
        )

        discord_timestamp = int(dt.timestamp())

        lines = [
            f"Game started <t:{discord_timestamp}:F>",
            ""
        ]

        return "\n".join(lines).rstrip()


    def make_match_embedd(self, match_data):
        embed = discord.Embed(title=match_data["name"])
        embed.description = f"Map: {match_data['mapName']}"

        players = match_data["players"]
        teams = {}

        for player in players:
            teams.setdefault(player["team"], []).append(player)

        def add_team_columns(team_label, team_players):
            names_col = "\n".join(
                f"{self.PLAYER_EMOJIS.get(p['color'], '')} "
                f"{p['name'] or 'Unknown'}"
                for p in team_players
            ) + "\n\u200b"

            civ_col = "\n".join(
                p["civName"] or "-"
                for p in team_players
            ) + "\n\u200b"

            embed.add_field(
                name=team_label,
                value=names_col,
                inline=True,
            )
            embed.add_field(
                name="Civ",
                value=civ_col,
                inline=True,
            )
            embed.add_field(
                name="\u200b",
                value="\u200b",
                inline=True,
            )

        def team_sort_key(team):
            if team == "-":
                return (0, 0)

            if team is None:
                return (0, 1)

            return (1, team)

        for team_key in sorted(teams, key=team_sort_key):
            if team_key == "-":
                label = "Team -"
            elif team_key is None:
                label = "Team -"
            else:
                label = f"Team {team_key}"

            add_team_columns(label, teams[team_key])

        return embed

    def make_match_ended_message(self, match_data):
        return f"Match `{match_data['matchId']}` has ended."
