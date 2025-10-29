class Team:
    def __init__(self, name, lineup, bullpen):
        self.name = name
        self.lineup = lineup
        self.bullpen = bullpen
        self.lineup_index = 0

        # starter = first pitcher in bullpen list
        self.starter = bullpen[0] if bullpen else None
        self._pitcher = self.starter  # active pitcher slot

        # empty reserves by default
        self.reserves = []

    # -------------
    # Lineup control
    # -------------
    def next_batter(self):
        batter = self.lineup[self.lineup_index]
        self.lineup_index = (self.lineup_index + 1) % len(self.lineup)
        return batter

    # -------------
    # Pitcher control
    # -------------
    def get_pitcher(self):
        """Return the active pitcher (starter or current reliever)."""
        return getattr(self, "_pitcher", self.starter)

    def set_pitcher(self, pitcher):
        """Set a new active pitcher on the mound."""
        self._pitcher = pitcher

    @property
    def starting_pitcher(self):
        """Alias for compatibility."""
        return self.starter
