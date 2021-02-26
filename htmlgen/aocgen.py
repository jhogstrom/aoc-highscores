import json
import scores
import logging
import os
import boto3
import hashlib
import datetime
import math
from typing import Dict, List
from jsextractor import jsextractor
from botocore.exceptions import ClientError
import concurrent.futures

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


def file_upload(
        filekey: str,
        func) -> None:
    logger.debug(f"Uploading {filekey}?")
    data = func()
    md5 = hashlib.md5(data.encode('utf-8')).hexdigest()
    try:
        response = s3client.head_object(
            Bucket=html_bucket_name,
            Key=filekey)
        need_upload = response["Metadata"].get("md5") != md5
    except ClientError:
        need_upload = True
    except Exception as e:
        print(e)

    if need_upload:
        logger.debug(f"Pushing {filekey} to S3")
        html_bucket.put_object(
            Body=data,
            ContentType='application/json',
            Key=filekey,
            Metadata={"md5": md5})
        logger.debug("Uploading done")
    else:
        logger.debug(f"Up to date: {filekey} (no upload required)")


def generate_data(leaderboard, params: dict):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                file_upload,
                f'{leaderboard.year}/{leaderboard.uuid}/{name}.json', func)
            for name, func in params.items()]

    [f.result() for f in futures]


def get_highest_day(year: int) -> int:
    now = datetime.datetime.today()
    if now.year != year:
        return 25
    if now.month != 12:
        return 25
    return math.min([25, now.day()])


def generatelist(
        *,
        boardid: str,
        year: str,
        namemap: dict,
        sessionid: str,
        title: str,
        uuid: str,
        global_scores: dict,
        nopoint_days: List[int]):
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
        global_scores=global_scores,
        nopoint_days=nopoint_days)
    # leaderboard.update_global_scores()
    leaderboard.post_process_stats()
    logger.info(f"Generated data for {leaderboard.title}-{leaderboard.year}")
    extravars = {
        "aoc_fetch": f"{generation_date.strftime('%Y-%m-%d %H:%M:%S')} [{generation_date.tzname()}]",
        "generated": f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "nopoints": nopoint_days
    }
    print(nopoint_days)

    jse = jsextractor(leaderboard, extravars)
    generation_params = {
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

    generate_data(leaderboard, generation_params)


def get_config(filename):
    with open(filename, encoding='utf-8') as f:
        return json.load(f)


if __name__ == "__main__":
    config = get_config("boards.json")
    namemap = get_config("namemap.json")
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
                global_scores={'names': []},
                nopoint_days=[1, 2, 3])
