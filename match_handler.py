import asyncio
from database_handler import db
from discord_bot import bot
from datetime import datetime, timezone
import discord
from PIL import Image, ImageDraw, ImageFont
import io
import os

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
            FONT_BOLD, 18 * supersample_scale
        )
        body_font = ImageFont.truetype(
            FONT_REG, 16 * supersample_scale
        )
        vs_font = ImageFont.truetype(
            FONT_BOLD, 20 * supersample_scale
        )
        team_label_font = ImageFont.truetype(
            FONT_BOLD, 16 * supersample_scale
        )

        title = match_data.get("name") or "Unknown Match"
        map_name = match_data.get("mapName") or "-"
        teams = match_data.get("teams") or []

        image_width = 620

        player_row_height = 52
        player_row_gap = 8

        outer_padding = 20
        header_height = 60
        team_section_gap = 16
        team_label_height = 24

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

        def centered_text_y(cursor_y, row_height, text, font):
            """Vertically center text within a row, correcting for the
            font's ascender offset so the glyph ink is centered, not
            just its bounding box."""
            bbox = draw.textbbox((0, 0), text, font=font)
            text_height = bbox[3] - bbox[1]
            return cursor_y + (row_height - text_height) // 2 - bbox[1]

        # ------------------------------------------------------------
        # Two-team layout
        # ------------------------------------------------------------
        if len(teams) == 2:
            column_gap = 50
            vs_width = 30

            column_width = (
                image_width
                - outer_padding * 2
                - column_gap
                - vs_width
            ) // 2

            total_player_rows = max(
                len(teams[0].get("players") or []),
                len(teams[1].get("players") or []),
            )

            image_height = (
                outer_padding * 2
                + header_height
                + total_player_rows
                * (player_row_height + player_row_gap)
                - player_row_gap
            )

            scaled_width = image_width * supersample_scale
            scaled_height = image_height * supersample_scale

            scaled_padding = (
                outer_padding * supersample_scale
            )
            scaled_header_height = (
                header_height * supersample_scale
            )
            scaled_row_height = (
                player_row_height * supersample_scale
            )
            scaled_row_gap = (
                player_row_gap * supersample_scale
            )
            scaled_column_width = (
                column_width * supersample_scale
            )

            image = Image.new(
                "RGB",
                (scaled_width, scaled_height),
                "#1E1F22",
            )

            draw = ImageDraw.Draw(image)

            # Header
            draw.text(
                (
                    scaled_padding,
                    scaled_padding,
                ),
                title,
                font=title_font,
                fill="#FFFFFF",
            )

            draw.text(
                (
                    scaled_padding,
                    scaled_padding
                    + 28 * supersample_scale,
                ),
                f"Map: {map_name}",
                font=body_font,
                fill="#949BA4",
            )

            left_x = scaled_padding

            right_x = (
                scaled_width
                - scaled_padding
                - scaled_column_width
            )

            start_y = (
                scaled_padding
                + scaled_header_height
            )

            # VS
            vs_text = "VS"

            vs_bbox = draw.textbbox(
                (0, 0),
                vs_text,
                font=vs_font,
            )

            vs_text_width = (
                vs_bbox[2] - vs_bbox[0]
            )
            vs_text_height = (
                vs_bbox[3] - vs_bbox[1]
            )

            vs_x = (
                scaled_width - vs_text_width
            ) // 2

            vs_y = (
                start_y
                + (
                    total_player_rows
                    * (scaled_row_height + scaled_row_gap)
                    - scaled_row_gap
                ) // 2
                - vs_text_height // 2
                - vs_bbox[1]
            )

            draw.text(
                (vs_x, vs_y),
                vs_text,
                font=vs_font,
                fill="#B5BAC1",
            )

            def draw_player_column(players, x):
                cursor_y = start_y

                for player in players:
                    accent_color = self.PLAYER_COLORS.get(
                        player.get("color"),
                        "#72767D",
                    )

                    player_name = (
                        player.get("name") or "Unknown"
                    )

                    player_rating = str(
                        player.get("rating") or "-"
                    )

                    civ = player.get("civ")
                    civ_icon = load_civ_icon(civ)

                    # Player card
                    draw.rounded_rectangle(
                        [
                            x,
                            cursor_y,
                            x + scaled_column_width,
                            cursor_y + scaled_row_height,
                        ],
                        radius=10 * supersample_scale,
                        fill="#2B2D31",
                    )

                    # Player color accent
                    draw.rounded_rectangle(
                        [
                            x,
                            cursor_y,
                            x + 5 * supersample_scale,
                            cursor_y + scaled_row_height,
                        ],
                        radius=3 * supersample_scale,
                        fill=accent_color,
                    )

                    # Civilization icon
                    civ_icon_size = 40 * supersample_scale
                    icon_gap = 10 * supersample_scale  # space between accent bar and icon

                    icon_x = x + 5 * supersample_scale + icon_gap
                    icon_y = cursor_y + (scaled_row_height - civ_icon_size) // 2

                    if civ_icon:
                        civ_icon = civ_icon.resize(
                            (civ_icon_size, civ_icon_size),
                            Image.LANCZOS,
                        )

                        image.paste(
                            civ_icon,
                            (icon_x, icon_y),
                            civ_icon,
                        )

                    # Player name
                    player_name_x = icon_x + civ_icon_size + 12 * supersample_scale

                    rating_width = draw.textlength(
                        player_rating,
                        font=body_font,
                    )

                    max_name_width = (
                        x
                        + scaled_column_width
                        - 16 * supersample_scale
                        - rating_width
                        - player_name_x
                    )

                    name = player_name

                    while (
                        draw.textlength(
                            name,
                            font=body_font,
                        ) > max_name_width
                        and len(name) > 1
                    ):
                        name = name[:-2] + "…"

                    name_y = centered_text_y(
                        cursor_y, scaled_row_height, name, body_font
                    )

                    draw.text(
                        (
                            player_name_x,
                            name_y,
                        ),
                        name,
                        font=body_font,
                        fill="#FFFFFF",
                    )

                    # Rating
                    rating_x = (
                        x
                        + scaled_column_width
                        - 16 * supersample_scale
                        - rating_width
                    )

                    rating_y = centered_text_y(
                        cursor_y, scaled_row_height, player_rating, body_font
                    )

                    draw.text(
                        (
                            rating_x,
                            rating_y,
                        ),
                        player_rating,
                        font=body_font,
                        fill="#DBDEE1",
                    )

                    cursor_y += (
                        scaled_row_height
                        + scaled_row_gap
                    )

            draw_player_column(
                teams[0].get("players") or [],
                left_x,
            )

            draw_player_column(
                teams[1].get("players") or [],
                right_x,
            )

        # ------------------------------------------------------------
        # Three or more teams: vertical layout
        # ------------------------------------------------------------
        else:
            total_player_rows = sum(
                len(team.get("players") or [])
                for team in teams
            )

            image_height = (
                outer_padding * 2
                + header_height
                + len(teams)
                * (team_label_height + team_section_gap)
                + total_player_rows
                * (player_row_height + player_row_gap)
                - (
                    player_row_gap
                    if total_player_rows
                    else 0
                )
            )

            scaled_width = (
                image_width * supersample_scale
            )
            scaled_height = (
                image_height * supersample_scale
            )

            scaled_padding = (
                outer_padding * supersample_scale
            )
            scaled_header_height = (
                header_height * supersample_scale
            )
            scaled_row_height = (
                player_row_height * supersample_scale
            )
            scaled_row_gap = (
                player_row_gap * supersample_scale
            )
            scaled_team_section_gap = (
                team_section_gap * supersample_scale
            )
            scaled_team_label_height = (
                team_label_height * supersample_scale
            )

            image = Image.new(
                "RGB",
                (scaled_width, scaled_height),
                "#1E1F22",
            )

            draw = ImageDraw.Draw(image)

            # Header
            draw.text(
                (
                    scaled_padding,
                    scaled_padding,
                ),
                title,
                font=title_font,
                fill="#FFFFFF",
            )

            draw.text(
                (
                    scaled_padding,
                    scaled_padding
                    + 28 * supersample_scale,
                ),
                f"Map: {map_name}",
                font=body_font,
                fill="#949BA4",
            )

            cursor_y = (
                scaled_padding
                + scaled_header_height
            )

            for team in teams:
                team_id = team.get("teamId")

                team_label = (
                    f"Team {team_id}"
                    if isinstance(team_id, int)
                    else "Team -"
                )

                draw.text(
                    (
                        scaled_padding,
                        cursor_y,
                    ),
                    team_label,
                    font=team_label_font,
                    fill="#B5BAC1",
                )

                cursor_y += scaled_team_label_height

                for player in team.get("players") or []:
                    accent_color = self.PLAYER_COLORS.get(
                        player.get("color"),
                        "#72767D",
                    )

                    player_name = (
                        player.get("name") or "Unknown"
                    )

                    player_rating = str(
                        player.get("rating") or "-"
                    )

                    civ = player.get("civ")
                    civ_icon = load_civ_icon(civ)

                    # Player card
                    draw.rounded_rectangle(
                        [
                            scaled_padding,
                            cursor_y,
                            scaled_width - scaled_padding,
                            cursor_y + scaled_row_height,
                        ],
                        radius=10 * supersample_scale,
                        fill="#2B2D31",
                    )

                    # Player color accent
                    draw.rounded_rectangle(
                        [
                            scaled_padding,
                            cursor_y,
                            scaled_padding
                            + 5 * supersample_scale,
                            cursor_y + scaled_row_height,
                        ],
                        radius=3 * supersample_scale,
                        fill=accent_color,
                    )

                    # Civilization icon
                    civ_icon_size = 40 * supersample_scale
                    icon_gap = 10 * supersample_scale

                    icon_x = scaled_padding + 5 * supersample_scale + icon_gap
                    icon_y = cursor_y + (scaled_row_height - civ_icon_size) // 2

                    if civ_icon:
                        civ_icon = civ_icon.resize(
                            (civ_icon_size, civ_icon_size),
                            Image.LANCZOS,
                        )

                        image.paste(
                            civ_icon,
                            (icon_x, icon_y),
                            civ_icon,
                        )

                    # Player name
                    player_name_x = icon_x + civ_icon_size + 16 * supersample_scale

                    rating_width = draw.textlength(
                        player_rating,
                        font=body_font,
                    )

                    max_name_width = (
                        scaled_width
                        - scaled_padding
                        - 20 * supersample_scale
                        - rating_width
                        - player_name_x
                    )

                    name = player_name

                    while (
                        draw.textlength(
                            name,
                            font=body_font,
                        ) > max_name_width
                        and len(name) > 1
                    ):
                        name = name[:-2] + "…"

                    name_y = centered_text_y(
                        cursor_y, scaled_row_height, name, body_font
                    )

                    draw.text(
                        (
                            player_name_x,
                            name_y,
                        ),
                        name,
                        font=body_font,
                        fill="#FFFFFF",
                    )

                    # Rating
                    rating_x = (
                        scaled_width
                        - scaled_padding
                        - 20 * supersample_scale
                        - rating_width
                    )

                    rating_y = centered_text_y(
                        cursor_y, scaled_row_height, player_rating, body_font
                    )

                    draw.text(
                        (
                            rating_x,
                            rating_y,
                        ),
                        player_rating,
                        font=body_font,
                        fill="#DBDEE1",
                    )

                    cursor_y += (
                        scaled_row_height
                        + scaled_row_gap
                    )

                cursor_y += scaled_team_section_gap

        # ------------------------------------------------------------
        # Downsample and return
        # ------------------------------------------------------------
        buffer = io.BytesIO()

        image = image.resize(
            (
                image_width,
                image_height,
            ),
            Image.LANCZOS,
        )

        image.save(buffer, "PNG")
        buffer.seek(0)

        return buffer
