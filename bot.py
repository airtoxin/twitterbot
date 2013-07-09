#!/usr/bin/env python
# -*- coding: utf-8 -*-

u"""airtoxinbotbot

とりあえずTL監視だけ"""

import re
import csv
import random
import shelve
import logging
from multiprocessing import Process, Queue
from collections import OrderedDict
import time
from datetime import timedelta

import tweepy
from tweepy.streaming import StreamListener, Stream
from tweepy.auth import OAuthHandler
import MeCab

#==========*設定*==========#
#ふぁぼ用ワード
fav_words = [u"botbot", u"airtoxin"]

# NOTEXT_MESSAGE = [u"ん〜〜〜っ…♡", u"んっ…♡", u"んふ…っ///", u"やっ…♡", u"んっ、ブラ外そ", u"んっんっ…♡",
#             u"あっ…♡", u"やぁ…♡", u"ぁあんっ……♡", u"あぁんっ………♡", u"あんっ…♡", u"あぁっ……♡", u"ぁんっあっえっ…♡",
#             u"あうっうっ………♡", u"あんっやあぁ……♡", u"あっはっんっ……♡", u"んうっんんっあぁあぁっはあっあっんあぁ♡♡♡"]
#時々発言します
NOTEXT_MESSAGE = [u"んっ♡"]

DELETE_MESSAGE = [u"ツ消見", u"ツイの消しか"]

#パクリをする閾値
COPY_THRESHOLD = 1

#==========*グローバル関数*==========#
def get_oauth():
    consumer_key = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    consumer_secret = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    access_key = 'XXXXXXXX-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    access_secret = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_key, access_secret)
    return auth

def load_data(key):
    open_data = shelve.open("data.db")
    return open_data[key]
    open_data.close()

def save_data(data, key):
    open_data = shelve.open("data.db")
    open_data[key] = data
    open_data.close()

def get_hinshi(sentence):
    u"""品詞のみを取り出したリストを返す"""
    if isinstance(sentence, unicode):
        sentence = sentence.encode("utf-8")
    hinshis = []
    tagger = MeCab.Tagger('-Ochasen')
    node = tagger.parseToNode(sentence)
    while node:
        feature = node.feature.decode("utf-8").split(",")
        surface = node.surface.decode("utf-8")
        if feature[0] == u"名詞":
            hinshis.append(surface)
        node = node.next
    return hinshis

def to_plane_tweet(tweet_text):
    tweet_text = r_rep.sub("", tweet_text)
    twitpic = generate_twitpic()
    tweet_text = r_url.sub(twitpic, tweet_text)
    return tweet_text

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

def regular_tweet(bot_ins, markov_ins):
    u"""定期的なツイートをするための関数"""
    #TLの差分取得
    while 1:
        newest_tweet_id = load_data("newest_tweet_id")
        logging.debug("newest_tweet_id: %s" % newest_tweet_id)
        new_tweets = bot_ins.get_new_tweets("_eannu_", newest_tweet_id)
        if new_tweets != []:
            save_data(new_tweets[0].id, "newest_tweet_id")
            logging.debug("newest_tweet_id update: %#s" % new_tweets[0].id)
        #マルコフ辞書のアップデート
        for new_tweet in new_tweets:
            logging.debug("add to markov_dictionary: %s" % new_tweet.text)
            markov_ins.add_from_sentence(new_tweet.text)
        markov_ins.save_dictionary()
        logging.debug("markov_dictionary saved")
        tweet_text = to_plane_tweet(markov_ins.generate())
        logging.debug("tweet_text: %s" % tweet_text)
        bot_ins.send_tweet(tweet_text)
        hinshis = [hinshi for hinshi in get_hinshi(tweet_text) if len(hinshi) > 1]
        QUE.put(hinshis, True, 1)
        time.sleep(1200)


#==========*Central class*==========#
class Bot:
    def __init__(self):
        self.auth = get_oauth()
        self.api = tweepy.API(auth_handler=self.auth, api_root='/1.1')
    def send_tweet(self, tweet_text, in_reply_to=None):
        logging.debug("send_tweet()")
        try:
            self.api.update_status(tweet_text, in_reply_to_status_id=in_reply_to)
            print "tweet: %s" % tweet_text.rstrip()
        except tweepy.error.TweepError as e:
            print "failure tweet: (%s) on Bot.send_tweet()" % e.message
    def get_new_tweets(self, user_id, old_tweet_id):
        u"""指定ユーザーのTLからツイートを取得する関数
        user_idのTLをold_tweet_idまで取ってきて(上限200)、
        それらをリスト化して返す"""
        cursor = tweepy.Cursor(self.api.user_timeline, screen_name=user_id).pages(10)
        new_tweets = []
        track_back_flg = False
        for tweet_list in cursor:
            for tweet in tweet_list:
                if tweet.id == old_tweet_id:
                    track_back_flg = True
                    break
                else:
                    new_tweets.append(tweet)
            if track_back_flg == True:
                break
        return new_tweets
    @classmethod
    def load_csv_tweets(cls, csv_path):
        u"""twitter公式のtweetアーカイブのcsvからツイートを読み込む関数"""
        csv_tweets = csv.reader(open(csv_path))
        csv_tweets.next() #ヘッダー
        return (tweet[7].decode("utf-8") for tweet in csv_tweets)


#==========*Favorite words*==========#
class FavWords:
    def __init__(self, wordlist):
        self.favs = dict()
        self.to_unicode = lambda x: x.decode("utf-8") if isinstance(x, str) else x
        self.favs["init"] = set([self.to_unicode(word) for word in wordlist])
    def iterwords(self):
        return (value for key in self.favs.iterkeys() for value in self.favs[key])
    def add_words(self, key, wordlist):
        self.favs.setdefault(key, set())
        self.favs[key] = self.favs[key].union([self.to_unicode(word) for word in wordlist])
    def add_words_into_init(self, wordlist):
        wordlist = [self.to_unicode(word) for word in wordlist]
        self.favs["init"] = self.favs.union([self.to_unicode(word) for word in wordlist])
    def del_key(self, key):
        try:
            self.favs.pop(key)
        except:
            pass
    def del_words(self, key, wordlist):
        self.favs[key].difference_update([self.to_unicode(word) for word in wordlist])
    def def_words_from_init(self, key, wordlist):
        self.favs["init"].difference_update([self.to_unicode(word) for word in wordlist])
    def initialize(self):
        for key in self.favs.iterkeys():
            if key != "init":
                self.favs.pop(key)


#==========*Markov chain*==========#
class MarkovGenerator:
    u"""マルコフ連鎖で文章を作るクラス
    クラス生成の際にマルコフ辞書を渡すことで、その辞書を利用してマルコフ連鎖を行う

    ==attributes==
    MarkovGenerator.dictionary : マルコフ辞書(dict)
    MarkovGenerator.start_point_word : マルコフ辞書用開始文字(str)
    MarkovGenerator.end_point_word : マルコフ辞書用終点文字(str)

    ==辞書フォーマット==
    2重マルコフ連鎖辞書
    keyに開始文字2つのタプル
    valueにその開始文字に続く言葉

    Ex)
    "はじめの言葉に続く言葉"
    =>  {
            (u"__start__", u"はじめの"): u"言葉に",
            (u"はじめの", u"言葉に"): u"続く言葉",
            (u"言葉に", u"続く言葉"): u"__end__"
        }
    逆連鎖辞書もend→startの方向"""
    def __init__(self, markov_dictionary=None, reversed_markov_dictionary=None, start_point_word=u"\\start\\", end_point_word=u"\\end\\"):
        if markov_dictionary != None:
            self.dictionary = markov_dictionary
        else:
            self.dictionary = dict()
        if reversed_markov_dictionary != None:
            self.reversed_dictionary = reversed_markov_dictionary
        else:
            self.reversed_dictionary = dict()
        self.start_point_word = start_point_word
        self.end_point_word = end_point_word
    def generate(self, min_length=3, max_length=50):
        u"""マルコフ連鎖によって文字列を出力"""
        start_word = self._choose_start_word()
        markov_sentence = start_word[1]
        while 1:
            chosen_word = random.choice(self.dictionary[start_word])
            if chosen_word == self.end_point_word:
                if len(markov_sentence) > min_length:
                    break
                else:
                    markov_sentence = self.generate()
            else:
                if len(markov_sentence + chosen_word) <= max_length:
                    markov_sentence += chosen_word
                    start_word = (start_word[1], chosen_word)
                else:
                    break
        return markov_sentence
    def generate_from_word(self, word, min_length=3, max_length=25):
        u"""ある単語から前方向と後ろ方向にマルコフ連鎖して文字列をつくる"""
        # 後ろ方向に伸ばす
        if len([key for key in self.dictionary if key[0] == word]) == 0 \
        or len([key for key in self.reversed_dictionary if key[0] == word]) == 0:
            return self.generate()
        start_word = random.choice([key for key in self.dictionary if key[0] == word])
        markov_sentence = start_word[0]
        while 1:
            chosen_word = random.choice(self.dictionary[start_word])
            if chosen_word == self.end_point_word:
                if len(markov_sentence) > min_length:
                    break
                else:
                    markov_sentence = self.generate_from_word(word)
            else:
                if len(markov_sentence + chosen_word) <= max_length:
                    markov_sentence += chosen_word
                    start_word = (start_word[1], chosen_word)
                else:
                    break
        # 前方向に伸ばす
        start_word = random.choice([key for key in self.reversed_dictionary if key[0] == word])
        while 1:
            chosen_word = random.choice(self.reversed_dictionary[start_word])
            if chosen_word == self.start_point_word:
                break
            else:
                if len(markov_sentence + chosen_word) <= max_length * 2:
                    markov_sentence = chosen_word + markov_sentence
                    start_word = (start_word[1], chosen_word)
                else:
                    break
        return markov_sentence
    def _choose_start_word(self):
        u"""マルコフ連鎖のはじめの言葉を選ぶ関数
        マルコフ辞書は2重のものなのでstart_wordは
        (u"\\start\\", u"はじめ")というようなキーでstart_wordを取り出さなければならない。
        このu"はじめ"を選ぶための関数"""
        start_words = [start_word for start_word in self.dictionary.iterkeys() if start_word[0] == self.start_point_word]
        return random.choice(start_words)
    def add_from_dictionary(self, user_dictionary):
        u"""辞書型からマルコフ辞書に追加する"""
        if not isinstance(user_dictionary, dict):
            raise Exception, "add_from_dictionary args must be dictionary"
        #正順マルコフ辞書
        for key in user_dictionary:
            if key in self.dictionary:
                self.dictionary[key].append(user_dictionary[key])
            else:
                self.dictionary[key] = [user_dictionary[key]]
        #逆連鎖マルコフ辞書
        word_sets = []
        for key in user_dictionary:
            for i in range(len(user_dictionary[key])):
                word_sets.append((user_dictionary[key].pop(), key[1], key[0]))
        for word_set in word_sets:
            key = (word_set[0], word_set[1])
            if key in self.reversed_dictionary:
                self.reversed_dictionary[key].append(word_set[2])
            else:
                self.reversed_dictionary[key] = [word_set[2]]
    def add_from_sentence(self, sentence):
        u"""文字列からマルコフ辞書に追加する"""
        wakati = self.get_wakati_sentence(sentence)
        wakati.insert(0, self.start_point_word)
        wakati.append(self.end_point_word)
        #正順マルコフ辞書
        for i in range(len(wakati)-2):
            key = (wakati[i], wakati[i+1])
            if key in self.dictionary:
                self.dictionary[key].append(wakati[i+2])
            else:
                self.dictionary[key] = [wakati[i+2]]
        #逆連鎖マルコフ辞書
        for i in reversed(range(len(wakati)-2)):
            key = (wakati[i+2], wakati[i+1])
            if key in self.reversed_dictionary:
                self.reversed_dictionary[key].append(wakati[i])
            else:
                self.reversed_dictionary[key] = [wakati[i]]
    def save_dictionary(self):
        u"""shelveによってマルコフ辞書を永続化"""
        save_data(self.dictionary, "markov_dictionary")
        save_data(self.reversed_dictionary, "reversed_markov_dictionary")
    def load_dictionary(self):
        u"""shelveによって永続化したマルコフ辞書を読み込む"""
        self.dictionary = load_data("markov_dictionary")
        self.reversed_dictionary = load_data("reversed_markov_dictionary")
    def get_wakati_sentence(self, sentence):
        u"""文字列を分かち書きしたものを返す"""
        mec = MeCab.Tagger("-Owakati")
        wakatis = []
        if isinstance(sentence, unicode):
            sentence = sentence.encode("utf-8")
        sentence_lines = sentence.split("\n")
        for sentence_line in sentence_lines:
            wakati = mec.parse(sentence_line)
            wakati = wakati.decode("utf-8").split()
            wakatis.extend(wakati)
            wakatis.append(u"\n")
        wakatis.pop()
        return wakatis



#==========*User stream*==========#
class AbstractedlyListener(StreamListener):
    """ Let's stare abstractedly at the User Streams ! """
    def on_connect(self):
        u"""ストリーミングサーバーに接続された時に1度だけ呼び出される__init__的な関数"""
        pass
    def on_status(self, status):
        u"""新しいstatusが流れてきたら呼び出される"""
        if not hasattr(status, "text"):
            status.text = random.choice(NOTEXT_MESSAGE)
            logging.info("status has no text")
        if isinstance(status.text, str):
            status.text = status.text.decode("utf-8")
        if not hasattr(status, "id"):
            status.id = 350698977273978880
            logging.info("status has no id")
        # timezone is JP
        status.created_at += timedelta(hours=9)
        self.if_reply(status)
        self.timeline_watcher(status)
    def on_delete(self, status_id, user_id):
        u"""ツイートが消されたら呼び出される"""
        return
    def on_limit(self, track):
        u"""apiリミット？がきたら呼び出される"""
        return
    def on_error(self, status_code):
        u"""non-200ステータスがきたら呼び出される"""
        return
    def on_timeout(self):
        u"""タイムアウトしたら呼び出される"""
        return
    def timeline_watcher(self, status):
        u"""ふぁぼパクリRT"""
        #TL監視用辞書
        if not hasattr(self, "timeline_statuses"):
            self.timeline_statuses = OrderedDict() #追加順を保持する辞書型
        status_text = status.text.rstrip()
        #ふぁぼ
        self.fav_tweet(status)
        #パクリ
        if not status_text in self.timeline_statuses:
            #誰もパクってないツイートだったら何もしない
            self.timeline_statuses[status_text] = [status]
            if len(self.timeline_statuses) > 400:
                #保存TLが400を超えたら古いものから200個を削除
                for i in range(200):
                    self.timeline_statuses.popitem(last=False)
        elif len(self.timeline_statuses[status_text]) == COPY_THRESHOLD: #パクリのスレッショルド
            #RTだったら公式RTする
            if status_text.find("RT") == 0:
                try:
                    Bot().api.retweet(status.id)
                except (tweepy.error.TweepError, AttributeError) as e:
                    print "failure retweet (%s) on AbstractedlyListener.timeline_watcher()" % e.message
            else: #誰かがパクってたツイートならパクる
                self.timeline_statuses[status_text].append(status)
                try: 
                    for sts in self.timeline_statuses[status_text]:
                        time.sleep(1)
                        try:
                            Bot().api.create_favorite(sts.id)
                        except:
                            print "failure favorite tweet on AbstractedlyListener.timeline_watcher()"
                    print "copy: %s" % status_text
                    time.sleep(3)
                    Bot().send_tweet(status_text)
                except Exception as e:
                    print "failure copy tweet on AbstractedlyListener.timeline_watcher()"
                #辞書に追加
                MarkovGenerator().add_from_sentence(status_text)
        else:
            #パクリ済みならふぁぼるだけ
            self.timeline_statuses[status_text].append(status)
            if status.id == 350698977273978880:
                pass
            else:
                try:
                    Bot().api.create_favorite(status.id)
                except (tweepy.error.TweepError, AttributeError) as e:
                    print "failure favorite tweet (%s) on AbstractedlyListener.timeline_watcher()" % (e.message)
    def fav_tweet(self, status):
        logging.debug("AbstractedlyListener.fav_tweet()")
        #キューからふぁぼワードを取り出す
        try:
            regular_favs = QUE.get_nowait()
            FAV_WORDS.del_key("regular")
            FAV_WORDS.add_words("regular", regular_favs)
            print "FAV_WORDS:",
            for FAV_WORD in FAV_WORDS.iterwords():
                print FAV_WORD,
            print ""
        except:
            logging.debug("QUE has no new fav word")
        for word in FAV_WORDS.iterwords():
            if status.text.find(word) != -1:
                logging.debug("find word '%s' in '%s'" % (word, status.text))
                time.sleep(5)
                logging.debug("try to favorite")
                try:
                    Bot().api.create_favorite(status.id)
                    print "fav: %s" % status.text
                except tweepy.error.TweepError as e:
                    print "failure favorite on AbstractedlyListener.fav_tweet"
                break
    def if_reply(self, status):
        if status.text.find("@airtoxinbotbot") != -1:
            if status.author.screen_name == "airtoxinbotbot":
                pass
            elif status.text.find("RT") == 0: #公式/非公式RT処理
                pass
            else:
                time.sleep(5)
                reply_from = u"@" + str(status.author.screen_name)
                hinshis = get_hinshi(status.text)
                if len(hinshis) > 0:
                    #リプライに含まれる最後の品詞を取り出す
                    hinshi = hinshis[len(hinshis)-1]
                    m = MarkovGenerator()
                    m.load_dictionary()
                    reply = reply_from + u" " + to_plane_tweet(m.generate_from_word(hinshi))
                else:
                    reply = reply_from + u" " + to_plane_tweet(MarkovGenerator(markov_dictionary=load_data("markov_dictionary")).generate())
                Bot().send_tweet(reply, in_reply_to=status.id)
                save_data(status.id, "replied_tweet_id")


def main():
    logging.info("bot starting")
    bot = Bot()
    logging.info("markov data loading")
    if load_csv == True:
        markov = MarkovGenerator()
        logging.info("load_csv == True")
        csv_tweets = Bot.load_csv_tweets("./tweets.csv")
        #newest_tweet_idを保存
        newest_tweet = csv_tweets.next()
        save_data(newest_tweet[0], "newest_tweet_id")
        markov.add_from_sentence(newest_tweet[7])
        #読み込み
        for tweet in csv_tweets:
            markov.add_from_sentence(tweet)
        markov.save_dictionary()
    else:
        markov = MarkovGenerator(markov_dictionary=load_data("markov_dictionary"), reversed_markov_dictionary=load_data("reversed_markov_dictionary"))
    # 20分ごとの定期ツイート
    #multiprocess間での値のやり取り用変数
    logging.info("regular tweet starting")
    p = Process(target=regular_tweet, args=(bot, markov))
    p.start()
    # userstreamによるTL監視（リプライ・ふぁぼ・パクツイ・RT）
    logging.info("start timeline watching")
    stream = Stream(bot.auth, AbstractedlyListener(), secure=True)
    user_stream = stream.userstream()
    user_stream.start()

#==========*グローバル変数*==========#
FAV_WORDS = FavWords(fav_words)
QUE = Queue()
logging.basicConfig(level=logging.CRITICAL)
r_url = re.compile(r"https?://[\w/:%#\$&\?\(\)~\.=\+\-]+")
r_rep = re.compile(r"@\w+")
load_csv = True

if __name__ == "__main__":
    main()