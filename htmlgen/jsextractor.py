import json
from scoreboard import LeaderBoard
import re
from collections import defaultdict


class jsextractor():
    def __init__(self, board):
        self.indent = {}
        # self.indent = {"indent": 3}
        self.board = board

    def flush(self, filename: str) -> None:
        with open(filename, "w") as f:
            # List of names
            f.write(self.all_players("all_players"))

            # Medals in different orders
            f.write(self.medals_best_time("medals_best_times"))
            f.write(self.medals_star2("medals_star2"))

            # Column definitions
            f.write(self.coldefs_two_stars("two_star_coldefs"))
            f.write(self.coldefs_one_star("one_star_coldefs"))
            f.write(self.default_coldefs_two_stars("default_coldefs_two_stars"))
            f.write(self.default_coldefs_two_stars_time("default_coldefs_two_stars_time"))
            f.write(self.default_coldefs_one_stars_time("default_coldefs_one_stars_time"))

            # Table data
            f.write(self.daily_position("d_daily_position"))
            f.write(self.accumulated_score("d_accumulated_score"))
            f.write(self.time_to_complete("d_time_to_complete"))
            f.write(self.offset_from_winner("d_offset_from_winner"))
            f.write(self.time_to_second_star("d_second_star"))
            f.write(self.accumulated_solve_time("d_accumulated_solve_time"))
            f.write(self.global_score("d_globalscore"))
            f.write(self.tobii_score("d_tobiiscore"))
            f.write(self.accumulated_position("d_accumulated_position"))
            f.write(self.score_diff("d_score_diff"))

            # Graph data
            f.write(self.scorediff_graph("scorediffgraph"))
            f.write(self.accumulated_position_graph("accumulated_positions"))
            f.write(self.daily_position_graph("daily_position_graph"))

    def get_padding(self, list_size) -> int:
        if list_size < 10:
            return 1
        if list_size < 100:
            return 2
        return 3

    def medals_best_time(self, varname: str) -> str:
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

        return f"var {varname} = {json.dumps(data, **self.indent)};\n\n"

    def medals_star2(self, varname: str) -> str:
        data = defaultdict(dict)
        for d in range(1, self.board.highestday+1):
            results = defaultdict(list)
            for p in self.board.players:
                if p[d].timetocompletestar2 is not None:
                    results[p[d].timetocompletestar2].append(p)

            for i, res in enumerate(sorted(results)[:3], start=1):
                for p in results[res]:
                    data[d][self.board.ordered_players.index(p)] = i

        return f"var {varname} = {json.dumps(data, **self.indent)};\n\n"

    def all_players(self, varname: str) -> str:
        res = [_.name for _ in self.board.ordered_players if _.totalscore > 0]
        return f"var {varname} = {json.dumps(res, **self.indent)};\n\n"

    def scorediff_graph(self, varname: str) -> str:
        res = []
        for day in range(1, self.board.highestday+1):
            for star in range(2):
                playerdata = [((day-1) * 2 + star + 1) / 2.0]
                for p in [_ for _ in self.board.ordered_players if _.totalscore > 0]:
                    playerdata.append(self.board.days[day][star].topscore - p[day][star].accumulatedscore)
                res.append(playerdata)

        return f"var {varname} = {json.dumps(res, **self.indent)};\n\n"

    def accumulated_position_graph(self, varname: str) -> str:
        res = []
        for day in range(1, self.board.highestday+1):
            for star in range(2):
                playerdata = [((day-1) * 2 + star + 1) / 2.0]
                for p in [_ for _ in self.board.ordered_players if _.totalscore > 0]:
                    playerdata.append(p[day][star].accumulatedposition + 1)
                res.append(playerdata)

        return f"var {varname} = {json.dumps(res, **self.indent)};\n\n"

    def daily_position_graph(self, varname: str) -> str:
        res = []
        for day in range(1, self.board.highestday+1):
            for star in range(2):
                playerdata = [((day-1) * 2 + star + 1) / 2.0]
                for p in [_ for _ in self.board.ordered_players if _.totalscore > 0]:
                    playerdata.append(p[day][star].position)
                res.append(playerdata)

        return f"var {varname} = {json.dumps(res, **self.indent)};\n\n"

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

    def score_diff(self, varname: str) -> str:
      data = []
      for i, p in enumerate(self.board.ordered_players, start=1):
          player_data = self.common_columns(i, p)
          for d in range(1, self.board.highestday+1):
              for star in range(2):
                  player_data[f"d{d}_{star}"] = self.board.days[d][star].topscore - p[d][star].accumulatedscore
          data.append(player_data)

      s = json.dumps(data, **self.indent)
      return f"var {varname} = {s};\n\n"

    def generate_two_star_data(self, varname: str, starextractor) -> str:
      data = []
      for i, p in enumerate(self.board.ordered_players, start=1):
          player_data = self.common_columns(i, p)
          for d in range(1, self.board.highestday+1):
              for star in range(2):
                  player_data[f"d{d}_{star}"] = starextractor(p[d][star])
          data.append(player_data)

      s = json.dumps(data, **self.indent)
      return f"var {varname} = {s};\n\n"

    def accumulated_position(self, varname: str) -> str:
      return self.generate_two_star_data(varname, lambda star: star.accumulatedposition + 1)

    def daily_position(self, varname: str) -> str:
        return self.generate_two_star_data(varname, lambda star: star.position)

    def global_score(self, varname: str) -> str:
        return self.generate_two_star_data(varname, lambda star: star.globalscore)

    def tobii_score(self, varname: str) -> str:
        return self.generate_two_star_data(varname, lambda star: star.accumulatedtobiiscore)


    def coldefs_two_stars(self, varname: str) -> str:
        data = self.common_coldefs()
        for d in range(1, self.board.highestday+1):
            for star in range(2):
                data.append({
                  "headerName": f"{d}/{star+1}",
                  "headerTooltip": f"Day {d} *{star+1}",
                  "field": f"d{d}_{star}",
                  })

        s = json.dumps(data, **self.indent)
        return f"var {varname} = {s};\n\n"

    def coldefs_one_star(self, varname: str) -> str:
        data = self.common_coldefs()

        for d in range(1, self.board.highestday+1):
            data.append({
              "headerName": f"{d}/*->**",
              "headerTooltip": f"Day {d} *->**",
              "field": f"d{d}",
              })

        s = json.dumps(data, **self.indent)
        return f"var {varname} = {s};\n\n"

    def string_to_tokens(self, s: str) -> str:
        s = re.sub(r'("comparator": )"([a-zA-Z0-9_]*)"', '\\1\\2', s)
        s = re.sub(r'("cellStyle": )"([a-zA-Z0-9_]*)"', '\\1\\2', s)
        s = re.sub(r'("valueFormatter": )"([a-zA-Z0-9_]*)"', '\\1\\2', s)
        return s

    def default_coldefs_two_stars(self, varname: str) -> str:
        res = {
            "sortable": True,
            "width": 70,
            "comparator": "comparator",
            "cellStyle": "medalPainter",
            "type": 'numericColumn'
        }
        s = self.string_to_tokens(json.dumps(res, **self.indent))
        return f"var {varname} = {s};\n\n"

    def default_coldefs_two_stars_time(self, varname: str) -> str:
        res = {
            "sortable": True,
            "width": 120,
            "comparator": "comparator",
            "cellStyle": "medalPainter",
            "type": 'numericColumn',
            "valueFormatter": "timedelta_to_string"
        }
        s = self.string_to_tokens(json.dumps(res, **self.indent))
        return f"var {varname} = {s};\n\n"

    def default_coldefs_one_stars_time(self, varname: str) -> str:
        res = {
            "sortable": True,
            "width": 120,
            "comparator": "comparator",
            "cellStyle": "medalPainter_star2",
            "type": 'numericColumn',
            "valueFormatter": "timedelta_to_string"
        }
        s = self.string_to_tokens(json.dumps(res, **self.indent))
        return f"var {varname} = {s};\n\n"

    def accumulated_score(self, varname: str) -> str:
        return self.generate_two_star_data(varname, lambda star: star.accumulatedscore)

    def time_to_second_star(self, varname: str) -> str:
        data = []
        for i, p in enumerate(self.board.ordered_players, start=1):
            player_data = self.common_columns(i, p)

            for d in range(1, self.board.highestday+1):
                player_data[f"d{d}"] = p[d].timetocompletestar2
            data.append(player_data)

        return f"var {varname} = {json.dumps(data, **self.indent)};\n\n"

    def time_to_complete(self, varname: str) -> str:
        return self.generate_two_star_data(varname, lambda star: star.timetocomplete)

    def accumulated_solve_time(self, varname: str) -> str:
        return self.generate_two_star_data(varname, lambda star: star.accumulatedtimetocomplete)

    def offset_from_winner(self, varname: str) -> str:
        return self.generate_two_star_data(varname, lambda star: star.offsetfromwinner)
