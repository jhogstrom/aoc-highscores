AoC Highscore generator
===

To do
===
Big
--
* Improve the documentation in this file explaining what each part does (databases, generators, frontend, slack interface)

Small
--
* Fix bugs in leaderboard (see year 2019)
* Add a generated page with links to all boards (preferably cognito-protected)
* Adjust cron jobs UTC -> EST
* Add list owner mail address in board config
* Handle fetch errors (expired sessionid) by mailing list owner
* Add DLQ for failures
* Reconsider S3 datacache-bucket. Most data is stored in Dynamo anyway...
* Reconsider all the refetch rules. Cron jobs should be enough, after that
  it's enough to wait 2-15 minutes after refreshing from AoC.
* Build dashboard+alarms in CDK
* Add links to other years for the same scoreboardid.
* ~~Figure out how to show blocked days~~
* ~~Move blocked days to database?~~
* ~~Add cronjob to regenerate files~~
* ~~Subscribe to dyndb deletions of boardtable and clean up~~
  - ~~S3-files~~
  - ~~name maps~~
* ~~Add GUID to boards~~
* ~~Use guid instead of boardID for generated files~~
* ~~Generate files into \<year>\\\<guid>\\\<file> in S3~~
* ~~Handle parameters in page~~
* ~~Generate some nicer error page if the parameters don't point to a valid file set~~
* ~~Add generation timestamp to client side (and display it)~~
* ~~Figure out how to filter out people with zero score (should be possible in grids)~~
* ~~Slack integration should print out uuid.~~





Deployment
***
Run `cdk deploy` in the working directory.

Flow
***
Once deployed the flow of the system is as follows:


    [browser] (user choice)
        ^
        | * Browser fetches html + data from S3
        | * Tables are rendered client side
        ^
    [scoreboard] (S3)
        ^
        |
        ^
    [htmlgen] (lambda)
        ^
        | * Updates the global scores if required
        | * Reads the message and
        |   - generates new data files to S3.
        |   - Makes a notification in DynDB on
        |     when the files where generated
        ^
    [scoreboard-generator_queue] (sqs)
        ^
        | * sends one message per eligeble board
        ^
    [spawner] (lambda)
        ^
        | * Spawner reads the board configurations
        |
        ^
    [scoreboard-config] (dynamoDB)
        ^
        | The slack integration has CRUD
        | capabilities on the board configuration
        ^
    [bot] (lambda)
        ^
        |
        ^
    [slack] (slack client)



Configuration files
***

To populate the system with data, run `add_data.py` with `boards.json` and `namemap.json` filled in.

    {
            '<list id>':
            {
                "jayone": "jesper",
                "donjoe": "jonas"
            },
            ...
        }
    }
_namemap.json_

    [
        {
            "boardid": "<your list id>",
            "sessionid": "<your session id>>",
            "title": "My own AoC highscore list",
            "year": ["2020", ...],
            "uuid": "<uuid>"
        },
        ...
    ]
_boards.json_

Slack integration
===
You need to create the integration in slack yourself.

I named my app is `aoc-highscores` and made it respond to `/aoc <command>`.

Follow https://medium.com/glasswall-engineering/how-to-create-a-slack-bot-using-aws-lambda-in-1-hour-1dbc1b6f021c and you should be fine.


Obscured by Clouds
***
You need to subscribe to events if you want to talk privately with the bot.

Go to slackAPI page | Features and enable events and subscribe to `message.im`.

Required scopes
***
Make sure the app has the following scopes:
* chat:write
* commands
* im:history
* incoming-webhook

A saucerful of secrets
***
Create a file named `slack_verification_token.txt` and copy the **verification token**
from the slackAPI page | Settings | Basic Information under App Credentials | Verification Token.

Create a file named `slack_bot_token.txt` and copy the **Bot User OAuth Access Token** from the slackAPI page | Features | OAuth & Permissions under OAuth Tokens for Your Team | Bot User OAuth Access Token.

Place both these two files in the git root directory. They are used during provisioning.

The Lost Art of Conversation
***
Talk to the bot either in private chats or by the command you hooked it to.

