import boto3
import os
import json
import logging
import datetime
import pytz

# logging.basicConfig(level=logging.DEBUG)

config_table_name = os.environ.get("DDB_CONFIG", "scoreboard-boardconfig")
config_table = boto3.resource('dynamodb').Table(config_table_name)

timestamps_table_name = os.environ.get("DDB_TIMESTAMPS", "scoreboard-timestamps")
timestamps_table = boto3.resource('dynamodb').Table(timestamps_table_name)

queue_name = os.environ.get('SQS_GENERATOR', "scoreboard-generator_queue")
queue = boto3.resource('sqs').get_queue_by_name(QueueName=queue_name)

def sqs_message(msg: dict) -> dict:
    """
    Wrap msg in a message suited for SQS.

    Args:
        msg (dict): The dictionary that goes into MessageBody

    Returns:
        dict: A message to send to SQS
    """
    return {
            'Id': msg['boardid'],
            'MessageBody': json.dumps(msg)
        }

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

def get_timestamps() -> dict:
    """
    Fetch the timestamps of the generated files and
    return in map(<year|boardid> -> timestamp)

    Returns:
        dict: Disctionary mapping <year>|<boardid> -> timestamp
    """
    result = {}
    for item in scan_table(timestamps_table):
        result[item['id']] = item['lastgen']
    return result

def should_send_message(timestamps: dict, msg: dict) -> bool:
    """
    Determine of the message should be sent.

    The message is sent of there is no prior record or if the
    age of the last generated file is greater than the cool off period.

    The cool off period is:
    * 2 weeks if the requsted year is not current year
    * 2 weeks if the current month is not December
    * 8 hours if the current day is after the 25th
    * 1 hours if the current time is more than 01:00 (America/New York)
    * 2 minutes if the current time is earlier than 01:00 (America/New York)

    Args:
        timestamps (dict): Last file generation timestamps
        msg (dict): msg with boardinfo

    Returns:
        bool: True if the board requires regeneration
    """
    if not msg:
        return False

    last_msg = timestamps.get(f"{msg['year']}|{msg['boardid']}", None)
    if not last_msg:
        return True

    last_time = datetime.datetime.fromtimestamp(last_msg)
    tz = pytz.timezone('America/New_York')
    now = datetime.datetime.now(tz=tz)
    age = now - last_time

    if msg['year'] != now.year:
        cool_off = datetime.timedelta(weeks=2)
    elif now.month != 12:
        cool_off = datetime.timedelta(weeks=2)
    elif now.day > 25:
        cool_off = datetime.timedelta(hours=8)
    elif now.hour >= 1:
        cool_off = datetime.timedelta(hours=1)
    else:
        cool_off = cool_off = datetime.timedelta(minutes=2)

    logging.debug(f"{msg['year']}|{msg['boardid']}: last_time: {last_time} age: {age}, cool_off: {cool_off}. Regenerate: {age > cool_off}")

    return age > cool_off



def generate_messages():
    timestamps = get_timestamps()
    messages = []

    # read all records from config_table
    # create and post a queue message for each record
    for item in scan_table(config_table):
        config = item.get('config', None)
        if config is None:
            logging.warning(f'Missing config: {item}')
            continue

        for year in config['years']:
            msg = {
                'boardid': config['boardid'],
                'sessionid': config['sessionid'],
                'title': config['title'],
                'year': year,
                'uuid': config.get('uuid', config['boardid'])
            }

            if should_send_message(timestamps, msg):
                messages.append(sqs_message(msg))

    if messages:
        queue.send_messages(Entries=messages)
    return len(messages)


def main(event, context):
    n = generate_messages()
    logging.info(f'Sent {n} messages.')

if __name__ == "__main__":
    n = generate_messages()
    print(f"Sent {n} messages...")
    raise Exception("This is just a module!")