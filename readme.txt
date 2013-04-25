指定ユーザーのタイムラインからマルコフ連鎖した文章をツイートするbotです。

依存モジュール:
    python-twitter
    MeCab

MeCabがインストールされているサーバーもしくはローカル環境で動かすことができます。

使用方法:
    セットアップ:
        settings.jsonを開いて
        consumer_key, consumer_secret, access_token, access_token_secret
        にbot用アカウントのそれぞれの項目をセットします。
        持ってない人はtwitter developperから取得して下さい。
        usernameに監視するtwitterのユーザーidをセットします。
        setupのところをTrueに変更します。
        settings.jsonを保存してbot.pyを実行するとbot用のアカウントにツイートされます。
        これでセットアップが終了したので、もう一度settings.jsonを開いてsettingsの項目をFalseに戻して保存します。

    likecron.py:
        cronで動かせるサーバーがないので自分のPCで動かしたい！
        でも定期的に自分でbot.pyを動かすのはめんどくさい！
        という人（自分）用に書きました。
        bot.pyの代わりにこっちを動かすと定期的にbotを動かしてくれます。
        投稿間隔はsettingsのcron_timeで設定出来ます。

    settingsについて:
        これをいじると色々設定出来ます。
        botaccount:
            bot用アカウントの設定項目です。
            consumer_key, consumer_secret, access_token, access_token_secret
            それぞれに対応するものを設定して下さい。
        setup:
            セットアップ用の設定項目です。
            setup: 初回起動の際にTrueに、それ以外はFalseに設定して下さい。
            load_tweet_csv: twitter公式からダウンロード出来る自分の過去ツイートのcsvファイルを読み込んでマルコフ連鎖に使いたい場合はTrueにしてください。csvファイルはdatasフォルダ以下に入れて下さい。
        like_cron:
            likecron.py用の設定項目です。
            cron_time: likecron.pyを実行した時のbotの投稿間隔を秒単位で設定します。
        etc:
            その他の設定項目です。
            min_tweet_length: マルコフ連鎖で生成するツイートの最小の長さです。これよりも短いツイートはされません。最小0。あまり小さい数字にすると「@」や「http」など意味の分からない単発ツイートが増えます
            min_tweet_length: マルコフ連鎖で生成するツイートの最長の長さです。これよりも長いツイートはされません。最大140。あまり大きい数字にすると意味の分からない文章ができやすくなります。

    datasフォルダについて:
        ここにtwitter公式の過去ツイートをまとめたcsvファイルを置いてsettingsのload_tweet_csvをTrueに設定すると過去のツイートも学習させることができます。

未実装:
    MeCab API(http://yapi.ta2o.net/apis/mecapi.cgi)によるMeCab環境非依存的な解析
    自動フォロー返し
    自動リムーブ返し
    リプライ返信
    改行ツイート対応