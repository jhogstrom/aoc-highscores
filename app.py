#!/usr/bin/env python3

from aws_cdk import core

from stack import ScoreboardStack


app = core.App()
ScoreboardStack(app, "scoreboard")

app.synth()
