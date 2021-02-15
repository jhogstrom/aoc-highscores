import json
import scores
import pathlib
import logging
import os
import boto3
import sys
from threading import Thread
from typing import Dict
from jsextractor import jsextractor

from scoreboard import LeaderBoard, ScoreboardRepresentation
from s3cache import S3Cache

cache_bucket_name = os.environ.get("S3_DATACACHE", "scoreboard-datacache")
html_bucket_name = os.environ.get("S3_HTML", "scoreboard-html")
html_bucket = boto3.resource('s3').Bucket(html_bucket_name)

DEFAULT_LOGLEVEL = logging.DEBUG
debuglevel = os.environ.get("debug", "")
debuglevels: Dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR}
debuglevel = debuglevels.get(debuglevel.upper(), DEFAULT_LOGLEVEL)


logger = logging.getLogger("aoc")
logger.setLevel(debuglevel)
formats: Dict[int, str] = {
    logging.DEBUG: '%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    logging.INFO: '%(asctime)s.%(msecs)03d - %(message)s'
}

formatter = logging.Formatter(
    formats.get(debuglevel, '%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s'),
    datefmt="%Y-%m-%d %H:%M:%S")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


def get_data(representation, sessionid: str):
    downloader = scores.Downloader(sessionid)
    cache = S3Cache(cache_bucket_name)
    retriever = scores.DataRetriever(downloader, cache)
    return retriever.get_data(representation)

# def get_text(representation, sessionid: str = None):
#     downloader = scores.Downloader(sessionid)
#     cache = S3Cache(cache_bucket_name)
#     retriever = scores.DataRetriever(downloader, cache)
#     return retriever.get_raw(representation)


def get_scores(year: str, sessionid: str, boardid: str):
    logger.info(f"Getting scores for {boardid} - {year}")
    representation = ScoreboardRepresentation(boardid, year)
    return get_data(representation, sessionid)

threads = []

def generate_data_proc(leaderboard: LeaderBoard, name: str, datafunc) -> None:
    filekey = f'{leaderboard.boardid}_{leaderboard.year}_{name}.json'
    logger.debug(f"Uploading {filekey}")
    html_bucket.put_object(
        Body=datafunc(),
        ContentType='application/json',
        Key=filekey)
    logger.debug(f"Uploading done")

def generate_data(leaderboard: LeaderBoard, name: str, datafunc) -> None:
    process = Thread(
        target=generate_data_proc,
        args=[leaderboard, name, datafunc])
    process.start()
    threads.append(process)

def generatelist(*,
        sessionid: str,
        year: str,
        title: str,
        boardid: str,
        namemap: dict,
        global_scores: dict):
    logger.info(f"Reading data for {title}/{year}")
    scoredict = get_scores(year, sessionid, boardid)
    leaderboard = LeaderBoard(
        title=title,
        score=scoredict,
        year=year,
        highestday=25,
        namemap=namemap,
        global_scores=global_scores)
    # leaderboard.update_global_scores()
    leaderboard.post_process_stats()
    logger.info(f"Generated data for {leaderboard.title}-{leaderboard.year}")
    jse = jsextractor(leaderboard)

    generate_data(leaderboard, "table-dailyposition", jse.daily_position)
    generate_data(leaderboard, "table-accumulated_score", jse.accumulated_score)
    generate_data(leaderboard, "table-time_to_complete", jse.time_to_complete)
    generate_data(leaderboard, "table-offset_from_winner", jse.offset_from_winner)
    generate_data(leaderboard, "table-accumulated_solve_time", jse.accumulated_solve_time)
    generate_data(leaderboard, "table-time_to_second_star", jse.time_to_second_star)
    generate_data(leaderboard, "table-score_diff", jse.score_diff)
    generate_data(leaderboard, "table-global_score", jse.global_score)
    generate_data(leaderboard, "table-tobii_score", jse.tobii_score)
    generate_data(leaderboard, "table-accumulated_position", jse.accumulated_position)

    generate_data(leaderboard, "graph-accumulated_position_graph", jse.accumulated_position_graph)
    generate_data(leaderboard, "graph-scorediff_graph", jse.scorediff_graph)
    generate_data(leaderboard, "graph-daily_position_graph", jse.daily_position_graph)

    generate_data(leaderboard, "var-config", jse.config)

    for process in threads:
        process.join()


def get_config(filename):
    with open(filename, encoding='utf-8') as f:
        return json.load(f)


config = get_config("boards.json")
namemap = get_config("namemap.json")
if __name__ == "__main__":
    for c in config:
        sessionid = c['sessionid']
        year = c.get('years', ["2020"])[0]
        boardid = c['boardid']
        title = c['title']
        generatelist(
            sessionid=sessionid,
            year=year,
            title=title,
            boardid=boardid,
            namemap=namemap.get(c['boardid'], {}),
            global_scores={'names': []})
