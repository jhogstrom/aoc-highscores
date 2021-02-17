import os
import boto3
import json
import scores
import scoreboard
import datetime
import pytz
import logging
from botocore.exceptions import ClientError

cache_bucket_name = os.environ.get("S3_DATACACHE", "scoreboard-datacache")
s3client, s3resource = boto3.client('s3'), boto3.resource('s3')
logger = logging.getLogger("aoc")

class S3Cache(scores.Cache):
    def __init__(self,
            bucket_name: str):
        super().__init__()
        self._ramcache = {}
        self.bucket_name = bucket_name
        self.item_ages = {}

    def item_date(self, representation: scores.DataRepresentation) -> bool:
        return self.item_ages.get(representation)

    def has_data(self, representation: scores.DataRepresentation) -> bool:
        if representation in self._ramcache:
            return True

        try:
            logger.debug(f"Looking for '{representation.filename()} in bucket {self.bucket_name}.")
            response = s3client.head_object(
                Bucket=self.bucket_name,
                Key=representation.filename())
            logger.debug(f"Found file. Timestamp: {response['Metadata'].get('timestamp')}")
            tz = pytz.timezone('America/New_York')
            now = datetime.datetime.now(tz=tz)
            last_timestamp = int(response['Metadata'].get('timestamp', '0'))
            last_filedate = datetime.datetime.fromtimestamp(last_timestamp, tz)
            self.item_ages[representation] = last_filedate
            age = now.timestamp() - last_timestamp

            if last_filedate.year != now.year:
                cool_off = datetime.timedelta(weeks=2)
            elif now.month != 12:
                cool_off = datetime.timedelta(weeks=2)
            elif now.day > 25:
                cool_off = datetime.timedelta(hours=8)
            elif now.hour >= 3:
                cool_off = datetime.timedelta(hours=1)
            else:
                cool_off = datetime.timedelta(minutes=2)
            # cool_off = datetime.timedelta(seconds=2)

            logger.debug(f"Using a cool off period of {int(cool_off.total_seconds())} seconds. Can use cached version? {age < cool_off.total_seconds()}")
            return age < cool_off.total_seconds()

        except ClientError as e:
            logger.exception(e)
            return False


    def add_data(self, representation: scores.DataRepresentation, data) -> None:
        tz = pytz.timezone('America/New_York')
        item_time = datetime.datetime.now(tz=tz)
        self.item_ages[representation] = item_time
        self._ramcache[representation] = data
        logger.debug(f"Puttin {representation.filename()} -> {self.bucket_name}.")

        s3client.put_object(
            Body=data,
            Bucket=self.bucket_name,
            Key=representation.filename(),
            Metadata={'timestamp': str(int(item_time.timestamp()))
        })

    def get_raw(self, representation) -> str:
        if representation in self._ramcache:
            return self._ramcache[representation]
        o = s3resource.Object(cache_bucket_name, representation.filename())
        response = o.get()
        return response['Body'].read().decode("utf-8")

if __name__ == "__main__":
    raise Exception("This is just a module!")