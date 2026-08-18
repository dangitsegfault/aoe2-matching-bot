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
        self.registered_profiles = {}

    def update(self, ongoing_matches):
        print ("Got a match update")
        return
    
        current_ids = set()

        for match in ongoing_matches:
            match_id = match["matchId"]

            # Is anyone in this match one of our registered players?
            if not self._is_interesting(match, self.registered_profiles):
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

    def _is_interesting(self, match):
        return any(
            player["profileId"] in self.registered_profiles
            for player in match["players"]
        )

    def set_message_id(self, match_id, message_id):
        if match_id in self.matches:
            self.matches[match_id]["message_id"] = message_id

    def get_match(self, match_id):
        return self.matches.get(match_id)

    def get_all_matches(self):
        return self.matches.values()
