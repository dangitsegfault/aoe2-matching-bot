from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from datetime import datetime

import os
import io

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_REG = os.path.join(BASE_DIR, "assets", "fonts", "Inter_18pt-Regular.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "assets", "fonts", "Inter_18pt-Bold.ttf")

PLAYER_COLORS = {
    1: "#4A6FE3", 2: "#E34A4A", 3: "#4AE36F", 4: "#E3D14A",
    5: "#4AD1E3", 6: "#E34AC9", 7: "#9A9A9A", 8: "#E38A4A",
}

IMAGE_COLORS = {
    "background": (30, 31, 34, 255),
    "card_background": (43, 45, 49, 255),
    "secondary_text": (148, 155, 164, 255),
    "primary_text": (255, 255, 255, 255),
    "rating_text": (219, 222, 225, 255),
    "vs_text_color": (181, 186, 193, 255),
    "border": (39, 139, 245, 255),
    "transparent": (0, 0, 0, 0),
}

supersample_scale = 3

f_bold_18 = ImageFont.truetype(FONT_BOLD, 18 * supersample_scale)
f_reg_16 = ImageFont.truetype(FONT_REG, 16 * supersample_scale)
f_bold_16 = ImageFont.truetype(FONT_BOLD, 16 * supersample_scale)

def calculate_match_duration (start_time, finish_time):
    if start_time is None or finish_time is None:
        return "0h 0m"
    
    started = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    finished = datetime.fromisoformat(finish_time.replace("Z", "+00:00"))

    duration = finished - started

    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes = remainder // 60

    if hours:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def load_result_icon(result):
    if not result:
        return None

    path = os.path.join(
        BASE_DIR,
        "assets",
        "icons",
        "result",
        f"{result}.png",
    )

    if not os.path.exists(path):
        return None

    return Image.open(path).convert("RGBA")

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
        fallback_path = os.path.join(
            BASE_DIR,
            "assets",
            "icons",
            "civs",
            "unknown.png",
            )

        if not os.path.exists(fallback_path):
            return None

        return Image.open(fallback_path).convert("RGBA")

    return Image.open(path).convert("RGBA")

def load_map_icon(target_map):
    if not target_map:
        return None

    path = os.path.join(
        BASE_DIR,
        "assets",
        "icons",
        "maps",
        f"{target_map}.png",
    )

    if not os.path.exists(path):
        fallback_path = os.path.join(
            BASE_DIR,
            "assets",
            "icons",
            "maps",
            "Unknown.png",
            )

        if not os.path.exists(fallback_path):
            return None

        return Image.open(fallback_path).convert("RGBA")

    return Image.open(path).convert("RGBA")

def center_to_topleft(center_x, center_y, image_to_center):
    """Return the top-left coordinates needed to center an image at the given coordinates."""
    return (
        center_x - image_to_center.width // 2,
        center_y - image_to_center.height // 2,
    )

def merge_images(img1, img2, direction="vertical", padding=0):
    if direction == "horizontal":
        width = img1.width + padding + img2.width
        height = max(img1.height, img2.height)

        result = Image.new(
            "RGBA",
            (width, height),
            color=IMAGE_COLORS["transparent"],
        )

        # Vertically center both images
        y1 = (height - img1.height) // 2
        y2 = (height - img2.height) // 2

        result.paste(img1, (0, y1), img1)
        result.paste(
            img2,
            (img1.width + padding, y2),
            img2,
        )

    elif direction == "vertical":
        width = max(img1.width, img2.width)
        height = img1.height + padding + img2.height

        result = Image.new(
            "RGBA",
            (width, height),
            color=IMAGE_COLORS["transparent"],
        )

        # Horizontally center both images
        x1 = (width - img1.width) // 2
        x2 = (width - img2.width) // 2

        result.paste(img1, (x1, 0), img1)
        result.paste(
            img2,
            (x2, img1.height + padding),
            img2,
        )

    else:
        raise ValueError(
            "direction must be 'horizontal' or 'vertical'"
        )

    return result

def create_match_meta(match_data):
    if not match_data:
        return None

    padding = 20 * supersample_scale
    line_spacing = 8 * supersample_scale

    lines = [
        (
            f"{match_data.get('gameModeName') or '-'} · "
            f"{match_data.get('mapName') or '-'}",
            f_bold_16,
        ),
        (
            f"{match_data.get('leaderboardName') or '-'} · "
            f"{match_data.get('mapSizeName') or '-'}",
            f_reg_16,
        ),
        (
            f"{match_data.get('server') or calculate_match_duration(match_data.get('started'), match_data.get('finished'))}",
            f_reg_16,
        ),
    ]

    bboxes = [
        font.getbbox(text)
        for text, font in lines
    ]

    width = (
        max(bbox[2] - bbox[0] for bbox in bboxes)
        + padding * 2
    )

    # Sum the actual height of each line
    height = (
        sum(bbox[3] - bbox[1] for bbox in bboxes)
        + line_spacing * (len(lines) - 1)
        + padding * 2
    )

    img = Image.new("RGBA", (width, height), color=IMAGE_COLORS["transparent"])
    draw = ImageDraw.Draw(img)

    y = padding

    for i, (text, font) in enumerate(lines):
        bbox = font.getbbox(text)

        draw.text(
            (padding - bbox[0], y - bbox[1]),
            text,
            font=font,
            fill=IMAGE_COLORS["primary_text"],
        )

        # Move down by THIS font's actual height
        y += bbox[3] - bbox[1]

        if i < len(lines) - 1:
            y += line_spacing

    return img

def centered_text_y(draw, cursor_y, row_height, text, font):
    """Vertically center text within a row, correcting for the
    font's ascender offset so the glyph ink is centered, not
    just its bounding box."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_height = bbox[3] - bbox[1]
    return cursor_y + (row_height - text_height) // 2 - bbox[1]

def make_team_data(team, match_finished=False, is_ranked=False):
    """Create and return an image containing all players on a team."""

    result_victory = load_result_icon("victory")
    result_defeat = load_result_icon("defeat")
    result_unknown = load_result_icon("unknown")

    edge_padding = 15 * supersample_scale
    children_padding = 10 * supersample_scale

    civ_icon_size = 40 * supersample_scale
    result_icon_size = 30 * supersample_scale if match_finished else 0

    player_name_width = int (f_reg_16.getlength("XXXXXXXXXXXXXXXXX"))
    rating_width = (
        int(f_bold_16.getlength("8888"))
        if is_ranked else 0
    )

    team_width = edge_padding + civ_icon_size + children_padding + player_name_width + edge_padding

    if is_ranked:
        team_width = team_width + children_padding + rating_width

    if match_finished:
        team_width = team_width + children_padding + result_icon_size

    civ_icon_x = edge_padding

    player_name_x = (
        civ_icon_x
        + civ_icon_size
        + children_padding
    )

    rating_x = player_name_x + player_name_width + children_padding
    
    result_icon_x = (
        rating_x + rating_width + children_padding
        if is_ranked
        else player_name_x + player_name_width + children_padding
    )

    players = team.get("players") or []

    row_height = 52 * supersample_scale
    row_gap = 8 * supersample_scale

    team_height = (
        len(players) * row_height
        + max(0, len(players) - 1) * row_gap
    )

    team_image = Image.new(
        "RGBA",
        (team_width, team_height),
        color=IMAGE_COLORS["transparent"],
    )

    draw = ImageDraw.Draw(team_image)

    cursor_y = 0

    for player in players:
        accent_color = PLAYER_COLORS.get(
            player.get("color"),
            "#72767D",
        )

        player_name = player.get("name") or "Unknown"

        if is_ranked:
            player_rating = str(player.get("rating") or "-")

        civ = player.get("civ") or "-"
        civ_icon = load_civ_icon(civ)

        # Player card
        draw.rounded_rectangle(
            [
                0,
                cursor_y,
                team_width,
                cursor_y + row_height,
            ],
            radius=10 * supersample_scale,
            fill=IMAGE_COLORS["card_background"],
        )

        # Player color accent
        draw.rounded_rectangle(
            [
                0,
                cursor_y,
                5 * supersample_scale,
                cursor_y + row_height,
            ],
            radius=3 * supersample_scale,
            fill=accent_color,
        )

        civ_icon_y = cursor_y + (row_height - civ_icon_size) // 2

        if civ_icon:
            civ_icon = civ_icon.resize(
                (civ_icon_size, civ_icon_size),
                Image.LANCZOS,
            )

            team_image.paste(
                civ_icon,
                (civ_icon_x, civ_icon_y),
                civ_icon,
            )

        name = player_name

        while (
            draw.textlength(name, font=f_reg_16) > player_name_width
            and len(name) > 1
        ):
            name = name[:-2] + "…"

        name_y = centered_text_y(
            draw,
            cursor_y,
            row_height,
            name,
            f_reg_16,
        )

        draw.text(
            (player_name_x, name_y),
            name,
            font=f_reg_16,
            fill=IMAGE_COLORS["primary_text"],
        )

        if is_ranked:
            rating_y = centered_text_y(
                draw,
                cursor_y,
                row_height,
                player_rating,
                f_bold_16,
            )

            draw.text(
                (rating_x, rating_y),
                player_rating,
                font=f_bold_16,
                fill=IMAGE_COLORS["rating_text"],
            )

        if match_finished:
            game_result = player.get("won")

            if game_result is True:
                result_icon = result_victory

            elif game_result is False:
                result_icon = result_defeat

            else:
                result_icon = result_unknown

            result_icon = result_icon.resize(
                (result_icon_size, result_icon_size),
                Image.LANCZOS,
            )

            result_icon_y = cursor_y + (row_height - result_icon_size) // 2

            team_image.paste(
                result_icon,
                (result_icon_x, result_icon_y),
                result_icon,
            )

        cursor_y += row_height + row_gap

    return team_image

def make_match_image(match_data):
    map_icon = load_map_icon(match_data.get("mapName"))

    meta_image = merge_images(map_icon, create_match_meta (match_data), "horizontal", 20)

    teams = match_data.get ("teams") or None

    teams_images = []
    for team in teams:
        team_image = make_team_data(
            team,
            match_data.get("finished") is not None,
            match_data.get("leaderboard") != "unranked"
        )
        teams_images.append(team_image)

    teams_image_merged = None

    for i in range(0, len(teams_images), 2):
        image_a = teams_images[i]
        image_b = teams_images[i + 1] if i + 1 < len(teams_images) else None

        teams_image_duo = None

        if image_b is None:
            teams_image_duo = image_a

        else:
            teams_image_duo = merge_images(image_a, image_b, direction="horizontal", padding=100)

        if teams_image_merged is None:
            teams_image_merged = teams_image_duo
            continue

        teams_image_merged = merge_images(teams_image_merged, teams_image_duo, padding=50)

    image = merge_images(meta_image, teams_image_merged, padding=100)

    # make final image 10 percent bigger 
    final_image = Image.new(
        "RGBA",
        (image.width + int(image.width * 0.10),
        image.height + int(image.height * 0.10)),
        color=IMAGE_COLORS["transparent"])

    draw = ImageDraw.Draw(final_image)

    draw.rounded_rectangle(
        [
            0,
            0,
            final_image.width - 1,
            final_image.height - 1,
        ],
        radius=10 * supersample_scale,
        outline=IMAGE_COLORS["border"],
        fill=IMAGE_COLORS["background"],
        width=3 * supersample_scale,
    )

    final_image.paste(
        image,
        center_to_topleft(
            final_image.width // 2,
            final_image.height // 2,
            image),
        image,
    )

    # Downscale back to logical size with LANCZOS for a crisp, antialiased result.
    final_image = final_image.resize(
        (final_image.width // supersample_scale,
        final_image.height // supersample_scale),
        Image.LANCZOS)

    buffer = io.BytesIO()

    final_image.save(
        buffer,
        "PNG",
    )

    buffer.seek(0)

    return buffer
