import asyncio
from database_handler import db
from discord_bot import bot

class MatchHandler:
    def __init__(self):
        # Only matches involving registered players.
        #
        # {
        #     match_id: {
        #         "data": match_data,
        #         "message_id": discord_message_id
        #     }
        # }
        self.matches = {}

    async def extract_target_matches(self, ongoing_matches):
        for match in ongoing_matches:
            match_data = match["data"]
            match_id = match_data["matchId"]
            event_type = match["type"]

            match event_type:
                case "matchAdded":
                    # Is anyone in this match one of our registered players?
                    if not self.has_member(match_data):
                        continue

                    if match_id in self.matches:
                        # Existing match: update its data but preserve message_id.
                        self.matches[match_id]["data"] = match_data
                    else:
                        # New match.
                        # send a message to the server and store its message id
                        content = self.make_match_message(match_data)

                        message_id = await bot.send_match_message(
                            content,
                            match_id,
                        )

                        self.matches[match_id] = {
                            "data": match_data,
                            "message_id": message_id,
                        }

                case "matchRemoved":
                    if match_id in self.matches:
                    # update the message on discord to tell the match has ended and delete the match from your lisr
                        message_id = self.matches[match_id]["message_id"]
                        content = self.make_match_ended_message(
                            self.matches[match_id]["data"]
                        )

                        await bot.update_match_message(
                            message_id,
                            content,
                        )
                        del self.matches[match_id]

                case _:
                    print ("Unknown event_type: {}" . format (event_type))
                
    def has_member(self, match_data):
        return any(
            db.is_member(player["profileId"])
            for player in match_data["players"]
        )

    def get_match(self, match_id):
        return self.matches.get(match_id)

    def get_all_matches(self):
        return self.matches.values()

    def make_match_message(self, match_data):
        players = match_data["players"]

        teams = {}

        for player in players:
            team = player["team"]
            teams.setdefault(team, []).append(player)

        lines = [
            f"Game started {match_data['started']}",
            f"**{match_data['name']}**",
            f"Map: {match_data['mapName']}",
            "",
        ]

        # Unassigned players first
        if "-" in teams:
            lines.append("**Team -**")
            for player in teams["-"]:
                lines.append(
                    f"{player['name']} — {player['civName']}"
                )
            lines.append("")

        # Teams 1 through 8
        for team_number in range(1, 9):
            if team_number not in teams:
                continue

            lines.append(f"**Team {team_number}**")

            for player in teams[team_number]:
                lines.append(
                    f"{player['name']} — {player['civName']}"
                )

            lines.append("")

        return "\n".join(lines).rstrip()

    def make_match_ended_message(self, match_data):
        return f"Match `{match_data['matchId']}` has ended."
