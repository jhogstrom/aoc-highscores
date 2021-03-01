from aws_cdk import (
    core,
    aws_apigateway,
    aws_lambda_event_sources,
    aws_dynamodb,
    aws_s3,
    aws_s3_deployment,
    aws_lambda,
    aws_events
)
import aws
import os


DESTROY = core.RemovalPolicy.DESTROY
RETAIN = core.RemovalPolicy.RETAIN

EPHEMERALDATA = DESTROY
CONFIGDATA = DESTROY


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

        htmlgen = aws.Function(
            self,
            "htmlgen",
            layers=layer.layers,
            timeout=core.Duration.seconds(20),
            memory_size=1024)

        # id: str (boardid), name: str (username), value: str (replacement value)
        namemap = aws.Table(
            self,
            "namemap",
            sort_key=aws_dynamodb.Attribute(
                name='name',
                type=aws_dynamodb.AttributeType.STRING),
            removal_policy=CONFIGDATA)
        namemap.grant_read_data(htmlgen)

        no_point_days = aws.Table(
            self,
            "nopointdays")

        # id: str (boardid), day: int, results_1: dict ({player: score, ...}), results_2: dict ({player: score, ...})
        globalscores = aws.Table(
            self,
            "globalscores",
            partition_key=aws_dynamodb.Attribute(
                name='year',
                type=aws_dynamodb.AttributeType.NUMBER),
            sort_key=aws_dynamodb.Attribute(
                name='day',
                type=aws_dynamodb.AttributeType.NUMBER),
            removal_policy=EPHEMERALDATA)
        parse_globals = aws.Function(
            self,
            "parse_globals",
            layers=layer.layers,
            timeout=core.Duration.seconds(20),
            memory_size=1024)
        parse_globals.add_environment("DDB_GLOBALSCORES", globalscores.table_name)
        globalscores.grant_read_write_data(parse_globals)
        globalscores.grant_read_data(htmlgen)

        timestamps = aws.Table(
            self,
            "timestamps",
            removal_policy=EPHEMERALDATA)
        htmlgen.add_environment("DDB_TIMESTAMPS", timestamps.table_name)
        timestamps.grant_write_data(htmlgen)

        datacache = aws.Bucket(self, "datacache")
        datacache.grant_read_write(htmlgen)

        htmlbucket = aws.Bucket(
            self,
            "html",
            removal_policy=EPHEMERALDATA,
            auto_delete_objects=True,
            block_public_access=None,
            website_error_document="error.html",
            website_index_document="scoreboard.html",
            cors=[aws_s3.CorsRule(
                allowed_methods=[aws_s3.HttpMethods.GET],
                allowed_headers=["*"],
                allowed_origins=["*"])])
        htmlbucket.grant_public_access()
        core.CfnOutput(
                self,
                f"{id}_bucketurl",
                value=f"BUCKET_URL={htmlbucket.bucket_website_url}")
        htmlbucket.grant_read_write(htmlgen)
        htmlgen.add_environment("S3_DATACACHE", datacache.bucket_name)
        htmlgen.add_environment("S3_HTML", htmlbucket.bucket_name)
        htmlgen.add_environment("DDB_NAMEMAP", namemap.table_name)

        aws_s3_deployment.BucketDeployment(
            self, "StaticHtml",
            sources=[aws_s3_deployment.Source.asset("htmlgen/frontend")],
            destination_bucket=htmlbucket,
            prune=False)

        # Create
        # * spawner function
        # * boardconfig-table
        #   * allow spawner to read from boardconfig-table
        # * generator_queue
        #   allow spawner to post messages to queue
        spawner = aws.Function(
            self,
            "spawner",
            layers=layer.layers)
        boardconfig = aws.Table(
            self,
            "boardconfig",
            stream=aws_dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy=CONFIGDATA)
        boardconfig.grant_read_data(spawner)
        spawner.add_environment("DDB_CONFIG", boardconfig.table_name)
        spawner.add_environment("DDB_NOPOINTDAYS", no_point_days.table_name)

        boardconfig_source = aws_lambda_event_sources.DynamoEventSource(
            boardconfig,
            starting_position=aws_lambda.StartingPosition.LATEST
        )

        boarddeletions = aws.Function(self, "boarddeletions")
        boarddeletions.add_event_source(boardconfig_source)
        boarddeletions.add_environment("S3_HTML", htmlbucket.bucket_name)
        htmlbucket.grant_read_write(boarddeletions)

        generator_queue = aws.Queue(self, "generator_queue")
        generator_queue.grant_send_messages(spawner)
        spawner.add_environment("SQS_GENERATOR", generator_queue.queue_name)
        spawner.add_environment("DDB_TIMESTAMPS", timestamps.table_name)
        timestamps.grant_read_data(spawner)

        # Connect the generator_queue to the htmlgen-function
        event_source = aws_lambda_event_sources.SqsEventSource(generator_queue, batch_size=10)
        htmlgen.add_event_source(event_source)

        # Admin API
        adminhandler = aws.Function(self, "adminhandler")
        adminhandlerApi = aws_apigateway.LambdaRestApi(
            self,
            "adminapi",
            handler=adminhandler)
        core.CfnOutput(self, "root_url", value=f"Admin URL={adminhandlerApi.url_for_path()}")
        adminhandler.add_environment("DDB_CONFIG", boardconfig.table_name)
        boardconfig.grant_read_write_data(adminhandler)

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
        # "xoxb-1033954193568-1654676166455-Vzom9aQY9NUjAYR5mhKZP70k")
        slack.handler.add_environment("DDB_CONFIG", boardconfig.table_name)
        slack.handler.add_environment("DDB_NAMEMAP", namemap.table_name)
        namemap.grant_read_write_data(slack.handler)
        boardconfig.grant_read_write_data(slack.handler)

        # aws.Rule(
        #     self,
        #     "Test",
        #     description="Remove after functions verified - Fire every minute for some duration in Februaryx",
        #     schedule=aws_events.Schedule.cron(minute="*", hour="*", week_day="2", month="FEB"),
        #     target=spawner)

        aws.Rule(
            self,
            "RestOfYear",
            description="Fire every week jan-novx",
            schedule=aws_events.Schedule.cron(minute="0", hour="4", week_day="2", month="JAN-NOV"),
            target=spawner)
        aws.Rule(
            self,
            "Mornings_December",
            description="Every second minute 06-08 (CET) 1-25 decx",
            schedule=aws_events.Schedule.cron(minute="0/2", hour="6-7", day="1-25", month="DEC"),
            target=spawner)
        aws.Rule(
            self,
            "Daytime_December",
            description="Every 20 minutes 08-15 (CET) 1-25 decx",
            schedule=aws_events.Schedule.cron(minute="0/20", hour="8-15", day="1-25", month="DEC"),
            target=spawner)
        aws.Rule(
            self,
            "Nighttime_December",
            description="Every hour 00-6,14-24 (CET) 1-25 decx",
            schedule=aws_events.Schedule.cron(
                minute="0",
                hour="0-6,14-23",
                day="1-25",
                month="DEC"),
            target=spawner)
        aws.Rule(
            self,
            "EndOf_December",
            description="Every hour 9-23 (CET) 25-31 decx",
            schedule=aws_events.Schedule.cron(minute="0", hour="9-23", day="26-31", month="DEC"),
            target=spawner)
