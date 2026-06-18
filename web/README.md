# 扉のむこうの少女 Web版 v1

Cloudflare Worker 1本で、静的HTML配信と `/start` `/turn` `/letter` API を扱う文字版です。ローカル版の `server.py` / `index.html` は変更しません。

## ローカル起動

```bash
cd web
npm install
cp .dev.vars.example .dev.vars
```

`.dev.vars` に次を入れます。

- `ANTHROPIC_API_KEY`: ローカル確認用の Anthropic API キー
- `TURNSTILE_SECRET`: ローカルでは Cloudflare Turnstile のテスト secret を利用可能
- `SESSION_HMAC_SECRET`: `openssl rand -base64 32` などで生成したランダム文字列

起動:

```bash
npm run dev
```

標準では `http://localhost:8787` で確認できます。Turnstile の公開 sitekey は `wrangler.toml` の `TURNSTILE_SITE_KEY` で指定します。初期値は Cloudflare の常時pass用テスト sitekey です。

## 公開前の設定

公開前に `ANTHROPIC_API_KEY` を新規発行して `wrangler secret put` してください。現行キーは使わないでください。

```bash
wrangler secret put ANTHROPIC_API_KEY
wrangler secret put TURNSTILE_SECRET
wrangler secret put SESSION_HMAC_SECRET
```

KV namespace を作り、`wrangler.toml` の `id` / `preview_id` を差し替えます。

```bash
wrangler kv namespace create DOOR_KV
wrangler kv namespace create DOOR_KV --preview
```

Turnstile の本番 sitekey は秘密ではないため、`wrangler.toml` の `TURNSTILE_SITE_KEY` を本番値に変更します。デプロイはレビュー後に実行してください。

## 安全弁の調整

- 日次呼び出し上限: `wrangler.toml` の `DAILY_CALL_CAP` を変更します。既定は `600` です。
- セッション期限: `src/worker.ts` の `SESSION_TTL_SECONDS`。既定は30分です。
- セッション最大ターン: `src/worker.ts` の `MAX_SESSION_TURNS`。既定は30ターンです。
- 入力長: `MAX_USER_TEXT_CHARS` と履歴上限 `MAX_HISTORY_MESSAGES` / `MAX_HISTORY_TOTAL_CHARS` を調整します。

`SYSTEM`、Anthropic APIキー、サーバ側の進行指示は `src/worker.ts` 内だけで使い、HTML/JS/APIレスポンスには出しません。

## 確認コマンド例

```bash
npm run typecheck
npm run dev
curl -s http://localhost:8787/health
curl -s http://localhost:8787/ | grep -E 'ANTHROPIC_API_KEY|SESSION_HMAC_SECRET|演出指示|# 真相|SYSTEM' || true
```

`/start` は Turnstile トークン必須です。ブラウザで Turnstile を通してから、会話、扉の開放、手紙、`.txt` 保存、つづきからを確認してください。
