import os
import logging
# from airium import Airium
from typing import List
from jinja2 import Environment, FileSystemLoader
from scoreboard import LeaderBoard, Player
import jinjafilters


class HtmlGenerator:
    def __init__(self, leaderboard: LeaderBoard):
        self.leaderboard = leaderboard
        self.html: List[str] = []
        self.tableid = 0
        # if (_settings.ContainsKey(fieldName))
        #     _metacolumns = _settings["fields_" + _leaderBoardId].Split(',').Select(s => s.Trim()).ToList();
        # else
        #     _metacolumns = new List<string>();
        self.metacolumns: List[str] = []

    def generate(self):
        logging.info("Generating html")
        root = os.path.dirname(os.path.abspath(__file__))
        print(f"root dir: {root}")
        templates_dir = os.path.join(root, 'templates')
        print(f"templates_dir: {templates_dir}")
        env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True
        )
        env.filters["timestr"] = jinjafilters.seconds_to_string
        env.filters["winner"] = jinjafilters.winner
        env.filters["htmlescape"] = jinjafilters.htmlescape
        env.filters["add_or_empty"] = jinjafilters.add_or_empty
        env.filters["empty_if_true"] = jinjafilters.empty_if_true
        env.filters["sortable"] = jinjafilters.sortable


        template = env.get_template('scores.html')

        res = template.render(leaderboard=self.leaderboard)
        print(f"Generated html ({len(res)} characters)")
        return res
        # outdir = os.path.join(root, 'output')
        # os.mkdir(outdir)
        outdir = "/tmp"
        filename = os.path.join(outdir, f'leaderboard_{self.leaderboard.boardid}_{self.leaderboard.year}.html')
        with open(filename, 'w', encoding='utf8') as fh:
            fh.write(res)
        logging.info("Done")
        return filename

if __name__ == "__main__":
    import aocgen
    raise Exception("This is just a module!")
