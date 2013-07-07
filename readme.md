#twitter-bot (airtoxinbotbot)
指定ユーザーのタイムラインからマルコフ連鎖した文章をツイートするbotです。

##依存パッケージ
+ python-twitter

+ MeCab

MeCabがインストールされている環境で動かすことができます。

##使用方法
`$ python bot.py`

bot.pyと同じ階層にtwitter公式のツイート履歴(tweet.csv)を置くとそれを読み込みます
データはshelveでpickle化した物がdata.dbとして保存されます。
設定項目はまだないです。