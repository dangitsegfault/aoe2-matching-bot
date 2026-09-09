import asyncio
from database_handler import db
from discord_bot import bot
from datetime import datetime, timezone
import discord
from PIL import Image, ImageDraw, ImageFont
import io
import os
from png_renderer import Container, ImageNode, Text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_REG = os.path.join(BASE_DIR, "assets", "fonts", "Inter_18pt-Regular.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "assets", "fonts", "Inter_18pt-Bold.ttf")

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

        self.PLAYER_COLORS = {
            1: "#4A6FE3", 2: "#E34A4A", 3: "#4AE36F", 4: "#E3D14A",
            5: "#4AD1E3", 6: "#E34AC9", 7: "#9A9A9A", 8: "#E38A4A",
        }

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
            image = self.make_match_started_image(match_data)


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
                self.matches[match_id]["messages"][guild_id] = message_id

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
            embed = self.make_match_finished_embed(match_data)

            for guild_id, message_id in self.matches[match_id]["messages"].items():
                if message_id is None:
                    continue

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

    def make_match_started_image(self, match_data):
        supersample_scale = 3

        title_font = ImageFont.truetype(
            FONT_BOLD,
            18 * supersample_scale,
        )

        body_font = ImageFont.truetype(
            FONT_REG,
            16 * supersample_scale,
        )

        vs_font = ImageFont.truetype(
            FONT_BOLD,
            20 * supersample_scale,
        )

        team_label_font = ImageFont.truetype(
            FONT_BOLD,
            16 * supersample_scale,
        )

        title = match_data.get("name") or "Unknown Match"
        teams = match_data.get("teams") or []

        meta_lines = [
            f"Leaderboard: {match_data.get('leaderboardName') or '-'}",
            f"Game Mode: {match_data.get('gameModeName') or '-'}",
            f"Map: {match_data.get('mapName') or '-'}",
            f"Map Size: {match_data.get('mapSizeName') or '-'}",
            f"Server: {match_data.get('server') or '-'}",
        ]

        image_width = 620

        outer_padding = 20

        player_row_height = 52
        player_row_gap = 8

        team_section_gap = 16
        team_label_height = 24

        column_gap = 50
        vs_width = 15

        background = (30, 31, 34, 255)
        card_background = (43, 45, 49, 255)
        secondary_text = (148, 155, 164, 255)
        primary_text = (255, 255, 255, 255)
        rating_text = (219, 222, 225, 255)
        vs_text_color = (181, 186, 193, 255)

        def load_civ_icon(civ):
            if not civ:
                return None

            path = os.path.join(
                BASE_DIR,
                "assets",
                "icons",
                "civs",
                f"{civ}.png",
            )

            if not os.path.exists(path):
                return None

            return Image.open(path).convert("RGBA")

        def truncate_text(text, font, max_width):
            dummy = Image.new("RGBA", (1, 1))
            draw = ImageDraw.Draw(dummy)

            if draw.textlength(text, font=font) <= max_width:
                return text

            while len(text) > 1:
                text = text[:-2] + "…"

                if draw.textlength(text, font=font) <= max_width:
                    return text

            return text

        def make_header():
            return Container(
                direction="column",
                gap=28 * supersample_scale,
                children=[
                    Text(
                        title,
                        font=title_font,
                        fill=primary_text,
                    ),
                    Container(
                        direction="column",
                        gap=0,
                        children=[
                            Text(
                                meta_lines[0],
                                font=body_font,
                                fill=secondary_text,
                            ),
                            Text(
                                meta_lines[1],
                                font=body_font,
                                fill=secondary_text,
                            ),
                            Text(
                                meta_lines[2],
                                font=body_font,
                                fill=secondary_text,
                            ),
                            Text(
                                meta_lines[3],
                                font=body_font,
                                fill=secondary_text,
                            ),
                            Text(
                                meta_lines[4],
                                font=body_font,
                                fill=secondary_text,
                            ),
                        ],
                    ),
                ],
            )

        def make_player_card(player, width):
            accent_color = self.PLAYER_COLORS.get(
                player.get("color"),
                "#72767D",
            )

            player_name = player.get("name") or "Unknown"
            player_rating = str(
                player.get("rating") or "-"
            )

            civ_icon = load_civ_icon(
                player.get("civ")
            )

            accent_width = 5 * supersample_scale
            icon_gap = 10 * supersample_scale
            icon_size = 40 * supersample_scale

            # Reserve space for:
            # accent + gap + icon + gap + rating + padding.
            rating_width = ImageDraw.Draw(
                Image.new("RGBA", (1, 1))
            ).textlength(
                player_rating,
                font=body_font,
            )

            name_width = (
                width
                - accent_width
                - icon_gap
                - icon_size
                - 12 * supersample_scale
                - rating_width
                - 16 * supersample_scale
            )

            name = truncate_text(
                player_name,
                body_font,
                max(1, name_width),
            )

            children = [
                Container(
                    width=accent_width,
                    height=player_row_height * supersample_scale,
                    background=accent_color,
                ),
            ]

            if civ_icon is not None:
                children.append(
                    ImageNode(
                        civ_icon,
                        width=icon_size,
                        height=icon_size,
                        align_self="center",
                    )
                )
            else:
                # Keep the layout identical when there is no civ icon.
                children.append(
                    Container(
                        width=icon_size,
                        height=icon_size,
                    )
                )

            children.append(
                Text(
                    name,
                    font=body_font,
                    fill=primary_text,
                    align_self="center",
                )
            )

            children.append(
                Text(
                    player_rating,
                    font=body_font,
                    fill=rating_text,
                    align_self="center",
                )
            )

            return Container(
                width=width,
                height=player_row_height * supersample_scale,
                direction="row",
                align="center",
                gap=icon_gap,
                padding=0,
                background=card_background,
                children=children,
            )

        def make_team_column(team, width):
            players = team.get("players") or []

            return Container(
                width=width,
                direction="column",
                gap=player_row_gap * supersample_scale,
                children=[
                    make_player_card(
                        player,
                        width,
                    )
                    for player in players
                ],
            )

        # ------------------------------------------------------------
        # Root
        # ------------------------------------------------------------

        if len(teams) == 2:
            team_width = (
                image_width * supersample_scale
                - outer_padding * 2 * supersample_scale
                - column_gap * 2 * supersample_scale
                - vs_width * supersample_scale
            ) // 2

            body = Container(
                direction="row",
                align="center",
                gap=column_gap * supersample_scale,
                children=[
                    make_team_column(
                        teams[0],
                        team_width,
                    ),

                    Container(
                        width=vs_width * supersample_scale,
                        align="center",
                        justify="center",
                        children=[
                            Text(
                                "VS",
                                font=vs_font,
                                fill=vs_text_color,
                            ),
                        ],
                    ),

                    make_team_column(
                        teams[1],
                        team_width,
                    ),
                ],
            )

        else:
            body_children = []

            for team in teams:
                team_id = team.get("teamId")

                team_label = (
                    f"Team {team_id}"
                    if isinstance(team_id, int)
                    else "Team -"
                )

                body_children.append(
                    Container(
                        direction="column",
                        gap=team_section_gap * supersample_scale,
                        children=[
                            Container(
                                height=team_label_height * supersample_scale,
                                align="center",
                                children=[
                                    Text(
                                        team_label,
                                        font=team_label_font,
                                        fill=vs_text_color,
                                    ),
                                ],
                            ),
                            *[
                                make_player_card(
                                    player,
                                    (
                                        image_width
                                        - outer_padding * 2
                                    )
                                    * supersample_scale,
                                )
                                for player in (
                                    team.get("players") or []
                                )
                            ],
                        ],
                    )
                )

            body = Container(
                direction="column",
                gap=team_section_gap * supersample_scale,
                children=body_children,
            )

        root = Container(
            width=image_width * supersample_scale,
            direction="column",
            gap=32 * supersample_scale,
            padding=outer_padding * supersample_scale,
            background=background,
            children=[
                make_header(),
                body,
            ],
        )

        # ------------------------------------------------------------
        # Render at 3x and downsample
        # ------------------------------------------------------------

        width, height = root.measure()

        root.actual_width = width
        root.actual_height = height
        root.x = 0
        root.y = 0

        root.layout()

        image = Image.new(
            "RGBA",
            (width, height),
            background,
        )

        root.draw(image)

        image = image.resize(
            (
                width // supersample_scale,
                height // supersample_scale,
            ),
            Image.Resampling.LANCZOS,
        )

        buffer = io.BytesIO()

        image.save(
            buffer,
            "PNG",
        )

        buffer.seek(0)

        return buffer
