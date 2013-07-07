#!/usr/bin/env python
# -*- coding: utf-8 -*-
import twitter
import MeCab
import random
import re
import pickle
import json
import urllib

#==変数定義==#

#urlにマッチ
m = re.compile("https?://[\w/:%#\$&\?\(\)~\.=\+\-]+")

with open("settings.json") as f:
    settings = json.load(f)

user_name = settings["botaccount"]["username"]
setup = bool(settings["setup"]["setup"]=="True")
load_tweet_csv = bool(settings["setup"]["load_tweet_csv"]=="True")
min_tweet_length = settings["etc"]["min_tweet_length"]
max_tweet_length = settings["etc"]["max_tweet_length"]

#airtoxinbotbot
consumer_key = settings["botaccount"]["consumer_key"]
consumer_secret = settings["botaccount"]["consumer_secret"]
access_token = settings["botaccount"]["access_token"]
access_token_secret = settings["botaccount"]["access_token_secret"]

api = twitter.Api(consumer_key = consumer_key,
                consumer_secret = consumer_secret,
                access_token_key = access_token,
                access_token_secret = access_token_secret)

#==関数定義==#

def loadObject(object_name):
    with open(object_name, "rb") as f:
        o = pickle.load(f)
    return o

def saveObject(object_name, save_name):
    with open(save_name, "w+") as f:
        pickle.dump(object_name, f)

def getDiffTimeline(new, old):
    new_ids = [t.id for t in new]
    old_id = old[0].id
    if setup:
        return new
    elif old_id in new_ids:
        return new[:new_ids.index(old_id)]
    else:
        return new

def updateUserTimeline(user_name):
    user_timeline = api.GetUserTimeline(user_name, count=100)
    if setup:
        saveObject(user_timeline, "./datas/old_user_timeline.dump")
        return user_timeline
    old_user_timeline = loadObject("./datas/old_user_timeline.dump")
    diff_timeline = getDiffTimeline(user_timeline, old_user_timeline)
    saveObject(user_timeline, "./datas/old_user_timeline.dump")
    return diff_timeline

def splitSentence(sentence):
    mec = MeCab.Tagger("-Owakati")
    wakati = mec.parse(sentence.encode("utf-8"))
    return wakati.decode("utf-8").split(" ")

def splitSentenceByMECAPI(sentence):
    #thanks http://yapi.ta2o.net/apis/mecapi.cgi
    apiURL = "http://yapi.ta2o.net/apis/mecapi.cgi?sentence=%s&response=&filter=&format=json" % sentence
    sentenceJSON = json.load(urllib.urlopen(apiURL))
    return [word["surface"] for word in sentenceJSON]



def removeURL(text):
    URLs = m.findall(text)
    processedText = m.sub("http://twitpic.com/cbupg7", text) #http://twitpic.com/cc2jxd #http://twitpic.com/cbupg7
    return(processedText,URLs)

def loadTweetCsvFile(filename):
    import csv
    with open(filename) as f:
        reader = csv.reader((line.replace("\x00", "") for line in f), delimiter=",")
        header = reader.next()
        csv_tweets = [twitter.Status(id=line[0], text=line[7].decode("utf-8")) for line in reader]
    return csv_tweets

def updateMarkovDictionary(user_timeline):
    if load_tweet_csv:
        csv_tweets = loadTweetCsvFile("./datas/tweets.csv")
        user_timeline = csv_tweets
    if setup:
        d = {}
        saveObject(d, "./datas/markov_dict.dump")
    markov_dict = loadObject("./datas/markov_dict.dump")
    if user_timeline == []: #差分のツイートがないなら辞書をそのまま返す
        return markov_dict
    for tweet in user_timeline: #辞書のアップデート
        tweet.text, url = removeURL(tweet.text)
        breakSplittedTweet = tweet.text.split("\n")
        splitBreakSplittedTweet = [splitSentence(tweetBreaks) for tweetBreaks in breakSplittedTweet] #改行で分けたツイートを更に分かち書きにする
        splitBreakSplittedTweet[0].insert(0, "\\start\\")
        splitBreakSplittedTweet[len(splitBreakSplittedTweet)-1].append("\\end\\")
        for splittedTweet in splitBreakSplittedTweet:
            splittedTweet.append("\\break\\") #改行をマーキング
        splitBreakSplittedTweet[len(splitBreakSplittedTweet)-1].pop #最後のデータが \\end\\ \\break\\になってりうので\\break\\を取り除く
        wakati_tweet = [wakati for wakati in splittedTweet for splittedTweet in splitBreakSplittedTweet] #フラット化
        for i in range(len(wakati_tweet)-2):
            front = (wakati_tweet[i], wakati_tweet[i+1])
            back = wakati_tweet[i+2]
            if front in markov_dict:
                markov_dict[front].append(back)
            else:
                markov_dict[front] = [back]
    saveObject(markov_dict, "./datas/markov_dict.dump")
    return markov_dict

def generateMarkovSentence(markov_dict):
    startKeys = [key for key in markov_dict.iterkeys() if key[0]=="\\start\\"] #キーのタプルに\\start\\を含むものだけを抽出
    front = random.choice(startKeys)
    markov_sentence = front[1] #ツイートの初めの文字
    while True:
        print front
        back = random.choice(markov_dict[front])
        if back == u"\\end\\":
            if len(markov_sentence) < min_tweet_length: #短すぎるツイートはもう一回生成し直す
                markov_sentence = generateMarkovSentence(markov_dict)
            else:
                break
        elif len(markov_sentence+back) > max_tweet_length: #140字を超えたら終了
            break
        else:
            markov_sentence += back
            front = (front[1],back)
    markov_sentence = re.sub(r"\\break\\", "\n", markov_sentence)
    return markov_sentence

def generate_twitpic():
    strings = [chr(n) for n in range(ord("0"), ord("9")+1)] + [chr(s) for s in range(ord("a"), ord("z")+1)]
    twitpic_url = ""
    for i in range(6):
        while 1:
            choose_str = random.choice(strings)
            if twitpic_url + choose_str < "cbupg7":
                twitpic_url += choose_str
                break
    return " http://twitpic.com/"+twitpic_url

def sendTweet(tweet, mute=False):
    tweet = re.sub(u"^RT ", u"", tweet) #先頭のRTを削除
    tweet = re.sub(u"@[0-9A-Za-z_]*", u"", tweet) #リプライの表示を削除
    twitpic = generate_twitpic()
    tweet = m.sub(twitpic, tweet)
    #re.sub(u"@", u"©", tweet) #ツイート中の@を©に変換
    try:
        status = api.PostUpdate(tweet)
    except twitter.TwitterError:
        tweet = generateMarkovSentence(markov_dict)
        sendTweet(tweet)
    if not mute:
        try:
            print "tweet:"+status.text
        except UnboundLocalError:
            pass

def generate_replie(user_id):
    markov_dict = loadObject("./datas/markov_dict.dump")
    replie = generateMarkovSentence(markov_dict)
    replie = re.sub(r"^\w*", "@%s "%user_id, replie)
    return replie

def sendReply():
    old_rep = loadObject("old_replie.dump")
    reps = api.GetMentions(since_id=old_rep.id)
    if reps != []:
        for rep in reps:
            rep_user_id = rep.user.screen_name
            print rep_user_id
            if rep_user_id == "airtoxinbotbot":
                continue
            replie = generate_replie(rep_user_id)
            twitpic = generate_twitpic()
            replie = m.sub(twitpic, replie)
            status = api.PostUpdate(replie)
            try:
                print "replie:"+status.text
            except UnboundLocalError:
                pass
    saveObject(reps[0], "old_replie.dump")

def refollow():
    pass

def favouriteTimeline():
    pass

#==メイン==#

if __name__ == "__main__":
    user_timeline = updateUserTimeline(user_name)
    markov_dict = updateMarkovDictionary(user_timeline)
    tweet = generateMarkovSentence(markov_dict)
    sendTweet(tweet)
    #sendReply()
    #refollow()
    #favouriteTimeline()