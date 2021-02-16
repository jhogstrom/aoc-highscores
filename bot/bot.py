import json
import os
import urllib
import uuid
import datetime
import logging
import requests
from urllib import parse
from urllib import request
from urllib.parse import urlparse
import boto3
from boto3.dynamodb.conditions import Attr

config_table_name = os.environ.get("DDB_CONFIG", "scoreboard-boardconfig")
config_table = boto3.resource('dynamodb').Table(config_table_name)

namemap_table_name = os.environ.get("DDB_NAMEMAP", "scoreboard-namemap")
namemap_table = boto3.resource('dynamodb').Table(namemap_table_name)


def read_token_from_file(filename: str):
    if not os.path.exists(filename):
        return ""
    with open(filename) as f:
        return f.readline().strip()

bot_token = os.environ.get("BOT_TOKEN", read_token_from_file('slack_bot_token.txt'))
verification_token = os.environ.get("BOT_VERIFICATION", read_token_from_file('slack_verification_token.txt'))
previous_events = []

def scan_table(table, **scan_kwargs):
    done = False
    start_key = None
    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        for item in items:
            yield item
        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None


def get_board(boardid: str) -> dict:
    res = config_table.get_item(Key={'id': boardid})
    return res.get('Item')


def list_boards() -> str:
    result = ["Available boards:"]
    for item in scan_table(config_table):
        config = item['config']
        result.append(f"* >>{config['title']}<< ({config['boardid']}) -- {config['years']} [{config['sessionid']}]")
    return "\n".join(result)


def list_namemaps(boardid: str = None) -> str:
    args = {}
    if boardid is not None:
        args['FilterExpression'] = Attr('id').eq(boardid)
    res = ["Available name maps:"]
    for item in scan_table(namemap_table, **args):
        res.append(f"\t{item['id']:>6}: {item['name']} -> {item['value']}")
    return "\n".join(res)


def add_namemap(boardid: str, name: str, value):
    if not (boardid and name and value):
        return "Correct format: add namemap <boardid> <name> <map>"

    board = get_board(boardid)
    if not board:
        return f"No board with id '{boardid}'."

    item = {
        'id': boardid,
        'name': name,
        'value': " ".join(value)
    }

    namemap_table.put_item(Item=item)
    return f"Added map for '{name}' -> '{value}' in {boardid}"


def add_board(boardid: str, sessionid: str, title) -> str:
    if not (boardid and sessionid and title):
        return "Correct format: add board <boardid> <sessionid> <title>"

    year = str(datetime.date.today().year)
    title = " ".join(title)

    item = {
        'id': boardid,
        'config': {
            'boardid': boardid,
            'sessionid': sessionid,
            'title': title,
            'years': [year],
            'uuid': str(uuid.uuid1())
        }
    }
    config_table.put_item(Item=item)
    return f"Added board {boardid} //{title}// for {year}."


def extend_board(boardid: str, year: str) -> str:
    if not (boardid and year):
        return "Correct format: extend board <boardid> <year>"

    item = get_board(boardid)
    if not item:
        return f"No board with id '{boardid}'."

    if year in item['config']['years']:
        return f"Board '{boardid}' already set up for {year}."

    item['config']['years'].append(year)

    config_table.put_item(Item=item)

    return f"Extended board {boardid} for {year}."


def process_command(command: str) -> str:
    def help_text(cmd):
        return f'''
Valid commands:
* list boards
* list namemaps [<boardid>]
* add board <boardid> <sessionid> <title>
* add namemap <boardid> <name> <map>
* extend board <boardid> <year>
'''
    def get_part(parts, ix: int) -> str:
        if ix < len(parts):
            return parts[ix]
        return None

    logging.info(f"Processing '{command}'.")

    parts = command.split()
    if len(parts) == 0:
        return "No command received"
    cmd = parts[0]
    request = f"** Request: [{command}] **\n\n"

    if cmd in ["help", "?", "-?", "--help", "info", "/?"]:
        return request + help_text(cmd)

    if cmd == "list" and get_part(parts, 1) == "boards":
        return request + list_boards()

    if cmd == "list" and get_part(parts, 1) == "namemaps":
        return request + list_namemaps(get_part(parts, 2))

    if cmd == "add" and get_part(parts, 1) == "namemap":
        return request + add_namemap(get_part(parts, 2), get_part(parts, 3), parts[4:])

    if cmd == "add" and get_part(parts, 1) == "board":
        return request + add_board(get_part(parts, 2), get_part(parts, 3), parts[4:])

    if cmd == "extend" and get_part(parts, 1) == "board":
        return request + extend_board(get_part(parts, 2), get_part(parts, 3))

    return request + f'"{cmd}" not implemented\n{help_text(cmd)}'


def respond_to_im(channel_id: str, response: str) -> None:
    logging.info("Messaging Slack...")
    SLACK_URL = "https://slack.com/api/chat.postMessage"

    data = parse.urlencode(
        (
            ("token", bot_token),
            ("channel", channel_id),
            ("text", response)
        )
    )
    data = data.encode("ascii")

    req = request.Request(SLACK_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    # Fire off the request!
    from_request = request.urlopen(req).read()
    logging.debug(f"Request returned: {from_request}.")

def respond_to_command(response_url: str, response: str) -> None:
    headers = {"Content-Type": "application/json"}
    data = {
        'text': response
    }
    r = requests.request("POST", response_url, data=data, headers=headers)
    logging.debug(f"Request returned: {r} - {r.content}.")


def message_from_bot(body: dict):
    if not body:
        return True

    return body.get('event', {}).get('bot_id')


def is_duplicate(event_id: str) -> bool:
    res = event_id in previous_events
    if not res:
        previous_events.append(event_id)
    return res


def verify_token(token: str) -> bool:
    return token == verification_token


def main(event, context):
    logging.debug(f"Received event:\n{event}")
    content_type = event.get('headers', {}).get('Content-Type', "")
    if "challenge" in event:
        return {
            'statusCode': 200,
            'body': event["challenge"]
        }


    if content_type == 'application/json':
        logging.info("direct message")
        body = json.loads(event.get("body", "{}"))
        loggin.debug(f"Body: {body}")

        challenge_answer = body.get("challenge", "NOT FOUND")

        if message_from_bot(body) or is_duplicate(body.get('event_id')):
            logging.info("Message dropped. Dupe or bot message.")
            return "200 OK"

        if not verify_token(body.get('token')):
            logging.info(f"Message dropped. Wrong verification token. Exp: {verification_token} got {body.get('token')}")
            return "200 OK"

        channel_id = body.get('event', {}).get('channel')
        command = body.get('event', {}).get('text')
        response = process_command(command)
        respond_to_im(channel_id, response)
    elif content_type == 'application/x-www-form-urlencoded':
        logging.info("slash command")
        body = dict(urllib.parse.parse_qsl(event.get('body')))
        if not verify_token(body.get('token')):
            logging.debug("Message dropped. Wrong verification token.")
            return "200 OK"
        channel_id = body.get('channel_id')
        command = body.get('text')
        response = process_command(command)
        # respond_to_command(body.get('response_url'), response)
        respond_to_im(channel_id, response)
        return {
            'headers': { "Content-Type": "application/json" },
            'body': json.dumps(
                {
                    'text': f"Hope that helped!",
                }),
        }
    else:
        logging.warning(f"Unknown content-type: {content_type}.")

    return "200 OK"

if __name__ == "__main__":
    s = "token=KvH8HaKiV9qmNEnqHULDVFUm&team_id=T010ZU25PGQ&team_domain=salgs&channel_id=D01KPK9BQ2X&channel_name=directmessage&user_id=U010ZSN6QER&user_name=jspr.hgstrm&command=%2Flist&text=boards&api_app_id=A01KNCASSFL&is_enterprise_install=false&response_url=https%3A%2F%2Fhooks.slack.com%2Fcommands%2FT010ZU25PGQ%2F1682512109745%2FGFkXkB7v3dxbHs8klVN2IGij&trigger_id=1663106876214.1033954193568.6ca8825c33af40aee1058cc4a0c99c2a"
    o = urllib.parse.parse_qsl(s)
    o = dict(o)
    print(o)
    print(o['response_url'])
    exit()
    print(bot_token)
    handle_message(
        {
            'event':
            {
                "text": "add namemap 34481 jhm jesper högström",
                "channel":"D01KPK9BQ2X",
            }
        })