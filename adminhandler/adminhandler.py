import boto3
import os
import json
import uuid
import datetime
import logging

from pprint import pprint


config_table_name = os.environ.get("DDB_CONFIG", "scoreboard-boardconfig")
config_table = boto3.resource('dynamodb').Table(config_table_name)


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


def response(*, body: str = None, status: int = None, headers: dict = None) -> dict:
    if headers is None:
        headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        }
    res = {
        "statusCode": status or 200,
        'headers': headers
    }
    if body is not None:
        res['body'] = body
    return res


def error_response(paths: str, verb: str, body: dict, *, message: str = None) -> dict:
    return response(status=500, body=json.dumps(
        [
            f"Illegal combination: '{paths}' and '{verb}'",
            message
        ]))


def options_response():
    return response(status=100, headers={
        "Content-Type": "application/json",
        "Allow": "OPTIONS, GET, HEAD, POST",
        "Access-Control-Allow-Methods": "OPTIONS, GET, HEAD, POST",
        "Access-Control-Allow-Origin": "*"
    })


def get_boards():
    return [item['config'] for item in scan_table(config_table)]


def handle_list_request(paths: str, verb: str, body: dict) -> dict:
    print(f"List request: {paths} -- {verb}")
    if paths[0] == "boards":
        return response(body=json.dumps(get_boards()))
    return None


def handle_update_request(paths: str, verb: str, body: dict) -> dict:
    if paths[0] == 'boards':
        for board in body.get('boards', []):
            item = {
                'id': board['boardid'],
                'config': board
            }
            config_table.put_item(Item=item)
        return response()
    return None


def handle_add_request(paths: str, verb: str, body: dict) -> dict:
    if paths[0] == "board":
        item = {
            'id': body['id'],
            'config': {
                'boardid': body['id'],
                'uuid': str(uuid.uuid1()),
                'sessionid': "<missing>",
                'title': "<new board>",
                'years': [str(datetime.datetime.now().year)]
            }
        }
        print(f"Adding: {item}")
        try:
            res = config_table.put_item(Item=item)
            print(res)
            return response(status=200, body=json.dumps(res))
        except Exception as e:
            logging.exception(e)


def handle_request(paths: str, verb: str, body: dict) -> dict:
    print(f"Requesting: {paths} -- {verb}")
    if paths[0] == "list":
        return handle_list_request(paths[1:], verb, body)
    if paths[0] == "update":
        return handle_update_request(paths[1:], verb, body)
    if paths[0] == "add":
        return handle_add_request(paths[1:], verb, body)

    return None


def main(event, context):
    try:
        # pprint(event)
        path = event.get('path', "")
        verb = event.get('httpMethod', "")
        body = json.loads(event.get('body', "{}") or "{}")
        print(f"Request: {path} // {verb} -- body:")
        pprint(body)
        if verb == "OPTIONS":
            return options_response()

        res = handle_request(path.split('/')[1:], verb, body)
        if res is not None:
            return res
        return error_response(path, verb, body)
    except Exception as e:
        return response(status=500, body=json.dumps(str(e)))


if __name__ == "__main__":
    r = main({'path': '/list/boards', 'httpMethod': "GET", 'body': None}, None)
    print(r)
