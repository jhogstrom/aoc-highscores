from aws_cdk import (
    core,
    aws_lambda_event_sources,
    aws_dynamodb,
    aws_s3
)
import aws
import os

DESTROY=core.RemovalPolicy.DESTROY
RETAIN=core.RemovalPolicy.RETAIN

EPHEMERALDATA=DESTROY
CONFIGDATA=DESTROY

def read_token_from_file(filename: str) -> str:
    if not os.path.exists(filename):
        return ""
    with open(filename) as f:
        return f.readline().strip()


class ScoreboardStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        layer = aws.PipLayers(
            self,
            "scoreboard_layer",
            layers={
                "htmlgen": "htmlgen/requirements.txt",
                "parse_globals": "parse_globals/requirements.txt",
                "bot": "bot/requirements.txt"
            })

        # Create
        # * the generator function
        # * Namemap-table
        #   * allow generator to read from namemap-table
        #   (This might change - why not pass the mapping structure in the message?)
        # * Datacache-bucket
        #   * Allow generator to read and write to bucket

        htmlgen = aws.Function(self,
            "htmlgen",
            layers=layer.layers,
            timeout=core.Duration.seconds(20),
            memory_size=1024)

        # id: str (boardid), name: str (username), value: str (replacement value)
        namemap = aws.Table(self,
            "namemap",
            sort_key=aws_dynamodb.Attribute(
                name='name',
                type=aws_dynamodb.AttributeType.STRING),
                removal_policy=CONFIGDATA)
        namemap.grant_read_data(htmlgen)

        # id: str (boardid), day: int, results_1: dict ({player: score, ...}), results_2: dict ({player: score, ...})
        globalscores = aws.Table(self,
            "globalscores",
            partition_key=aws_dynamodb.Attribute(
                name='year',
                type=aws_dynamodb.AttributeType.NUMBER),
            sort_key=aws_dynamodb.Attribute(
                name='day',
                type=aws_dynamodb.AttributeType.NUMBER),
            removal_policy=EPHEMERALDATA)
        parse_globals = aws.Function(self,
            "parse_globals",
            layers=layer.layers,
            timeout=core.Duration.seconds(20),
            memory_size=1024)
        parse_globals.add_environment("DDB_GLOBALSCORES", globalscores.table_name)
        globalscores.grant_read_write_data(parse_globals)
        globalscores.grant_read_data(htmlgen)

        timestamps = aws.Table(self,
            "timestamps",
            removal_policy=EPHEMERALDATA)
        htmlgen.add_environment("DDB_TIMESTAMPS", timestamps.table_name)
        timestamps.grant_write_data(htmlgen)

        datacache = aws.Bucket(self, "datacache")
        datacache.grant_read_write(htmlgen)

        htmlbucket = aws.Bucket(self,
            "html",
            removal_policy=EPHEMERALDATA,
            auto_delete_objects=True,
            block_public_access=None,
            website_error_document="error.html",
            website_index_document="index.html")
        htmlbucket.grant_public_access()
        core.CfnOutput(
                self,
                f"{id}_bucketurl",
                value=f"BUCKET_URL={htmlbucket.bucket_website_url}")
        htmlbucket.grant_read_write(htmlgen)
        htmlgen.add_environment("S3_DATACACHE", datacache.bucket_name)
        htmlgen.add_environment("S3_HTML", htmlbucket.bucket_name)
        htmlgen.add_environment("DDB_NAMEMAP", namemap.table_name)


        # Create
        # * spawner function
        # * boardconfig-table
        #   * allow spawner to read from boardconfig-table
        # * generator_queue
        #   allow spawner to post messages to queue
        spawner = aws.Function(self,
            "spawner",
            layers=layer.layers)
        boardconfig = aws.Table(self,
            "boardconfig",
            removal_policy=CONFIGDATA)
        boardconfig.grant_read_data(spawner)
        spawner.add_environment("DDB_CONFIG", boardconfig.table_name)

        generator_queue = aws.Queue(self, "generator_queue")
        generator_queue.grant_send_messages(spawner)
        spawner.add_environment("SQS_GENERATOR", generator_queue.queue_name)
        spawner.add_environment("DDB_TIMESTAMPS", timestamps.table_name)
        timestamps.grant_read_data(spawner)

        # Connect the generator_queue to the htmlgen-function
        event_source = aws_lambda_event_sources.SqsEventSource(generator_queue, batch_size=10)
        htmlgen.add_event_source(event_source)


        # Slack API
        api = aws.RestApi(self, "slack")

        slack = aws.ResourceWithLambda(
            self,
            "bot",
            verb="POST",
            description="Handle incoming Slack-bot interaction",
            parent_resource=api.root,
            lambda_layers=[layer.idlayers["bot"]])
        slack.handler.add_environment("BOT_TOKEN", read_token_from_file('slack_bot_token.txt'))
        slack.handler.add_environment("BOT_VERIFICATION", read_token_from_file('slack_verification_token.txt'))
        #"xoxb-1033954193568-1654676166455-Vzom9aQY9NUjAYR5mhKZP70k")
        slack.handler.add_environment("DDB_CONFIG", boardconfig.table_name)
        slack.handler.add_environment("DDB_NAMEMAP", namemap.table_name)
        namemap.grant_read_write_data(slack.handler)
        boardconfig.grant_read_write_data(slack.handler)



