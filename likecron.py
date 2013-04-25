#!/usr/bin/env python  
# -*- coding: utf-8 -*- 
import json
import time
from subprocess import call

with open("settings.json") as f:
    settings = json.load(f)
while 1:
    call("python bot.py",shell=True)
    time.sleep(settings["like_cron"]["cron_time"])