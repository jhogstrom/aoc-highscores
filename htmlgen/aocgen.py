import json
import scores
import pathlib
import logging
import os
import boto3
import sys
import hashlib
import datetime
import math
from threading import Thread
from typing import Dict
from jsextractor import jsextractor

from scoreboard import LeaderBoard, ScoreboardRepresentation
from s3cache import S3Cache

cache_bucket_name = os.environ.get("S3_DATACACHE", "scoreboard-datacache")
html_bucket_name = os.environ.get("S3_HTML", "scoreboard-html")
html_bucket = boto3.resource('s3').Bucket(html_bucket_name)
s3client = boto3.client('s3')

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


def get_data(representation: ScoreboardRepresentation, sessionid: str):
    downloader = scores.Downloader(sessionid)
    cache = S3Cache(cache_bucket_name)
    retriever = scores.DataRetriever(downloader, cache)
    return retriever.get_data(representation), cache.item_date(representation)

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

def generate_data_proc(
        filekey: str,
        func) -> None:
    logger.debug(f"Uploading {filekey}?")
    data = func()
    md5 = hashlib.md5(data.encode('utf-8')).hexdigest()
    response = s3client.head_object(
        Bucket=html_bucket_name,
        Key=filekey)
    if response["Metadata"].get("md5") != md5:
        logger.debug(f"Pushing {filekey} to S3")
        html_bucket.put_object(
            Body=data,
            ContentType='application/json',
            Key=filekey,
            Metadata={"md5": md5})
        logger.debug(f"Uploading done")
    else:
        logger.debug(f"Up to date: {filekey} (no upload required)")

def generate_data(filekey: str, func) -> None:
    process = Thread(
        target=generate_data_proc,
        args=[filekey, func])
    process.start()
    threads.append(process)

def get_highest_day(year: int) -> int:
    now = datetime.datetime.today()
    if now.year != year:
        return 25
    if now.month != 12:
        return 25
    return math.min([25, now.day()])


def generatelist(*,
        boardid: str,
        year: str,
        namemap: dict,
        sessionid: str,
        title: str,
        uuid: str,
        global_scores: dict):
    highest_day = get_highest_day(int(year))
    logger.info(f"Reading data for {title}/{year} -> day {highest_day}")
    scoredict, generation_date = get_scores(year, sessionid, boardid)
    leaderboard = LeaderBoard(
        title=title,
        score=scoredict,
        year=year,
        highestday=highest_day,
        namemap=namemap,
        uuid=uuid,
        global_scores=global_scores)
    # leaderboard.update_global_scores()
    leaderboard.post_process_stats()
    logger.info(f"Generated data for {leaderboard.title}-{leaderboard.year}")
    extravars = {
        "generated": f"{generation_date.strftime('%Y-%m-%d %H:%M:%S')} [{generation_date.tzname()}]"
    }

    jse = jsextractor(leaderboard, extravars)
    generation_params= {
        "table-dailyposition": jse.daily_position,
        "table-accumulated_score": jse.accumulated_score,
        "table-time_to_complete": jse.time_to_complete,
        "table-offset_from_winner": jse.offset_from_winner,
        "table-accumulated_solve_time": jse.accumulated_solve_time,
        "table-time_to_second_star": jse.time_to_second_star,
        "table-score_diff": jse.score_diff,
        "table-global_score": jse.global_score,
        "table-tobii_score": jse.tobii_score,
        "table-accumulated_position": jse.accumulated_position,
        "graph-accumulated_position_graph": jse.accumulated_position_graph,
        "graph-scorediff_graph": jse.scorediff_graph,
        "graph-daily_position_graph": jse.daily_position_graph,
        "var-config": jse.config
    }

    for name, func in generation_params.items():
        generate_data(f'{leaderboard.year}/{leaderboard.uuid}/{name}.json', func)

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
        boardid = c['boardid']
        title = c['title']
        uuid = c['uuid']
        for year in c.get('years', ["2020"]):
            generatelist(
                sessionid=sessionid,
                year=year,
                title=title,
                boardid=boardid,
                namemap=namemap.get(c['boardid'], {}),
                uuid=uuid,
                global_scores={'names': []})
