# 扉のむこうの少女 — Web版 v1 仕様書(Codexハンドオフ)

ワンクリックで遊べる無料Web公開版。API代は運営(KASO)が負担する前提で、ボット濫用と費用暴走だけは確実に止める。
**声はv1では実装しない**(ブラウザ標準の音声合成のみ任意で使う)。ローカル版(`../server.py` + `../index.html`)が"フル体験"として別に残る。

## 0. 実測コスト(設計の前提)
- Claude Haiku 4.5＋プロンプトキャッシュで、1プレイ(会話9往復＋手紙)= **$0.033 ≈ ¥5**。1,000プレイ≈¥5,200。
- だから安全弁の役割は「正常な人気でなくボット/無限ループで青天井になるのを防ぐ」こと。

## 1. 構成(Cloudflare Worker 1本)
- Cloudflare Worker(Modules形式 `export default { fetch }`)1本で完結:
  - `GET /` → 静的フロント(`web/public/index.html`)を返す
  - `POST /start` → Turnstileトークン検証→OKなら署名付きセッショントークン(HMAC)を発行して返す＋OPENINGを返す
  - `POST /turn` → 会話1往復。セッショントークン必須
  - `POST /letter` → 結末後の手紙。セッショントークン必須
  - `GET /health` → `{ok:true, engine}`(任意)
- 秘密は Worker の環境変数(`wrangler secret`)で持つ。**ブラウザには絶対に出さない**:
  - `ANTHROPIC_API_KEY`(★公開前に新規発行=ローテーション。現行.envのキーは平文流通済みのため使わない)
  - `TURNSTILE_SECRET`(Cloudflare Turnstileのシークレット)
  - `SESSION_HMAC_SECRET`(セッショントークン署名用のランダム文字列)
- KV namespace `DOOR_KV`(日次予算カウンタ用)
- `wrangler.toml`/`package.json`/`tsconfig`同梱。TypeScript推奨。SDKは使わず**fetchで Anthropic Messages API を直叩き**(WorkerはNode SDK非対応)。

## 2. server.py から移植する中身(★真相はサーバ側だけ)
`../server.py` を読んで、以下を **そのまま** Workerへ移植する(文言は改変しない):
- `SYSTEM`(物語の真相を含む全文。**ブラウザに送らない**)
- `SCHEMA`(narration/stage/mood/opened/done の json_schema)
- `OPENING` / `SCENE0`
- `_stage_cap(prev_stage, turns)` … `min(prev+1, 1+turns//2, 5)`、`turns<MIN_TURNS(=8)`なら4止まり
- `_direction_note(stage, turns, cap, silence)` … 最新ユーザー発話の末尾に付ける【演出指示】(来訪者に見せない)
- `_sanitize_narration()` … 本文に演出指示やstage=が漏れたら以降を切る安全網
- `_girl_turn` のサーバ側ガード: `stage = max(prev, min(返値, cap))` / `opened = prev_opened or (返値opened and cap>=5)`(一度開いた扉は閉じない)/ `done = 返値done and opened` / moodがenum外ならcalm
- `LETTER_NOTE` と手紙生成(個人情報は書かない指示込み)、`FALLBACK_LETTER`
- 読み替え `{"綾香":"アヤカ"}` は**フロントの音声合成側**で行う(サーバは関与しない)

## 3. ステート(ステートレス設計)
サーバはセッションをメモリに持たない(Workerは呼び出し間で状態を共有しない)。
- クライアントが毎回 `{token, history:[{role,content}...], stage, turns, opened}` を送る。
- サーバはこれを**信用しない前提**で扱う: `turns` は history内のuser発話数から再計算し、`cap`を再計算して`stage`をクランプ。`opened`は単調(一度trueなら維持)。
- 履歴の中身(少女のせりふ・ユーザー入力)はもともと公開情報なので送ってよい。**SYSTEM(真相)だけは常にサーバ側**。
- 整合性を多少破られても失う物は無い(無料・データ無し)。費用の歯止めは§4で別途担保する。

## 4. 安全弁(費用暴走/ボット対策)★必須
1. **Cloudflare Turnstile**: フロントのイントロにウィジェットを置き、「扉の前に立つ」押下時のトークンを `/start` で `siteverify`(`https://challenges.cloudflare.com/turnstile/v0/siteverify`)。失敗なら開始させない。
2. **セッショントークン**: `/start`成功時にHMAC署名トークンを発行(payload= 発行時刻＋ランダムsid＋残ターン上限)。`/turn`/`/letter`はこのトークン必須・**有効30分・1セッション最大30ターン**・期限/上限超過で拒否。
3. **入力上限**: 1ユーザー発話は最大1000文字、history全体も上限(例 60メッセージ)を超えたら拒否。
4. **日次予算上限(KV)**: `DOOR_KV` の `calls:YYYY-MM-DD`(JST)をAPI呼び出しごとにincr。**1日あたりの上限(既定: 環境変数 `DAILY_CALL_CAP`=600 ≒ ¥3,000/日相当)** を超えたら `/start`と`/turn`は 503 で「本日の体験枠は終了しました。また明日、扉の前へ。」を返す(フロントは静かにその文言を表示)。上限値はenvで調整可。
5. CORS: 自サイト(Workerのドメイン)からのみ許可。`/turn`等はContent-Type必須。

## 5. Claude 呼び出し(fetch直叩き)
```
POST https://api.anthropic.com/v1/messages
headers: x-api-key: <ANTHROPIC_API_KEY>, anthropic-version: 2023-06-01, content-type: application/json
body: {
  model: "claude-haiku-4-5",
  max_tokens: 600,           // 手紙は800
  system: [{type:"text", text: SYSTEM, cache_control:{type:"ephemeral"}}],
  messages: <_build_messages相当: 履歴(最後のassistantにcache_control)＋ 末尾に user(発話+【演出指示】)>,
  output_config: {format:{type:"json_schema", schema: SCHEMA}}
}
```
- レスポンスの最初のtextブロックをJSON.parse。失敗時は穏当な「……もういちど、いいですか?」でprev状態維持(stage据置・opened据置)。
- キー/SYSTEM/演出指示はレスポンスにもログにも出さない。

## 6. フロント(`web/public/index.html`)
ローカル版 `../index.html` をベースに、**サーバ前提だけ差し替える**(世界観・演出・おもいでメーター・ことばの記録・手紙・つづきから は維持):
- **マイク(サーバwhisper)経路は削除**。入力は文字主体。声が欲しい人向けに**ブラウザ標準 `speechSynthesis`** で少女のせりふを読み上げる任意トグル(既定ON・日本語話者・「綾香」→「アヤカ」読み替えはここで)。`segments`/`/audio`/`/stt` は使わない。
- 起動フロー: イントロに **Turnstileウィジェット** を埋め込み→「扉の前に立つ」で `/start`(token取得)→OPENING表示→以降 `/turn`。トークンはメモリ保持し各リクエストに付ける。
- `/turn`の戻りは `{narration, stage, mood, opened, done}`(segmentsなし)。narrationを今の字幕表示(15文字区切り)で出し、speechSynthesisで読む。
- 結末後の `/letter`、`.txt`保存、つづきから(localStorage)、おもいでメーター、ことばの記録は**そのまま流用**。
- 503(日次上限)時はイントロに文言表示して開始ボタンを無効化。
- `data:audio` unlock等は不要に(speechSynthesisはユーザー操作後に発火させる)。

## 7. 成果物
```
web/
  wrangler.toml          # name, main, kv_namespaces=[DOOR_KV], vars(DAILY_CALL_CAP), compatibility_date
  package.json           # wrangler dev/deploy スクリプト
  tsconfig.json
  src/worker.ts          # 上記すべて(SYSTEM等はここに移植)
  public/index.html      # 文字版フロント
  .dev.vars.example      # ANTHROPIC_API_KEY= / TURNSTILE_SECRET= / SESSION_HMAC_SECRET=
  README.md              # ローカル(wrangler dev)とデプロイ手順、キーローテ注意、安全弁の調整方法
```
`.dev.vars`と本物の値は **gitignore**。READMEに「公開前にAPIキーを新規発行して `wrangler secret put` する」明記。

## 8. 受け入れ基準(レビュー時に確認)
- `wrangler dev` で `/` が表示され、Turnstile(devは常時pass用テストキー可)→会話→stage進行→扉が開く→手紙→.txt保存→つづきから、まで通る。
- SYSTEM/真相/演出指示がレスポンス・HTML・JSにいっさい出ない(curl + ページソース grep で確認)。
- 1セッション30ターン超・トークン無し/期限切れ・日次上限超で正しく拒否される。
- ローカル版(server.py/index.html)は無改変で従来通り動く(Web版は別ディレクトリ web/ に隔離)。

— 設計: KASO(CEO)/ 実装: Codex / レビュー: Claude。2026-06-18
