# 扉のむこうの少女

> 暗がりに、ふるい扉がひとつ。むこうから、小さな声がします。

**扉のむこうの少女と、声か文字で自由に会話する 15〜20 分の物語体験。**
何を話してもかまいません。あなたの言葉が、彼女が思い出す手がかりになります。
彼女が充分に思い出せたとき——扉は、ひらきます。

- 1人用 / 所要 15〜20 分 / 準備するのは Claude の API キーだけ
- こわい演出はありません(しずかな、すこし切ない物語です)
- TRPG の「自由に話していい」体験を、ひとりで・気軽に味わうための実験作です

⚠️ **ネタバレ注意**: `server.py` と `docs/` には物語の真相が書かれています。
**まず一度プレイしてから**ソースを読むことを強くおすすめします。

---

## あそびかた(セットアップ)

必要なもの: **Python 3.9+** と **Anthropic API キー**([console.anthropic.com](https://console.anthropic.com/) で取得)

```bash
git clone https://github.com/siraha0611/tobira-no-mukou-no-shoujo.git
cd tobira-no-mukou-no-shoujo

# 1) 依存をインストール(venv推奨)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2) APIキーを設定
cp .env.example .env
#    → .env を開いて ANTHROPIC_API_KEY=sk-ant-... を貼り付け

# 3) 起動
.venv/bin/python server.py
```

ブラウザで **http://localhost:8138** を開き、「扉の前に立つ」を押してください。

- API キーが未設定でも「体験モード(台本進行)」で動作確認できます
- 料金の目安: 1 プレイあたり数円程度(既定モデル Claude Haiku 4.5・プロンプトキャッシュ使用)

## 声とマイク(任意)

無くてもテキスト会話だけで完結します。あると没入感が上がります。

| 機能 | 用意するもの | 備考 |
|---|---|---|
| 彼女の声 | [VOICEVOX](https://voicevox.hiroshiba.jp/) か [AivisSpeech](https://aivis-project.com/) を起動しておく | 自動検出。macOS は `say` でも代替 |
| マイク入力 | [whisper.cpp](https://github.com/ggml-org/whisper.cpp) (`whisper-cli`) + モデル + `ffmpeg` | 無い場合は Chrome のブラウザ音声認識に自動フォールバック |

## 設定(環境変数 / .env)

| 変数 | 既定値 | 説明 |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | 必須。Claude API キー |
| `CLAUDE_MODEL` | `claude-haiku-4-5` | 会話モデル。品質を上げたいときは `claude-sonnet-4-6` 等に |
| `PORT` | `8138` | サーバポート |
| `MIN_TURNS` | `8` | 扉が開くまでの最低会話ターン数 |
| `TTS_MODE` | `auto` | `off` で声を無効化 |
| `VOICEVOX_HOST` / `VOICEVOX_SPEAKER` | `http://127.0.0.1:50021` / `14` | VOICEVOX 接続先と話者 |
| `AIVIS_HOST` / `AIVIS_SPEAKER` | `http://127.0.0.1:10101` / `1878365376` | AivisSpeech 接続先と話者 |
| `WHISPER_BIN` / `WHISPER_MODEL` | `whisper-cli` / `~/.local/share/whisper-cpp/...` | マイク入力(STT) |
| `SAVE_TRANSCRIPTS` | `0` | `1` で会話記録を `transcripts/` に保存(研究・体験調査用。画面に保存中である旨が表示されます) |

## しくみ(ネタバレなし)

```
ブラウザ (index.html)
  │  テキスト or 録音
  ▼
server.py (Python 標準ライブラリのみの小さなHTTPサーバ)
  ├─ STT: whisper.cpp で文字起こし(任意)
  ├─ 会話: Claude API — 少女の人格・物語の真相は server.py 内の
  │        システムプロンプトだけにあり、ブラウザには送られません
  ├─ 進行: 「思い出し」の段階(stage 0-5)はサーバ側でゲート
  │        (急に結末へ飛ばない・最低ターン数を保証)
  └─ TTS: VOICEVOX / AivisSpeech / macOS say を自動検出(任意)
```

- 会話履歴はメモリ上のみ(既定)。外部送信は Anthropic API のみ
- プロンプトキャッシュ(system 凍結+履歴ブレークポイント)でコストを最小化

## トラブルシューティング

- **「サーバに接続できません」** → `server.py` が起動しているか、ポートが他のアプリと衝突していないか(`PORT=8200` などで変更)
- **マイクが使えない** → `http://localhost:8138` を Chrome で直接開く(埋め込みビューはマイク不可)。whisper が無ければ文字入力で
- **声が出ない** → VOICEVOX / AivisSpeech が起動しているか。`/health` で現在のエンジンを確認できます
- **彼女の応答が JSON っぽく壊れる** → `pip install -U anthropic` で SDK を更新

## クレジット

- 企画・物語・キャラクター設計: **KASO**(TRPG シナリオ作家)
  - 代表作: クトゥルフ神話TRPGシナリオ『[夢語りはティータイムのあとで](https://booth.pm/ja/items/8045336)』
- 本作は「TRPG 初回体験の設計」研究(修了課題)のプロトタイプです

## ライセンス

- **コード**: MIT License
- **物語・キャラクター(綾香)・セリフ等のテキスト**: © KASO。個人で遊ぶ・改造して遊ぶのは自由ですが、物語部分の再配布・商用利用はご相談ください。
- 詳細は [LICENSE](LICENSE) を参照

---

## English (brief)

**The Girl Beyond the Door** — a 15–20 min solo narrative experience where you talk freely
(by voice or text, in Japanese) with a girl behind an old door. Your words help her remember
who she is; when she remembers enough, the door opens.

Setup: `pip install -r requirements.txt`, put your `ANTHROPIC_API_KEY` in `.env`, run
`python3 server.py`, open `http://localhost:8138`. Voice (VOICEVOX/AivisSpeech) and
mic input (whisper.cpp) are optional. Code is MIT; story text © KASO.

⚠️ Spoilers live in `server.py` and `docs/` — play first, read later.
