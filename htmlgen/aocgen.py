import json
import scores
import pathlib
import logging
import os
import boto3
import sys
from typing import Dict
from jsextractor import jsextractor

from scoreboard import LeaderBoard, ScoreboardRepresentation, BaseObj
from generator import HtmlGenerator
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
    logger.debug("Generating js-data")
    logger.info(f"Generated data for {leaderboard.title}-{leaderboard.year}")
    jse = jsextractor(leaderboard)
    jse.flush("output/tabledata.js")
    logger.debug("Done generating js-data")

    return


    filekey = f'leaderboard_{leaderboard.boardid}_{leaderboard.year}.html'
    g = HtmlGenerator(leaderboard)
    data = g.generate()
    html_bucket.put_object(
        Body=data,
        ContentType='string',
        Key=filekey)


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
