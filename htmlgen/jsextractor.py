import json
import re
import logging
from collections import defaultdict

from scoreboard import LeaderBoard

logger = logging.getLogger("aoc")


class jsextractor():
    def __init__(self, board):
        self.indent = {}
        # self.indent = {"indent": 3}
        self.board = board


    def _make_return_value(self, data, *, make_tokens: bool = False) -> str:
        """
        Convert the data into a variable or simply return it as a json string
        if no variable name was passed in.

        Args:
            data (dict|list): structure with data.
            make_tokens (bool, optional): If True, some strings on the data-side will get their quotations removed
            This allows them to be treated as programmatic tokens on the javascript sidebar. Defaults to False.

        Returns:
            str: data as a json dump
        """
        s = json.dumps(data, **self.indent)
        if make_tokens:
            return self.string_to_tokens(s)
        return s

    def get_padding(self, list_size) -> int:
        if list_size < 10:
            return 1
        if list_size < 100:
            return 2
        return 3

    def config(self) -> str:
        data = {
            'all_players': [_.name for _ in self.board.ordered_players if _.totalscore > 0],
            'medals_best_time': self._medals_best_time(),
            'medals_star2': self._medals_star2(),
            'title': self.board.title
        }
        return self._make_return_value(data)

    def _medals_best_time(self) -> dict:
        data = defaultdict(dict)
        for star in range(2):
            for d in range(1, self.board.highestday+1):
                results = defaultdict(list)
                for p in self.board.players:
                    offset = p[d][star].offsetfromwinner
                    if offset is not None:
                        results[p[d][star].offsetfromwinner].append(p)

                for i, res in enumerate(sorted(results)[:3], start=1):
                    for p in results[res]:
                        data[d*2 + star][self.board.ordered_players.index(p)] = i
        return data

    def _medals_star2(self) -> dict:
        data = defaultdict(dict)
        for d in range(1, self.board.highestday+1):
            results = defaultdict(list)
            for p in self.board.players:
                if p[d].timetocompletestar2 is not None:
                    results[p[d].timetocompletestar2].append(p)

            for i, res in enumerate(sorted(results)[:3], start=1):
                for p in results[res]:
                    data[d][self.board.ordered_players.index(p)] = i
        return data

    def all_players(self) -> str:
        data = [_.name for _ in self.board.ordered_players if _.totalscore > 0]
        return self._make_return_value(data)

    def scorediff_graph(self) -> str:
        data = []
        for day in range(1, self.board.highestday+1):
            for star in range(2):
                playerdata = [((day-1) * 2 + star + 1) / 2.0]
                for p in [_ for _ in self.board.ordered_players if _.totalscore > 0]:
                    playerdata.append(self.board.days[day][star].topscore - p[day][star].accumulatedscore)
                data.append(playerdata)

        return self._make_return_value(data)

    def accumulated_position_graph(self) -> str:
        data = []
        for day in range(1, self.board.highestday+1):
            for star in range(2):
                playerdata = [((day-1) * 2 + star + 1) / 2.0]
                for p in [_ for _ in self.board.ordered_players if _.totalscore > 0]:
                    playerdata.append(p[day][star].accumulatedposition + 1)
                data.append(playerdata)

        return self._make_return_value(data)

    def daily_position_graph(self) -> str:
        data = []
        for day in range(1, self.board.highestday+1):
            for star in range(2):
                playerdata = [((day-1) * 2 + star + 1) / 2.0]
                for p in [_ for _ in self.board.ordered_players if _.totalscore > 0]:
                    playerdata.append(p[day][star].position)
                data.append(playerdata)

        return self._make_return_value(data)

    def common_columns(self, pos, p) -> dict:
      pad = self.get_padding(len(self.board.ordered_players))
      return {
              "name": f"{pos:>{pad}}. {p.name}",
              "T": p.totalscore,
              "G": p.globalscore,
              "S": p.stars,
              "Tob": p.accumulatedtobiiscoretotal
            }

    def common_coldefs(self) -> list:
        width = 60
        return [
            {"field": "name", "resizable": True, "pinned": "left", "width": 200, },
            {"field": "T", "width": width+10, "headerTooltip": "Total score"},
            {"field": "G", "headerTooltip": "Global score"},
            {"field": "S", "headerTooltip": "# stars (problems solved)"},
            {"field": "Tob", "headerTooltip": "Tobii score"},
        ]

    def score_diff(self) -> str:
      data = []
      for i, p in enumerate(self.board.ordered_players, start=1):
          player_data = self.common_columns(i, p)
          for d in range(1, self.board.highestday+1):
              for star in range(2):
                  player_data[f"d{d}_{star}"] = self.board.days[d][star].topscore - p[d][star].accumulatedscore
          data.append(player_data)

      return self._make_return_value(data)

    def generate_two_star_data(self, *, starextractor) -> str:
      data = []
      for i, p in enumerate(self.board.ordered_players, start=1):
          player_data = self.common_columns(i, p)
          for d in range(1, self.board.highestday+1):
              for star in range(2):
                  player_data[f"d{d}_{star}"] = starextractor(p[d][star])
          data.append(player_data)

      return self._make_return_value(data)

    def accumulated_position(self) -> str:
      return self.generate_two_star_data(starextractor=lambda star: star.accumulatedposition + 1)

    def daily_position(self) -> str:
        return self.generate_two_star_data(starextractor=lambda star: star.position)

    def global_score(self) -> str:
        return self.generate_two_star_data(starextractor=lambda star: star.globalscore)

    def tobii_score(self) -> str:
        return self.generate_two_star_data(starextractor=lambda star: star.accumulatedtobiiscore)

    def coldefs_two_stars(self) -> str:
        data = self.common_coldefs()
        for d in range(1, self.board.highestday+1):
            for star in range(2):
                data.append({
                  "headerName": f"{d}/{star+1}",
                  "headerTooltip": f"Day {d} *{star+1}",
                  "field": f"d{d}_{star}",
                  })

        return self._make_return_value(data)

    def coldefs_one_star(self) -> str:
        data = self.common_coldefs()

        for d in range(1, self.board.highestday+1):
            data.append({
              "headerName": f"{d}/*->**",
              "headerTooltip": f"Day {d} *->**",
              "field": f"d{d}",
              })

        return self._make_return_value(data)

    def string_to_tokens(self, s: str) -> str:
        s = re.sub(r'("comparator": )"([a-zA-Z0-9_]*)"', '\\1\\2', s)
        s = re.sub(r'("cellStyle": )"([a-zA-Z0-9_]*)"', '\\1\\2', s)
        s = re.sub(r'("valueFormatter": )"([a-zA-Z0-9_]*)"', '\\1\\2', s)
        return s

    def default_coldefs_two_stars(self) -> str:
        data = {
            "sortable": True,
            "width": 70,
            "comparator": "comparator",
            "cellStyle": "medalPainter",
            "type": 'numericColumn'
        }
        return self._make_return_value(data, make_tokens=True)

    def default_coldefs_two_stars_time(self) -> str:
        data = {
            "sortable": True,
            "width": 120,
            "comparator": "comparator",
            "cellStyle": "medalPainter",
            "type": 'numericColumn',
            "valueFormatter": "timedelta_to_string"
        }
        return self._make_return_value(data, make_tokens=True)

    def default_coldefs_one_stars_time(self) -> str:
        data = {
            "sortable": True,
            "width": 120,
            "comparator": "comparator",
            "cellStyle": "medalPainter_star2",
            "type": 'numericColumn',
            "valueFormatter": "timedelta_to_string"
        }
        return self._make_return_value(data, make_tokens=True)

    def accumulated_score(self) -> str:
        return self.generate_two_star_data(starextractor=lambda star: star.accumulatedscore)

    def time_to_second_star(self) -> str:
        data = []
        for i, p in enumerate(self.board.ordered_players, start=1):
            player_data = self.common_columns(i, p)

            for d in range(1, self.board.highestday+1):
                player_data[f"d{d}"] = p[d].timetocompletestar2
            data.append(player_data)

        return self._make_return_value(data)

    def time_to_complete(self) -> str:
        return self.generate_two_star_data(starextractor=lambda star: star.timetocomplete)

    def accumulated_solve_time(self) -> str:
        return self.generate_two_star_data(starextractor=lambda star: star.accumulatedtimetocomplete)

    def offset_from_winner(self) -> str:
        return self.generate_two_star_data(starextractor=lambda star: star.offsetfromwinner)
