import os
import boto3
from boto3.dynamodb.types import TypeDeserializer
import concurrent.futures

html_bucket_name = os.environ.get("S3_HTML", "scoreboard-html")
html_bucket = boto3.resource('s3').Bucket(html_bucket_name)
s3client = boto3.client('s3')

serializer = TypeDeserializer()


def deserialize(data):
    if isinstance(data, list):
        return [deserialize(v) for v in data]

    if isinstance(data, dict):
        try:
            return serializer.deserialize(data)
        except TypeError:
            return {k: deserialize(v) for k, v in data.items()}
    else:
        return data


def delete_files(uuid, year):
    print(f"Scanning {year}/{uuid}/...")
    delete_keys = {}
    objects_to_delete = s3client.list_objects(
        Bucket=html_bucket_name,
        Prefix=f'{year}/{uuid}/')

    delete_keys['Objects'] = [
        {'Key': k} for k in
        [obj['Key'] for obj in objects_to_delete.get('Contents', [])]]

    # pprint(delete_keys)

    if not delete_keys['Objects']:
        print(f"No files for {year}")
        return 0

    s3client.delete_objects(
        Bucket=html_bucket_name,
        Delete=delete_keys)

    print(f"Deleted {len(delete_keys['Objects'])} files for {year}.")

    return len(delete_keys['Objects'])


def delete_project_data(uuid: str, years) -> None:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                delete_files,
                uuid, year)
            for year in years]

    return sum([f.result() for f in futures])


def handle_record(record: dict) -> None:
    newimage = deserialize(record.get("dynamodb", {}).get("NewImage"))
    oldimage = deserialize(record.get("dynamodb", {}).get("OldImage"))
    if oldimage is None:
        print(f"Could not extract oldimage from {record}")
        return
    uuid = oldimage.get("config", {}).get("uuid")
    years = oldimage.get("config", {}).get("years")
    if all([uuid, years]):
        res = delete_project_data(uuid, years)
        print(f"Total sum: {res} files deleted.")
    else:
        print(f"Unable to delete project. Uuid: {uuid}, years: {years}")
    print(newimage)
    print(oldimage)


def main(event, context):
    [handle_record(record)
        for record in event.get("Records", {})
        if record["eventName"] == "REMOVE"]

# deleteevent = {
#     'Records': [
#         {
#             'eventID': '46e536a61dbf8ec3a0876a1c7b8cc04b',
#             'eventName': 'REMOVE',
#             'eventVersion': '1.1',
#             'eventSource': 'aws:dynamodb',
#             'awsRegion': 'us-east-2',
#             'dynamodb':
#             {
#                 'ApproximateCreationDateTime': 1613692139.0,
#                 'Keys': { 'id': {'S': 'asd'}},
#                 'OldImage':
#                 {
#                     'id': {'S': 'abc'},
#                     'config':
#                     {
#                         'M':
#                         {
#                             'boardid': {'S': '34481'},
#                             'years': {'L': [{'S': '2020'}, {'S': '2019'}]},
#                             'uuid': {'S': '21ae6a02-ec22-469e-ae39-c63e921b309b'}
#                         }
#                     },
#                     'uuid': {'S': 'khghdkjhkjahdskjashd'}
#                 },
#                 'SequenceNumber': '131890300000000004272775322',
#                 'SizeBytes': 10,
#                 'StreamViewType': 'NEW_AND_OLD_IMAGES'
#             },
#             'eventSourceARN': 'arn:aws:dynamodb:us-east-2:253686873989:table/scoreboard-boardconfig/stream/2021-02-18T22:57:55.255'
#         }
#     ]}
