# 扉のむこうの少女

> 暗がりに、ふるい扉がひとつ。むこうから、小さな声がします。

**扉のむこうの少女と、自由に会話する 15〜20 分の物語体験。**
何を話してもかまいません。あなたの言葉が、彼女が思い出す手がかりになります。
彼女が充分に思い出せたとき——扉は、ひらきます。

- 1人用 / 所要 15〜20 分 / インストール不要・ブラウザだけ
- こわい演出はありません(しずかな、すこし切ない物語です)
- TRPG の「自由に話していい」体験を、ひとりで・気軽に味わうための入り口です

## ▶ あそぶ

**ブラウザでひらくだけ。準備はいりません。**

### → <https://tobira-no-mukou-no-shoujo-web.anb14625siraha.workers.dev>

- 文字で話せます。彼女の言葉は、ブラウザの読み上げで声にもなります(対応ブラウザのみ)
- はじめての方へ向けて、入口に「RPって、なに?」の短い案内があります
- 「RPがはじめてのかたへ」紹介ページ: <https://takuwith-coc.com/rp>

⚠️ **ネタバレ注意**: `web/src/worker.ts` と `docs/` には物語の真相が書かれています。
**まず一度あそんでから**ソースを読むことを強くおすすめします。

## しくみ(ネタバレなし)

```
ブラウザ (web/public/index.html)
  │  あなたの言葉
  ▼
Cloudflare Worker (web/src/worker.ts)
  ├─ 会話: Claude API(既定 Claude Haiku 4.5)。少女の人格・物語の真相は
  │        Worker 側のシステムプロンプトだけにあり、ブラウザには送られません
  ├─ 進行: 「思い出し」の段階(stage 0-5)はサーバ側でゲート
  │        (急に結末へ飛ばない・最低ターン数を保証)
  └─ 読み上げ: ブラウザ内蔵の音声合成(任意)
```

- 会話の真相はクライアントに渡らない。やり取りの履歴は署名付きトークンに封じて改ざんを防止
- プロンプトキャッシュでAPIコストを最小化(1 プレイあたり数円程度)
- ソース全体は [`web/`](web/) を参照。設計メモは [`web/SPEC_web版_v1.md`](web/SPEC_web版_v1.md)

## 物語の正本

物語・キャラクター(綾香)の設定は [`docs/物語設定書_綾香.md`](docs/物語設定書_綾香.md) が唯一の正本です。
ここを書き換えると、公開版 (`web/src/worker.ts`) に反映してデプロイします。

## クレジット

- 企画・物語・キャラクター設計: **KASO**(TRPG シナリオ作家)
  - 代表作: クトゥルフ神話TRPGシナリオ『[夢語りはティータイムのあとで](https://booth.pm/ja/items/8045336)』
- 本作は「TRPG 初回体験の設計」研究(修了課題)のプロトタイプです

## ライセンス

- **コード**: MIT License
- **物語・キャラクター(綾香)・セリフ等のテキスト**: © KASO。個人で遊ぶのは自由ですが、物語部分の再配布・商用利用はご相談ください。
- 詳細は [LICENSE](LICENSE) を参照

---

## English (brief)

**The Girl Beyond the Door** — a 15–20 min solo narrative experience where you talk freely
(in Japanese) with a girl behind an old door. Your words help her remember who she is;
when she remembers enough, the door opens.

**Just open it in your browser — no setup:**
<https://tobira-no-mukou-no-shoujo-web.anb14625siraha.workers.dev>

Runs on a Cloudflare Worker calling the Claude API; the girl's persona and the story's
truth live only in the Worker's system prompt, never sent to the browser. Code is MIT;
story text © KASO.

⚠️ Spoilers live in `web/src/worker.ts` and `docs/` — play first, read later.
