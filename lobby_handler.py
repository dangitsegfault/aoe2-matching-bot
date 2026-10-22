from database_handler import db
from itertools import combinations

class LobbyHandler:
    def __init__(self):
        # Only lobbies involving registered players.
        #
        # {
        #     lobby_id: {
        #         "data": lobby_data,
        #         "slots": can be player, ai, closed (maximum of 8)
        #         "message_id": discord_message_id
        #     }
        # }
        self.lobbies = {}

    # need to keep the same name for function as for MatchHandler
    async def parse_lobbies(self, lobbies):
        for lobby in lobbies:
            lobby_data = lobby["data"]
            lobby_id = lobby_data["matchId"]
            event_type = lobby["type"]

            match event_type:
                case "lobbyAdded":
                    if lobby_id in self.lobbies:
                        # Existing lobby: update its data.
                        self.lobbies[lobby_id]["data"] = lobby_data
                    else:
                        self.lobbies[lobby_id] = {
                            "data": lobby_data,
                            "slots": {},
                            "message_id": None,
                        }

                case "lobbyUpdated":
                    if lobby_id in self.lobbies:
                            self.lobbies[lobby_id]["data"].update(lobby_data)

                case "lobbyRemoved":
                    self.lobbies.pop(lobby_id, None)

                case "slotAdded":
                    if lobby_id in self.lobbies:
                        slot_id = lobby_data["slot"]

                        self.lobbies[lobby_id]["slots"][slot_id] = lobby_data

                case "slotUpdated":
                    if lobby_id in self.lobbies:
                        slot_id = lobby_data["slot"]
                        slots = self.lobbies[lobby_id]["slots"]

                        if slot_id in slots:
                            if (lobby_data.get("name") == "Closed"):
                                self.lobbies[lobby_id]["slots"].pop(slot_id, None)

                            else:
                                slots[slot_id].update(lobby_data)

                case "slotRemoved":
                    if lobby_id in self.lobbies:
                        slot_id = lobby_data["slot"]
                        self.lobbies[lobby_id]["slots"].pop(slot_id, None)

                case _:
                    print(
                        "Unknown event_type: {}".format(event_type)
                    )

        await self.print_interested_lobbies()

    # async def print_interested_lobbies(self):
    #     for lobby in self.lobbies:
    #         if self.has_member (lobby):
    #             print (f"Lobby [{lobby["matchId"]}] contains an interested player")

    async def print_interested_lobbies(self):
        for lobby_id, lobby in self.lobbies.items():
            if self.has_member(lobby):
                print(
                    f"Lobby [{lobby_id}] contains an interested player"
                )

    def has_member(self, lobby):
        return any(
            db.is_profile_registered(player.get("profileId"))
            for player in lobby["slots"].values()
        )

    def get_lobby(self, lobby_id):
        return self.lobbies.get(lobby_id)

    def get_all_lobbies(self):
        return self.lobbies.values()

    def make_lobby_message(self, lobby_data):
        players = lobby_data["players"]

        lines = [
            f"**{lobby_data['name']}**",
            f"Map: {lobby_data['mapName']}",
            "",
        ]

        for player in players:
            lines.append(
                f"{player['name']} — {player['civName']}"
            )

        return "\n".join(lines)

    def make_lobby_ended_message(self, lobby_data):
        return f"Lobby `{lobby_data['lobbyId']}` has ended."

    def balance_lobby (self, lobby_id):
        players = []
        lobby = self.lobbies.get(lobby_id)

        if not lobby:
            return None

        for slot in lobby["slots"].values():
            if slot.get("profileId"):
                players.append(slot)

        player_count = len (players)

        if player_count < 2:
            return None

        player_team_1 = player_count // 2
        player_team_2 = player_count - player_team_1

        if any(player["rating"] is None for player in players):
            return None

        best_split = None
        best_difference = float("inf")

        # Generate every possible Team 1 combination.
        for team_a_tuple in combinations(players, player_team_1):
            team_a = list(team_a_tuple)

            # Avoid checking mirrored team splits twice.
            if players[0] not in team_a:
                continue

            team_a_ids = {p["profileId"] for p in team_a}

            team_b = [
                p for p in players
                if p["profileId"] not in team_a_ids
            ]

            average_a = sum(p["rating"] for p in team_a) / player_team_1
            average_b = sum(p["rating"] for p in team_b) / player_team_2

            difference = abs(average_a - average_b)

            if difference < best_difference:
                best_difference = difference
                best_split = {
                    "team_a": team_a,
                    "team_b": team_b,
                    "average_a": average_a,
                    "average_b": average_b,
                    "elo_difference": best_difference,
                }

        return best_split
        

lobby_handler = LobbyHandler ()
