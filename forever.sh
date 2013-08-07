#!/usr/bin/env sh

while :
do
    python bot.py >message.tmp 2>&1
    cat message.tmp | mail -s "airtoxinbotbot has an error" xxxxxxxxxxxx@xxxxx.xxx
    rm message.tmp
    sleep 10
done