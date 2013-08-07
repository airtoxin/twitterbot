#!/usr/bin/env sh

while :
do
    python bot.py 2> message.tmp
    cat message.tmp | mail -s "airtoxinbotbot has an error" xxxxxxxxxxxx@xxxxx.xxx
    rm message.tmp
    sleep 10
done