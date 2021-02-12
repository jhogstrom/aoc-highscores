import boto3
import os
import json

config_table_name = os.environ.get("DDB_CONFIG", "scoreboard-boardconfig")
config_table = boto3.resource('dynamodb').Table(config_table_name)
namemap_table_name = os.environ.get("DDB_NAMEMAP", "scoreboard-namemap")
namemap_table = boto3.resource('dynamodb').Table(namemap_table_name)

def add_board_config():
    with open("boards.json") as f:
        board_configs = json.loads(f.read())

    with config_table.batch_writer() as batch:
        for c in board_configs:
            print(f"Adding {c['boardid']}")
            batch.put_item(Item={
                "id": c['boardid'],
                "config": c
            })

def add_namemaps():
    with open("namemap.json") as f:
        namemaps = json.loads(f.read())

    with namemap_table.batch_writer() as batch:
        for m in namemaps:
            for name in namemaps[m]:
                print(f"Saving map {m}: {name} -> {namemaps[m][name]}")
                batch.put_item(Item={
                    "id": f"{m}",
                    "name": name,
                    "value": namemaps[m][name]
                })


add_board_config()
add_namemaps()