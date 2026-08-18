from database_handler import db

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

    def update(self, ongoing_matches):
        current_ids = set()

        for match in ongoing_matches:
            match_id = match["matchId"]

            # Is anyone in this match one of our registered players?
            if not self.is_registered(match):
                continue

            current_ids.add(match_id)

            if match_id in self.matches:
                # Existing match: update its data but preserve message_id.
                self.matches[match_id]["data"] = match
            else:
                # New interesting match.
                self.matches[match_id] = {
                    "data": match,
                    "message_id": None,
                }

    def is_registered(self, match):
        return any(
            player["profileId"] in db.members
            for player in match["players"]
        )

    def set_message_id(self, match_id, message_id):
        if match_id in self.matches:
            self.matches[match_id]["message_id"] = message_id

    def get_match(self, match_id):
        return self.matches.get(match_id)

    def get_all_matches(self):
        return self.matches.values()
