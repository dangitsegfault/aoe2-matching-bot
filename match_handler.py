import asyncio
from database_handler import db
from discord_bot import bot
from datetime import datetime, timezone
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

    async def parse_matches_started(self, started_matches):
        for match_data in started_matches:
            match_id = match_data["matchId"]

            if match_id in self.matches:
                # Existing match: update its data but preserve message_id.
                self.matches[match_id]["data"] = match_data
                continue

            # New match.
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
            embed = self.make_match_started_embed(match_data)


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

    async def parse_matches_finished(self, started_matches):
        for match_data in started_matches:
            match_id = match_data["matchId"]

            if match_id not in self.matches:
                continue

            # update the message on discord to tell the match has finished and delete the match from your lisr

            self.matches[match_id]["data"] = match_data 
            content = self.make_match_finished_content(match_data)
            embed = self.make_match_finished_embed(match_data)

            for guild_id, message_id in self.matches[match_id]["messages"].items():
                await bot.update_match_message(
                    message_id,
                    guild_id,
                    content,
                    embed,
                )

            del self.matches[match_id]
                    
    def make_match_started_embed(self, match_data):
        embed = discord.Embed(
            title=match_data.get("name") or "Unknown Match"
        )

        embed.description = (
            f"Map: {match_data.get('mapName') or '-'}"
        )

        teams = match_data.get("teams") or []

        def add_team_columns(team_label, players):
            names_col = "\n".join(
                (
                    f"{self.PLAYER_EMOJIS.get(player.get('color'), '')} "
                    f"{player.get('name') or 'Unknown'}"
                ).strip()
                for player in players
            ) + "\n\u200b"

            civ_col = "\n".join(
                player.get("civName") or "-"
                for player in players
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

        for team in teams:
            team_id = team.get("teamId")
            players = team.get("players") or []

            if not isinstance(team_id, int):
                team_label = "Team -"
            else:
                team_label = f"Team {team_id}"

            add_team_columns(team_label, players)

        return embed

    def make_match_finished_embed(self, match_data):
        embed = discord.Embed(
            title=match_data.get("name") or "Unknown Match"
        )

        embed.description = (
            f"Map: {match_data.get('mapName') or '-'}"
        )

        teams = match_data.get("teams") or []

        def add_team_columns(team_label, players):
            names_col = "\n".join(
                (
                    f"{self.PLAYER_EMOJIS.get(player.get('color'), '')} "
                    f"{player.get('name') or 'Unknown'}"
                ).strip()
                for player in players
            ) + "\n\u200b"

            civ_col = "\n".join(
                player.get("civName") or "-"
                for player in players
            ) + "\n\u200b"

            result_col = "\n".join(
                "Victory" if player.get("won") is True
                else "Defeat" if player.get("won") is False
                else "-"
                for player in players
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
                name="Result",
                value=result_col,
                inline=True,
            )

        for team in teams:
            team_id = team.get("teamId")
            players = team.get("players") or []

            if not isinstance(team_id, int):
                team_label = "Team -"
            else:
                team_label = f"Team {team_id}"

            add_team_columns(team_label, players)

        return embed

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
