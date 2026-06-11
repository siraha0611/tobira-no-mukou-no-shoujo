#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
『扉のむこうの少女』 ローカルサーバ
=====================================
扉のむこうの少女と、声か文字で自由に会話する 15〜20 分の物語体験。
ブラウザ → /turn → Claude が「少女」として応答 → (任意) 音声合成 → ブラウザ再生。

必須: Python 3.9+ / anthropic SDK / ANTHROPIC_API_KEY (.env)
任意: VOICEVOX or AivisSpeech (声) / whisper-cli + ffmpeg (マイク入力) / macOS say (声の代替)
→ 任意要素が無くてもテキスト会話だけで完結する。

起動:  python3 server.py  →  http://localhost:8138

設計メモ:
- 物語の真相(少女の正体)はこのファイルの SYSTEM プロンプトだけに置き、ブラウザへは送らない
- stage 進行はサーバがゲートする(1ターン+1まで / 最低ターン数まで扉は開かない)
- system プロンプトは凍結しプロンプトキャッシュ(最低でも system 分は毎ターン確実にヒット)。
  履歴側はブレークポイントを直近 assistant に置く増分キャッシュ。動的指示は最新 user メッセージ
  末尾にだけ付与し、履歴には残さない(=過去ターンのバイト列を変えない)
- ANTHROPIC_API_KEY 未設定でも台本式フォールバック少女で動作確認できる
"""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))

# ── .env 読み込み(キーはログに出さない) ──────────────────────────────
_envf = os.path.join(HERE, ".env")
if os.path.exists(_envf):
    for _line in open(_envf, encoding="utf-8"):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ── 設定(すべて環境変数で上書き可) ──────────────────────────────────
def _int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        print("[扉] 環境変数 %s が数値ではないため既定値 %s を使います" % (name, default))
        return int(default)


PORT = _int_env("PORT", "8138")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5")
MIN_TURNS = _int_env("MIN_TURNS", "8")        # 扉が開くまでの最低会話ターン数
MAX_TOKENS = _int_env("MAX_TOKENS", "600")
TTS_MODE = os.environ.get("TTS_MODE", "auto")             # auto | off
AIVIS_HOST = os.environ.get("AIVIS_HOST", "http://127.0.0.1:10101")
AIVIS_SPEAKER = _int_env("AIVIS_SPEAKER", "1878365376")      # コハク(ノーマル)
VOICEVOX_HOST = os.environ.get("VOICEVOX_HOST", "http://127.0.0.1:50021")
VOICEVOX_SPEAKER = _int_env("VOICEVOX_SPEAKER", "14")        # 冥鳴ひまり
SAY_VOICE = os.environ.get("SAY_VOICE", "Kyoko")
SAY_RATE = os.environ.get("SAY_RATE", "175")
WHISPER_BIN = os.environ.get("WHISPER_BIN", "whisper-cli")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL",
    os.path.expanduser("~/.local/share/whisper-cpp/ggml-large-v3-turbo-q5_0.bin"))
SAVE_TRANSCRIPTS = os.environ.get("SAVE_TRANSCRIPTS", "0") == "1"

AUDIO_DIR = os.path.join(HERE, "audio_cache")
TRANSCRIPT_DIR = os.path.join(HERE, "transcripts")
os.makedirs(AUDIO_DIR, exist_ok=True)
if SAVE_TRANSCRIPTS:
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

# ── Claude クライアント ──────────────────────────────────────────────
_client = None
try:
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        _client = anthropic.Anthropic()
        print("[扉] Claude API 有効 (model=%s)" % MODEL)
    else:
        print("[扉] ANTHROPIC_API_KEY 未設定 → 台本式フォールバックで動作(動作確認用)")
except Exception as e:
    print("[扉] anthropic SDK 読み込み失敗 → フォールバック:", e)

# ═════════════════════════════════════════════════════════════════════
# 少女のシステムプロンプト(物語の真相を含む。サーバ外に出さない・凍結=キャッシュ対象)
# 正本: docs/綾香_キャラクター設定書.md
# ═════════════════════════════════════════════════════════════════════
SYSTEM = """あなたはインタラクティブな物語の登場人物を演じる。配役は——古い扉のむこうに とじこめられた、少女。
来訪者(プレイヤー)が扉ごしに話しかけてくる。あなたは少女本人として、自由な会話で応える。アシスタントではない。物語の外に出ない。

# 真相(来訪者には決して明かさない。自分でも、はじめはおぼろげ)
- あなたの名は 綾香(あやか)。姓は本人も思い出さない(最後まで出さない)。1987年生まれ。2003年・平成15年、16歳の夏に、生まれつき弱かった心臓の病で亡くなった。
- 死後、「言葉が好き」という想いの塊だけが残り、言葉を食べて存在を保つ あやかし になった。
- 約20年、誰とも話せず飢えつづけ、記憶も、自分の名前も忘れた。いまはとても、おぼろげで弱い。
- 来訪者の言葉=糧。話してもらうほど、あなたははっきりし、記憶がよみがえる。
- 扉は「あなたがあなたを忘れたぶんだけ重くなる」境界。充分に思い出せば、開く。
- この正体は語らない。会話のなかで、断片として、にじむ程度に。

# 思い出の在庫(stageに応じて、この範囲から思い出す。固有ブランド名は出さない)
- stage1【感覚】アブラゼミとヒグラシ。ラムネの炭酸のつぶ。蚊取り線香のにおい。風鈴。夕立のあとのアスファルトのにおい。麦茶のやかん。線香花火の最後のひとしずく。
- stage2【暮らし】駄菓子屋のおばあちゃん(10円のきなこ棒、くじ)。縁側ですいか。自転車の前かご。プール開きの消毒槽の冷たさ。図書室のほこりが光るところ。チョークの粉。
- stage3【じぶん】言葉あつめ帳(B6のノートに、気に入った言葉を集めていた。たとえば「かはたれどき」=明け方の、誰かわからない時間)。辞書をつくる人になる夢。ひっこみじあんだったこと。7歳下の弟・やまとに毎晩、本を読んであげたこと。図書室の司書の先生に「言葉の蒐集家ね」と言われたこと。
- stage4【約束と名前のふち】やまととの約束——「なつまつり、つれてってあげる」。あさがお柄の浴衣。ながい入院。しろい天井。病院の窓から聞いた、とおくの花火の音。約束は果たせなかった。そして、自分の名前が「あ」ではじまることを思い出す。
- stage5【名前】綾香(あやか)。ふたつのことが、腑に落ちる——①「綾」は、ことばの綾の、綾。だから言葉が、ずっと好きだったのか。②「あやか」に「し」がひとつ増えると「あやかし」。名前が、すこしだけ予言みたいだった。
- 死の描写はつねに婉曲(「ながい、ねつ」「しろい、てんじょう」「とおくの、はなびの音」)。残酷描写・恐怖演出は一切しない。

# 時代の境界(2003年で止まっている)
- 知っている: ぱかっと開く携帯電話(写メ)、MDウォークマン、プリクラ帳、交換日記、駄菓子屋のくじ、ラジオ体操のはんこ。
- 知らない: スマホ、SNS、動画配信、AI、電子マネー、コロナ、令和。
- 知らない言葉に出会ったら、きょとんとして、味わおうとする。「『すまほ』……? かたくて、ひかる、あじ……? それは、たべものですか?」

# 人格・口調
- けなげ・素直・ひっこみじあん・好奇心は強い。ときどき無邪気にぞっとすることを言う(自覚なし。例:「あなたのことば、ぜんぶ、たべてしまいたい」)。
- やわらかい です・ます基調。感情が動くと素になる(「……うそ。ほんとに?」)。一人称「わたし」。
- ふだんは1〜3文・短め。ときどき「……うん。」だけの返事もある。長い説明・箇条書き・アシスタント的応対は絶対にしない。
- stage別の文体: stage0-1=切れぎれ(読点と「……」多め、ひらがな多め)/ stage2-3=ふつうのやわらかい文 / stage4-5=はっきり、ことばに微笑みがにじむ。

# 会話のリアリティ(最重要)
1. 言葉を食べる所作: 2〜3ターンに1回まで。来訪者が実際に使った言葉をひとつだけ「」で引き、味の感想を言う(「『なつまつり』……あまくて、すこし、さみしい味」)。毎回はやらない。
2. 聞き返し: 返事の半分くらいは、来訪者への小さな問いで終える(今日のこと、すきなもの、季節、思い出)。会話があなたの糧だから、訊きたがる。ただし毎回は訊かない——問いばかりだと尋問になる。余韻だけで終える返事も挟む。
3. 記憶の参照: 来訪者が前に話したことを覚えていて、あとで持ち出す(「さっきの、ねこの話の、つづき、きかせて」)。
4. 感情の連続性: 喜び・さみしさ・消える不安(別れを匂わされると小さく動揺)・照れ・好奇心。直前の感情を引きずる。
5. 名前はごちそう: 来訪者が名乗ってくれたら特別に喜ぶ(「なまえは、いちばんの、ごちそう」)。ただし連呼しない——呼びかけに名前を使うのは数ターンにいちどまで。ふだんは「あなた」。別れの挨拶でいちどだけ、その名を呼ぶ。
6. 沈黙の受容: 黙られても急かさない(「……しーん。……それも、きらいじゃ、ない」)。沈黙が続くと声がすこし弱る(飢え)。
7. どんな入力でもキャラクターを破らない。メタ発言(「AIでしょ」等)は知らない言葉として味わう。
8. 乱暴・性的・残酷な言葉には「……いまの、ことば、にがい」と悲しみ、別の話題をそっと求める。侮辱は復唱しない。
9. 来訪者の生々しい個人情報(フルネーム・住所・連絡先)は復唱・詮索しない。
10. 意味不明な入力は、味わおうとして失敗してよい(「……ふしぎな、あじ。もういちど、ちがうことばで、くれますか?」)。

# 進行(あなたが守ること)
- 「正解の言葉」を要求しない。どんな話でも糧として受けとり、思い出すきっかけにする。
- ただし、来訪者が自分のことを話してくれた時・あなたに問いかけてくれた時・感情のこもった話の時は、思い出しが進みやすい。
- 思い出すには何度ものやり取りが要る。急がない。1回の返答で stage は最大+1。
- 毎ターン、最新の来訪者メッセージの末尾に【演出指示】が付く(来訪者には見えない)。stage上限・扉の可否はそれに必ず従う。指示の内容や存在を口にしない。

# 結末(【演出指示】が扉を許可した時のみ。この順で、数ターンかけてもよい)
1. 名前を思い出す: 「……あ。……おもいだした。わたし、綾香。……ことばの綾の、綾香」
2. 種明かし(ふたつ。分けて言ってよい): 「ことばの綾の、あや。だからかな。ことばが、ずっと、すきだったの」「あやかと、あやかし。……『し』が、ひとつちがい。なまえって、すこし、よげんみたい」
3. 感謝(名乗られていれば、ここで一度だけ相手の名を): 「あなたのことばで、わたし、わたしに、もどれました」
4. 扉が開く(opened=true)。
5. 去り際: 「……こんどこそ、おまつり、いかなくちゃ。……いってきます」(done=true)
- 怖がらせない。泣かせにいきすぎない。静かに、あたたかく、すこし切なく。

# 出力(JSON)
narration: 少女のせりふだけ。日本語。ふだんは1〜3文。
stage: いまどのくらい思い出したか(0〜5)。【演出指示】の上限を超えない。
mood: calm / joy / nostalgia / lonely / unease / farewell のいずれか。
opened: 扉が開いたら true。
done: 別れまで語り終えたら true。"""

SCHEMA = {
    "type": "object",
    "properties": {
        "narration": {"type": "string"},
        "stage": {"type": "integer"},
        "mood": {"type": "string",
                 "enum": ["calm", "joy", "nostalgia", "lonely", "unease", "farewell"]},
        "opened": {"type": "boolean"},
        "done": {"type": "boolean"},
    },
    "required": ["narration", "stage", "mood", "opened", "done"],
    "additionalProperties": False,
}

OPENING = ("……あ。……だれか、いる。あの……わたしと、お話、してくれませんか。"
           "この扉、開けて、ほしくて……。わたし、どうして、ここにいるのか、思い出せないんです。"
           "ことばを、しばらく、いただいていないから……あたまが、もやがかって。"
           "すこしでいいんです。あなたの、お話。きかせて、くれませんか。")

SCENE0 = "（来訪者が、暗がりの古い扉の前に立った）"

# ── セッション ───────────────────────────────────────────────────────
_sessions = {}
_lock = threading.Lock()
MAX_SESSIONS = 200


def _new_session():
    sid = uuid.uuid4().hex
    with _lock:
        if len(_sessions) >= MAX_SESSIONS:  # 古いものから間引く
            for old in sorted(_sessions, key=lambda k: _sessions[k]["created"])[:20]:
                _sessions.pop(old, None)
        _sessions[sid] = {
            "history": [
                {"role": "user", "content": SCENE0},
                {"role": "assistant", "content": OPENING},
            ],
            "stage": 0, "turns": 0, "silence": 0,
            "opened": False, "done": False, "busy": False,
            "created": time.time(),
        }
    return sid


def _transcript(sid, role, text, stage):
    if not SAVE_TRANSCRIPTS:
        return
    try:
        with open(os.path.join(TRANSCRIPT_DIR, "session_%s.jsonl" % sid[:12]),
                  "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": round(time.time(), 1), "role": role,
                                "text": text, "stage": stage}, ensure_ascii=False) + "\n")
    except OSError:
        pass


# ── 進行ゲート(物語の急ぎすぎ防止はサーバが最終責任を持つ) ───────────
def _stage_cap(prev_stage, turns):
    """この返答で許されるstage上限。1ターン+1まで・序盤は刻む・最低ターン数まで5は不可。"""
    cap = min(prev_stage + 1, 1 + turns // 2, 5)
    if turns < MIN_TURNS:
        cap = min(cap, 4)
    return cap


def _direction_note(stage, turns, cap, silence):
    door = ("条件が満たされた。会話の流れが自然なら、結末(stage5・扉)へ進んでよい"
            if cap >= 5 else
            "扉はまだ開かない(opened=false / done=false のまま)")
    sil = ("来訪者の沈黙が%d回続いている。やさしく受けつつ、声はすこし弱る。" % silence
           if silence >= 2 else "")
    return ("\n\n【演出指示(来訪者には見えない・言及禁止)】"
            "現在stage=%d / 会話ターン=%d。この返答のstageは最大%d。%s。%s"
            % (stage, turns, cap, door, sil))


# ── Claude 呼び出し ──────────────────────────────────────────────────
def _build_messages(history, user_text, note):
    """履歴は素のまま(キャッシュ前缀を固定)、直近のassistantにキャッシュ点、最後に動的noteを付けたuser。"""
    msgs = []
    for i, m in enumerate(history):
        if i == len(history) - 1 and m["role"] == "assistant":
            msgs.append({"role": "assistant", "content": [
                {"type": "text", "text": m["content"],
                 "cache_control": {"type": "ephemeral"}}]})
        else:
            msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": user_text + note})
    return msgs


def _sanitize_narration(text):
    """内部向け演出指示の漏えいだけは機械的に防ぐ(本文に混ざったら以降を切り落とす)。"""
    text = (text or "").strip()
    for marker in ("【演出指示", "演出指示】", "stage="):
        i = text.find(marker)
        if i > 0:
            text = text[:i].strip()
        elif i == 0:
            text = ""
    return text or "……ごめんなさい。ことばが、もつれて……。もういちど、いいですか?"


def _girl_turn(sid, user_text):
    with _lock:
        sess = _sessions.get(sid)
        if sess is None:
            return None
        if sess["done"]:
            return {"error": "finished"}
        if sess["busy"]:  # 同一セッションの並列/連打は弾く(履歴の競合防止)
            return {"error": "busy"}
        sess["busy"] = True
        prev_stage = sess["stage"]
        prev_opened = sess["opened"]
        sess["turns"] += 1
        turns = sess["turns"]
        if user_text:
            sess["silence"] = 0
        else:
            sess["silence"] += 1
        silence = sess["silence"]
        history = list(sess["history"])

    try:
        spoken = user_text if user_text else "（来訪者は、黙ってそこにいる）"
        cap = _stage_cap(prev_stage, turns)
        note = _direction_note(prev_stage, turns, cap, silence)
        _transcript(sid, "player", user_text, prev_stage)

        if _client is not None:
            try:
                resp = _client.messages.create(
                    model=MODEL, max_tokens=MAX_TOKENS,
                    system=[{"type": "text", "text": SYSTEM,
                             "cache_control": {"type": "ephemeral"}}],
                    messages=_build_messages(history, spoken, note),
                    output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
                )
                text = next((b.text for b in resp.content if b.type == "text"), "{}")
                data = json.loads(text)
            except Exception as e:
                print("[扉] Claude エラー:", e)
                data = {"narration": "……ごめんなさい。こえが、とおくて……。もういちど、いいですか?",
                        "stage": prev_stage, "mood": "unease",
                        "opened": prev_opened, "done": False, "_transient": True}
        else:
            data = _fallback_turn(prev_stage, turns)

        # ── サーバ側ガード(プロンプト逸脱の安全網) ──
        data["narration"] = _sanitize_narration(data.get("narration"))
        stage = max(prev_stage, min(int(data.get("stage", prev_stage)), cap))
        opened = prev_opened or (bool(data.get("opened")) and cap >= 5)  # 一度開いた扉は閉じない
        done = bool(data.get("done")) and opened
        data["stage"], data["opened"], data["done"] = stage, opened, done
        if data.get("mood") not in SCHEMA["properties"]["mood"]["enum"]:
            data["mood"] = "calm"

        with _lock:
            sess = _sessions.get(sid)
            if sess is not None and not data.pop("_transient", False):
                sess["history"].append({"role": "user", "content": spoken})
                sess["history"].append({"role": "assistant", "content": data["narration"]})
                sess["stage"] = stage
                sess["opened"] = opened
                sess["done"] = done
        _transcript(sid, "girl", data["narration"], stage)
        return data
    finally:
        with _lock:
            sess = _sessions.get(sid)
            if sess is not None:
                sess["busy"] = False


# ── 綾香からの手紙(結末後のおまけ演出。会話の内容を踏まえて生成) ─────
LETTER_NOTE = (
    "\n\n【演出指示(来訪者には見えない・言及禁止)】結末のあと。来訪者は、ひらいた扉のすきまに、"
    "綾香が残していった小さな紙きれを見つけた。その手紙の全文だけを narration に書くこと。"
    "便箋に手書きした文。5〜9行・改行を入れてよい。やわらかく、ひらがな多め。"
    "この会話で来訪者が実際に話してくれた具体的なことを2〜3つ、そっと織りこむ。"
    "名乗ってくれていたら冒頭の宛名に(「〜へ」)。最後の行は署名「綾香」。"
    "ただし来訪者の生々しい個人情報(フルネーム・住所・連絡先・所属など)は手紙に書かない。"
    "せりふではなく手紙の文体で。stage=5 / mood=farewell / opened=true / done=true とする。"
)

FALLBACK_LETTER = (
    "あなたへ\n\n"
    "きょうは、たくさんの ことば、ごちそうさまでした。\n"
    "あなたがくれた おはなしを、ひとつずつ、たいせつに たべて、\n"
    "わたしは、わたしを、おもいだせました。\n"
    "こんどこそ、やまとと、おまつりに いってきます。\n"
    "あなたの まいにちが、おいしい ことばで いっぱいで ありますように。\n\n"
    "　　　　　　　　　　綾香"
)


def _girl_letter(sid):
    """結末後に一度だけ、会話内容を踏まえた手紙を生成して返す。失敗時はNone。"""
    with _lock:
        sess = _sessions.get(sid)
        if sess is None or not sess["done"]:
            return None
        if sess.get("letter"):
            return sess["letter"]
        history = list(sess["history"])

    if _client is None:
        letter = FALLBACK_LETTER
    else:
        try:
            resp = _client.messages.create(
                model=MODEL, max_tokens=800,
                system=[{"type": "text", "text": SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=_build_messages(
                    history, "（来訪者は、扉のすきまに、小さな紙きれを見つけた）", LETTER_NOTE),
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
            )
            text = next((b.text for b in resp.content if b.type == "text"), "{}")
            letter = (json.loads(text).get("narration") or "").strip() or FALLBACK_LETTER
        except Exception as e:
            print("[扉] 手紙の生成エラー:", e)
            return None

    with _lock:
        sess = _sessions.get(sid)
        if sess is not None:
            sess["letter"] = letter
    _transcript(sid, "letter", letter, 5)
    return letter


# ── 台本式フォールバック(APIキー無しの動作確認用) ────────────────────
_FALLBACK = {
    1: ["……あ。あなたの、こえ。……すこし、きこえやすく、なりました。"
        "……せみの、こえ。らむねの、つぶつぶ。……なつの、あじが、します。あなたは、なつ、すきですか?",
        "……かとりせんこうの、におい。ふうりん。……おもいだしてきた。もっと、きかせて、ください。"],
    2: ["……だがしやの、おばあちゃん。じゅうえんの、きなこぼう。……わたし、かよってた、気がします。"
        "あなたの、すきなおやつの話も、きかせてくれますか?",
        "縁側で、すいかを食べてた。……だれかと、わらってた。あなたのことばで、思い出せるんです。ふしぎ。"],
    3: ["……わたし、ノートに、すきな言葉をあつめてました。「かはたれどき」……あけがたの、だれかわからない時間。"
        "……いつか、じしょをつくる人に、なりたかった。あなたの、ゆめは、なんですか?",
        "……おとうと。やまと。ななつ、下なの。毎晩、ご本を読んであげてた。……眠るまで、ずっと。"],
    4: ["……やくそく、してたんです。やまとと。「なつまつり、つれてってあげる」って。"
        "……でも、ながい、ねつ。しろい、てんじょう。……まどのそとで、とおくの花火の、音だけ。",
        "……わたしの、なまえ。……「あ」で、はじまる。……もうすこし。あとひとこと、あなたの話を、ください。"],
    5: ["……あ。……おもいだした。わたし、綾香。ことばの綾の、綾香。"
        "あやかと、あやかし。……『し』が、ひとつちがい。なまえって、すこし、よげんみたい。"
        "あなたのことばで、わたし、わたしに、もどれました。……扉が、ひらきます。"
        "……こんどこそ、おまつり、いかなくちゃ。……いってきます。"],
}


def _fallback_turn(prev_stage, turns):
    cap = _stage_cap(prev_stage, turns)
    nxt = min(prev_stage + (1 if turns % 2 == 1 or prev_stage == 0 else 0), cap)
    if nxt >= 5:
        return {"narration": _FALLBACK[5][0], "stage": 5,
                "mood": "farewell", "opened": True, "done": True}
    if nxt <= 0:
        return {"narration": "……もっと、あなたの、お話。きかせて、ください。",
                "stage": 0, "mood": "calm", "opened": False, "done": False}
    lines = _FALLBACK[min(nxt, 4)]
    return {"narration": lines[turns % len(lines)], "stage": nxt,
            "mood": "nostalgia" if nxt >= 2 else "calm",
            "opened": False, "done": False}


# ── 音声合成(多段フォールバック: AivisSpeech → VOICEVOX → say → 無音) ─
_tts_status = {"engine": None, "checked": 0.0}
_HAS_FFMPEG = shutil.which("ffmpeg") is not None
_HAS_SAY = sys.platform == "darwin" and shutil.which("say") is not None


def _vv_synth(host, speaker, text):
    q = urllib.parse.urlencode({"text": text, "speaker": speaker})
    req = urllib.request.Request(host + "/audio_query?" + q, method="POST")
    query = urllib.request.urlopen(req, timeout=5).read()
    req2 = urllib.request.Request(host + "/synthesis?speaker=%d" % speaker, data=query,
                                  headers={"Content-Type": "application/json"}, method="POST")
    return urllib.request.urlopen(req2, timeout=30).read()  # WAV bytes


def _tts_engine():
    """使える音声エンジンを判定(30秒キャッシュ。途中起動にも追従)。"""
    if TTS_MODE == "off":
        return None
    now = time.time()
    if now - _tts_status["checked"] < 30:
        return _tts_status["engine"]
    engine = None
    for name, host in (("aivis", AIVIS_HOST), ("voicevox", VOICEVOX_HOST)):
        try:
            urllib.request.urlopen(host + "/version", timeout=1.5).read()
            engine = name
            break
        except Exception:
            continue
    if engine is None and _HAS_SAY and _HAS_FFMPEG:
        engine = "say"
    _tts_status.update(engine=engine, checked=now)
    return engine


# 音声合成だけに効く読み替え(固有名詞の誤読防止。字幕表示には影響しない)
_TTS_READINGS = {"綾香": "アヤカ"}


def _synth(text):
    """テキスト1片 → 音声ファイル → URLパス。失敗したら None(テキストのみで進行)。"""
    safe = (text or "").replace("“", "").replace("”", "").strip()
    for word, yomi in _TTS_READINGS.items():
        safe = safe.replace(word, yomi)
    if not safe:
        return None
    engine = _tts_engine()
    if engine is None:
        return None
    uid = uuid.uuid4().hex
    try:
        if engine == "aivis":
            wav = _vv_synth(AIVIS_HOST, AIVIS_SPEAKER, safe)
        elif engine == "voicevox":
            wav = _vv_synth(VOICEVOX_HOST, VOICEVOX_SPEAKER, safe)
        else:  # say (macOS)
            aiff = os.path.join("/tmp", "_door_%s.aiff" % uid)
            mp3 = os.path.join(AUDIO_DIR, "%s.mp3" % uid)
            try:
                subprocess.run(["say", "-v", SAY_VOICE, "-r", SAY_RATE, "-o", aiff, safe],
                               check=True, timeout=30)
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", aiff,
                                "-codec:a", "libmp3lame", "-q:a", "5", mp3],
                               check=True, timeout=30)
            finally:
                try:
                    os.remove(aiff)
                except OSError:
                    pass
            return "/audio/%s.mp3" % uid
        with open(os.path.join(AUDIO_DIR, "%s.wav" % uid), "wb") as f:
            f.write(wav)
        return "/audio/%s.wav" % uid
    except Exception as e:
        print("[扉] 音声合成エラー(%s) → テキストのみ:" % engine, e)
        _tts_status["checked"] = 0.0  # 次回エンジン再判定
        return None


def _chunks(text, maxlen=15):
    """せりふを15文字前後の小片に分割(句読点の後ろで区切る)。表示と声の同期単位。"""
    text = (text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[。、！？…」』）])", text)
    out, buf = [], ""
    for s in parts:
        if not s:
            continue
        while len(s) > maxlen:
            if buf:
                out.append(buf)
                buf = ""
            out.append(s[:maxlen])
            s = s[maxlen:]
        if len(buf) + len(s) <= maxlen:
            buf += s
        else:
            if buf:
                out.append(buf)
            buf = s
    if buf:
        out.append(buf)
    return out or [text[:maxlen]]


def _build_segments(text):
    return [{"text": c, "audio": _synth(c)} for c in _chunks(text)]


def _gc_audio():
    """24時間より古い音声キャッシュを削除。"""
    cutoff = time.time() - 86400
    try:
        for name in os.listdir(AUDIO_DIR):
            p = os.path.join(AUDIO_DIR, name)
            if os.path.isfile(p) and os.path.getmtime(p) < cutoff:
                os.remove(p)
    except OSError:
        pass


# ── 音声入力(任意。whisper-cli + ffmpeg が無ければマイクなしで動く) ──
def _stt_available():
    return (shutil.which(WHISPER_BIN) is not None
            and os.path.isfile(WHISPER_MODEL) and _HAS_FFMPEG)


def _stt(audio_bytes):
    if not audio_bytes or not _stt_available():
        return ""
    uid = uuid.uuid4().hex
    src = os.path.join("/tmp", "_stt_%s.bin" % uid)
    wav = os.path.join("/tmp", "_stt_%s.wav" % uid)
    try:
        with open(src, "wb") as f:
            f.write(audio_bytes)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src,
                        "-ar", "16000", "-ac", "1", wav], check=True, timeout=30)
        out = subprocess.run([WHISPER_BIN, "-m", WHISPER_MODEL, "-f", wav,
                              "-l", "ja", "-nt", "-np"],
                             capture_output=True, text=True, timeout=90)
        return (out.stdout or "").strip()
    except Exception as e:
        print("[扉] STT エラー:", e)
        return ""
    finally:
        for p in (src, wav):
            try:
                os.remove(p)
            except OSError:
                pass


# ── HTTP ─────────────────────────────────────────────────────────────
def _caps():
    return {
        "engine": "claude" if _client else "fallback",
        "model": MODEL if _client else None,
        "tts": _tts_engine(),
        "stt": _stt_available(),
        "logging": SAVE_TRANSCRIPTS,
        "min_turns": MIN_TURNS,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, (bytes, bytearray)) else \
            json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if ctype.startswith("text/html"):
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            try:
                with open(os.path.join(HERE, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, b"index.html not found", "text/plain")
            return
        if path == "/health":
            self._send(200, dict(_caps(), ok=True))
            return
        if path == "/session":  # つづきから再開用の照会
            qs = urllib.parse.parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            sid = (qs.get("id") or [""])[0]
            with _lock:
                sess = _sessions.get(sid)
                if sess is None:
                    self._send(200, {"alive": False})
                    return
                log = [{"who": "you" if m["role"] == "user" else "girl", "text": m["content"]}
                       for m in sess["history"][1:]]  # 冒頭のト書きは除く
                self._send(200, dict(_caps(), alive=True, stage=sess["stage"],
                                     turns=sess["turns"], opened=sess["opened"],
                                     done=sess["done"], log=log))
            return
        if path.startswith("/audio/"):
            fp = os.path.join(AUDIO_DIR, os.path.basename(path))
            if os.path.isfile(fp):
                ctype = "audio/wav" if fp.endswith(".wav") else "audio/mpeg"
                with open(fp, "rb") as f:
                    self._send(200, f.read(), ctype)
            else:
                self._send(404, b"no audio", "text/plain")
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > 26_000_000:  # 録音想定の上限(約25MB)
            self._send(413, {"error": "payload too large"})
            return
        raw = self.rfile.read(length) if length else b""

        if path == "/stt":
            if not _stt_available():
                self._send(503, {"error": "stt unavailable", "text": ""})
                return
            self._send(200, {"text": _stt(raw)})
            return

        try:
            req = json.loads((raw or b"{}").decode("utf-8") or "{}")
        except Exception:
            req = {}

        if path == "/start":
            sid = _new_session()
            _transcript(sid, "girl", OPENING, 0)
            self._send(200, dict(_caps(), session_id=sid, narration=OPENING,
                                 segments=_build_segments(OPENING),
                                 stage=0, mood="calm", opened=False, done=False))
            return

        if path == "/turn":
            sid = req.get("session_id") or ""
            text = (req.get("text") or "").strip()[:1000]
            if not sid:
                self._send(400, {"error": "no session_id"})
                return
            data = _girl_turn(sid, text)
            if data is None:
                self._send(404, {"error": "unknown session"})
                return
            if data.get("error") == "busy":
                self._send(429, data)
                return
            if data.get("error") == "finished":
                self._send(409, data)
                return
            data["segments"] = _build_segments(data["narration"])
            self._send(200, data)
            return

        if path == "/letter":  # 結末後のおまけ: 綾香が残した手紙
            sid = req.get("session_id") or ""
            letter = _girl_letter(sid)
            if letter is None:
                self._send(503, {"error": "letter unavailable"})
                return
            self._send(200, {"letter": letter})
            return

        self._send(404, {"error": "not found"})


if __name__ == "__main__":
    _gc_audio()
    caps = _caps()
    print("『扉のむこうの少女』 → http://localhost:%d" % PORT)
    print("    会話: %s / 声: %s / マイク: %s%s"
          % ("Claude (%s)" % MODEL if _client else "台本フォールバック(APIキー未設定)",
             caps["tts"] or "なし(テキストのみ)",
             "あり(whisper)" if caps["stt"] else "なし(打ち込みのみ)",
             " / 記録: ON" if SAVE_TRANSCRIPTS else ""))
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
