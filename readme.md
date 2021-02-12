AoC Highscore generator
===

Deployment
***
Run `cdk deploy` in the working directory.

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
            "year": ["2020"]
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

