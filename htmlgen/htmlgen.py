import os
import json
import boto3
from boto3.dynamodb.conditions import Key
import aocgen
import logging
import datetime
import pytz

namemap_table_name = os.environ.get("DDB_NAMEMAP", "scoreboard-namemap")
namemap_table = boto3.resource('dynamodb').Table(namemap_table_name)

globalscores_table_name = os.environ.get("DDB_GLOBALSCORES", "scoreboard-globalscores")
globalscores_table = boto3.resource('dynamodb').Table(globalscores_table_name)

timestamps_table_name = os.environ.get("DDB_TIMESTAMPS", "scoreboard-timestamps")
timestamps_table = boto3.resource('dynamodb').Table(timestamps_table_name)


COL_LISTSIZE = 'listsize'
COL_ID = 'year'
COL_DAY = 'day'
COL_RESULTS = 'results'

logging.basicConfig(level=logging.INFO)


global_scores = {}

def handle_record(*,
        boardid: str,
        year: str,
        namemap: dict,
        sessionid: str,
        title: str,
        uuid: str):
    boardid = msg.get('boardid')
    namemap = get_namemap(boardid)
    sessionid = msg.get('sessionid')
    title = msg.get('title')
    year = msg.get('year')

    print(f"Generating html for {title} ({boardid}) -- {year}.")
    tz = pytz.timezone('America/New_York')
    now = datetime.datetime.now(tz=tz).timestamp()
    timestamps_table.put_item(Item={
        "id": f"{year}|{boardid}",
        "lastgen": int(now)
    })

    aocgen.generatelist(
        boardid=boardid,
        year=year,
        namemap=namemap,
        sessionid=sessionid,
        title=title,
        uuid=uuid,
        global_scores=global_scores[year])


def get_namemap(boardid: str) -> dict:
    if not boardid:
        return {}
    print(f"Getting name maps for {boardid}")
    response = namemap_table.query(KeyConditionExpression=Key('id').eq(boardid))
    return {_['name']: _['value'] for _ in response['Items']}


def get_global_scores(years: set):
    for year in years:
        if year in global_scores:
            continue
        names = set()
        logging.info(f"Getting stored data for {year}")
        response = globalscores_table.query(KeyConditionExpression=Key(COL_ID).eq(int(year)))
        items = response.get('Items', {})
        scores = {}
        for item in items:
            scores[int(item[COL_DAY])] = item[COL_RESULTS]
            for _ in item[COL_RESULTS]:
                names.update(_)
        global_scores[year] = {'scores': scores, 'names': names}
        logging.debug(f"Loaded global data for {year}")


def process_messages(messages):
    if not messages:
        logging.warning("No records detected")
        return

    years = {json.loads(msg['body'])['year'] for msg in messages}
    get_global_scores(years)

    for msg in messages:
        try:
            msgstruct = json.loads(msg['body'])
            handle_record(
                boardid=msg['boardid'],
                year=msg['year'],
                namemap=get_namemap(msg['boardid']),
                sessionid=msg['sessionid'],
                title=msg['title'],
                uuid=msg['uuid'])
        except Exception as e:
            logging.exception(e)


def main(event, context):
    try:
        messages = event.get('Records', [])
        print(messages)
        process_messages(messages)
    except Exception as e:
        logging.exception(e)


if __name__ == "__main__":
    main(
        {
            'Records': [
                {
                    'messageId': 'c4a35f21-8ff4-4d28-8fb5-5be7cc73e3cf',
                    'receiptHandle': 'AQEBJfl0cnboalgoOsa1IstXAhAcltbpohFQI4q2mF3wiIo9fJMnG6Z0AOMaf/eXEm58cKWGDtT5YCD4SR20X5lpjP0CsMsO8XoK3QKvm/go9Ojp8osoe0OJHr513UDMvQCq6/K3FgSg0P17ZOps48mTvjpeCD750jtQh3rhII2ICK9WFWW9WGWIraeMqvPaY+BkTo2lJnOpWx90NI2MhO1Vqw6iSIx/N4VZyk+lWnzfce9Yf/qcvJmvLwhCADgP4J0LLjsi6BK4XGlHGTx/Ys/4WkF5BaLOQRn19cD5tg3NTDlEfCmgquhmJXm6a7hxlQx+SN+PSVe0UZoV0PzL/haZIs/jSd7O9VrG1F8HkchdHR5bmHlxNdAKV/wBA12GfZtq21OwF6GlITk58ICtGZYjow==',
                    'body': '{"boardid": "34481", "sessionid": "53616c7465645f5f538e95e0d6938f92cb62df52473d36ce5e269046fd7d5eeaccd579aec170a66b1eec0f1eacfbdcfa", "title": "Leica foo bar fighters", "year": "2020", "uuid": "21ae6a02-ec22-469e-ae39-c63e921b309b"}',
                    'attributes': {
                        'ApproximateReceiveCount': '1',
                        'SentTimestamp': '1611374547103',
                        'SenderId': 'AIDATWEHKP6C6UE5CR6OC',
                        'ApproximateFirstReceiveTimestamp':
                        '1611374547106'},
                    'messageAttributes': {},
                    'md5OfBody': 'e236be6889dccab4a6ca3498ef541f73',
                    'eventSource': 'aws:sqs',
                    'eventSourceARN': 'arn:aws:sqs:us-east-2:253686873989:scoreboard-generator_queue',
                    'awsRegion': 'us-east-2'
                }
            ]
        },
        None)
    # get_global_scores({2020})
    # print(get_namemap("34481"))
    raise Exception("This is just a module!")