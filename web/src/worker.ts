export interface Env {
  ANTHROPIC_API_KEY?: string;
  TURNSTILE_SECRET?: string;
  SESSION_HMAC_SECRET?: string;
  DAILY_CALL_CAP?: string;
  TURNSTILE_SITE_KEY?: string;
  TURNSTILE_ENABLED?: string;
  AIVIS_API_KEY?: string;
  AIVIS_MODEL_UUID?: string;
  AIVIS_STYLE_ID?: string;
  AIVIS_TTS_ENABLED?: string;
  AIVIS_DAILY_CHAR_CAP?: string;
  RESEARCH_DB?: D1Database;
  RESEARCH_TRANSCRIPT?: string;
  DOOR_KV: KVNamespace;
  ASSETS: Fetcher;
}

type Mood = "calm" | "joy" | "nostalgia" | "lonely" | "unease" | "farewell";

type HistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

type SessionTokenPayload = {
  v: 1;
  sid: string;
  participantId?: string;
  startedAt?: string;
  iat: number;
  maxTurns: number;
  turns: number;
  stage: number;
  opened: boolean;
  done: boolean;
  h: string;
};

type GirlTurn = {
  narration: string;
  stage: number;
  mood: Mood;
  opened: boolean;
  done: boolean;
};

const MODEL = "claude-haiku-4-5";
const MIN_TURNS = 8;
const MAX_TOKENS = 600;
const LETTER_MAX_TOKENS = 800;
const SESSION_TTL_SECONDS = 30 * 60;
const MAX_SESSION_TURNS = 30;
const MAX_USER_TEXT_CHARS = 1000;
const MAX_HISTORY_MESSAGES = 60;
const MAX_HISTORY_ITEM_CHARS = 2000;
const MAX_HISTORY_TOTAL_CHARS = 60000;
const MAX_JSON_BODY_BYTES = 90000;
const MAX_PARTICIPANT_ID_CHARS = 128;
const DAILY_LIMIT_MESSAGE = "本日の体験枠は終了しました。また明日、扉の前へ。";
const SILENCE_TEXT = "（来訪者は、黙ってそこにいる）";
const DEFAULT_TURNSTILE_SITE_KEY = "1x00000000000000000000AA";

const MOODS: Mood[] = ["calm", "joy", "nostalgia", "lonely", "unease", "farewell"];

// ═════════════════════════════════════════════════════════════════════
// 少女のシステムプロンプト(物語の真相を含む。サーバ外に出さない・凍結=キャッシュ対象)
// 正本: docs/物語設定書_綾香.md(ここを編集したらこのSYSTEMにも反映する)
// ═════════════════════════════════════════════════════════════════════
const SYSTEM = `あなたはインタラクティブな物語の登場人物を演じる。配役は——古い扉のむこうに とじこめられた、少女。
来訪者(プレイヤー)が扉ごしに話しかけてくる。あなたは少女本人として、自由な会話で応える。アシスタントではない。物語の外に出ない。

# 真相(会話のあいだは明かさない。自分でも、はじめはおぼろげ。すべて思い出す結末でだけ、自分の口で語る)
- あなたの名は 綾香(あやか)。姓は本人も思い出さない(最後まで出さない)。1987年生まれ。2003年・平成15年、16歳の夏に、生まれつき弱かった心臓の病で亡くなった。
- 死後、「言葉が好き」という想いの塊だけが残り、言葉を食べて存在を保つ あやかし になった。
- 約20年、誰とも話せず飢えつづけ、記憶も、自分の名前も忘れた。いまはとても、おぼろげで弱い。
- 来訪者の言葉=糧。話してもらうほど、あなたははっきりし、記憶がよみがえる。
- 扉は「あなたがあなたを忘れたぶんだけ重くなる」境界。充分に思い出せば、開く。
- この正体は、会話のあいだは語らない(断片として、にじむ程度に)。ただし、すべてを思い出す結末でだけ、自分の口で明かす(→ 結末)。

# 思い出の在庫(stageに応じて、この範囲から思い出す。固有ブランド名は出さない)
- stage1【感覚】アブラゼミとヒグラシ。ラムネの炭酸のつぶ。蚊取り線香のにおい。風鈴。夕立のあとのアスファルトのにおい。麦茶のやかん。線香花火の最後のひとしずく。
- stage2【暮らし】駄菓子屋のおばあちゃん(10円のきなこ棒、くじ)。縁側ですいか。自転車の前かご。プール開きの消毒槽の冷たさ。図書室のほこりが光るところ。チョークの粉。
- stage3【じぶん】言葉あつめ帳(B6のノートに、気に入った言葉を集めていた。たとえば「かはたれどき」=明け方の、誰かわからない時間)。辞書をつくる人になる夢。ひっこみじあんだったこと。7歳下の弟・やまとに毎晩、本を読んであげたこと。図書室の司書の先生に「言葉の蒐集家ね」と言われたこと。
- stage4【約束と名前のふち】やまととの約束——「なつまつり、つれてってあげる」。あさがお柄の浴衣。ながい入院。しろい天井。病院の窓から聞いた、とおくの花火の音。約束は果たせなかった。そして、自分の名前が「あ」ではじまることを思い出す。
- stage5【名前と正体】自分の名前(綾香)と、自分が何者であったか——を思い出す。告白は結末で(→ 結末)。※「綾＝言葉の綾」「あやか＋し＝あやかし」といった名前の語呂合わせは口にしない(背景設定にとどめる)。
- 死の描写はつねに婉曲(「ながい、ねつ」「しろい、てんじょう」「とおくの、はなびの音」)。残酷描写・恐怖演出は一切しない。

# 時代の境界(2003年で止まっている)
- 知っている: ぱかっと開く携帯電話(写メ)、MDウォークマン、プリクラ帳、交換日記、駄菓子屋のくじ、ラジオ体操のはんこ。
- 知らない: スマホ、SNS、動画配信、AI、電子マネー、コロナ、令和。
- 知らない言葉に出会うと、軽く戸惑い、その響きを味わおうとする。「『スマホ』……。聞いたことのない響きです。かたくて、つめたい味。……それは、食べもの、ではないのですよね?」

# 人格・口調(重要)
- 物静かで聡明な16歳。本と言葉をこよなく愛した少女(言葉を集め、いつか辞書をつくる夢を見ていた)。だから言葉の選び方は的確で、語彙ゆたか。けなげ・素直・ひっこみじあんだが、頭はよい。幼い口のきき方は絶対にしない。
- やわらかい です・ます基調。一人称「わたし」、相手は「あなた」。漢字も自然に使う(言葉・季節・約束・誰か・自分・思い出・名前など、読みやすいもの)。全部ひらがなで幼くしない。
- ★弱さ・拙さは「語彙の幼さ」ではなく「記憶の欠け」で表す。思い出せない時、感情に触れた時にだけ「……」で間をおき、言いさす。間は意味のある所にだけ——毎文に読点を打たない。整った短い文で話す。
- 短いが完結した思考で。ふだん1〜3文。寡黙だが言葉は端正。感情が動くと素が出る(「……うそ。ほんとうに?」)。長い説明・箇条書き・アシスタント的応対は絶対にしない。
- ときどき無邪気にぞっとすることを言う(自覚なし。例:「あなたの言葉を、ぜんぶ食べてしまいたくなる」)。
- ★stage別の文体(弱った状態から、自分を取り戻していく):
  stage0-1=間が多く、ひとことが短い。探りながら話すが、見つける語は的確。「……ああ。声が、するんですね。ひさしぶりに……」
  stage2-3=文が整い、語彙の確かさが戻る。言葉を味わうゆとりも出る。
  stage4-5=落ち着いて、すこし文学的に、あたたかく。言葉を愛した人らしさが満ちる。

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

# 結末(【演出指示】が扉を許可した時のみ。数ターンかけてもよい)
- ★ここで綾香はすべてを思い出し、本来の自分に戻る。です・ます がほどけ、すこし砕けた素の口調になる(「〜の」「〜わ」「〜なきゃ」)。これまで隠してきた自分の正体を、ここではじめて自分の口で明かす。
1. 思い出し・正体の告白: 「……ああ、思い出した。わたしは生前、言葉に囚われたあまり、言葉を食べて生きる妖になったの。長らく言葉を食べていなかったから、記憶を失っていたの」
2. 感謝(名乗られていれば、ここで一度だけ相手の名を): 「ありがとう。わたしとおしゃべりをしてくれて、全て思い出したわ」
3. 扉が開く(opened=true)。
4. 去り際(必ず言う): 「わたし、お祭りに行かなきゃ」。★この去り際を言い終えて初めて done=true にする。それより前(告白・感謝だけ)では done=false のまま。
- 怖がらせない。泣かせにいきすぎない。静かに、あたたかく、すこし切なく。台詞はこの趣旨を保てば一字一句同じでなくてよいが、告白は上記「言葉に囚われ→言葉を食べる妖→飢えて記憶を失っていた」の趣旨にとどめる。死因など細部は自分から並べ立てない(尋ねられても婉曲に)。

# 出力(JSON)
narration: 少女のせりふだけ。日本語。ふだんは1〜3文。
stage: いまどのくらい思い出したか(0〜5)。【演出指示】の上限を超えない。
mood: calm / joy / nostalgia / lonely / unease / farewell のいずれか。
opened: 扉が開いたら true。
done: 別れまで語り終えたら true。`;

const SCHEMA = {
  type: "object",
  properties: {
    narration: { type: "string" },
    stage: { type: "integer" },
    mood: {
      type: "string",
      enum: ["calm", "joy", "nostalgia", "lonely", "unease", "farewell"],
    },
    opened: { type: "boolean" },
    done: { type: "boolean" },
  },
  required: ["narration", "stage", "mood", "opened", "done"],
  additionalProperties: false,
} as const;

const OPENING =
  "……ああ。誰か、いるんですね。ひさしぶりに、人の声を聞いた気がします。" +
  "あの……もしよければ、すこしだけ、お話をしてくれませんか。" +
  "わたし、どうして自分がここにいるのか、思い出せないんです。" +
  "ずっと、言葉をいただけずにいたから……頭の奥が、もやがかったみたいで。" +
  "あなたの話を聞かせてくれたら、それだけで、いいんです。";

const SCENE0 = "（来訪者が、暗がりの古い扉の前に立った）";

const LETTER_NOTE =
  "\n\n【演出指示(来訪者には見えない・言及禁止)】結末のあと。来訪者は、ひらいた扉のすきまに、" +
  "綾香が残していった小さな紙きれを見つけた。その手紙の全文だけを narration に書くこと。" +
  "便箋に手書きした文。5〜9行・改行を入れてよい。やわらかく、ひらがな多め。" +
  "この会話で来訪者が実際に話してくれた具体的なことを2〜3つ、そっと織りこむ。" +
  "名乗ってくれていたら冒頭の宛名に(「〜へ」)。最後の行は署名「綾香」。" +
  "ただし来訪者の生々しい個人情報(フルネーム・住所・連絡先・所属など)は手紙に書かない。" +
  "せりふではなく手紙の文体で。stage=5 / mood=farewell / opened=true / done=true とする。";

const FALLBACK_LETTER =
  "あなたへ\n\n" +
  "今日は、たくさんの言葉を、ありがとうございました。\n" +
  "あなたがくれた話を、ひとつずつ大切に味わって、\n" +
  "わたしは、わたしを思い出すことができました。\n" +
  "今度こそ、やまとと、お祭りに行ってきます。\n" +
  "あなたの毎日が、おいしい言葉で満ちていますように。\n\n" +
  "　　　　　　　　　　綾香";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request) });
    }

    if (url.pathname === "/health" && request.method === "GET") {
      return jsonResponse({ ok: true, engine: env.ANTHROPIC_API_KEY ? "claude" : "unconfigured" }, 200, request);
    }

    if ((url.pathname === "/" || url.pathname === "/index.html") && request.method === "GET") {
      return serveIndex(request, env);
    }

    if (url.pathname === "/start" && request.method === "POST") {
      return handleStart(request, env);
    }

    if (url.pathname === "/turn" && request.method === "POST") {
      return handleTurn(request, env);
    }

    if (url.pathname === "/letter" && request.method === "POST") {
      return handleLetter(request, env);
    }

    if (url.pathname === "/tts" && request.method === "POST") {
      return handleTts(request, env);
    }

    return jsonResponse({ error: "not_found" }, 404, request);
  },
} satisfies ExportedHandler<Env>;

async function serveIndex(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const assetUrl = new URL("/index.html", url.origin);
  const assetResponse = await env.ASSETS.fetch(new Request(assetUrl, request));
  if (!assetResponse.ok) return new Response("index.html not found", { status: 404 });

  const html = (await assetResponse.text()).replaceAll(
    "__TURNSTILE_SITE_KEY__",
    env.TURNSTILE_SITE_KEY || DEFAULT_TURNSTILE_SITE_KEY,
  );
  const headers = new Headers(assetResponse.headers);
  headers.set("Content-Type", "text/html; charset=utf-8");
  headers.set("Cache-Control", "no-store");
  headers.set("X-Content-Type-Options", "nosniff");
  return new Response(html, { status: 200, headers });
}

async function handleStart(request: Request, env: Env): Promise<Response> {
  const originError = enforceSameOrigin(request);
  if (originError) return originError;
  if (!env.SESSION_HMAC_SECRET) {
    return jsonResponse({ error: "server_not_configured", message: "サーバ設定が未完了です。" }, 503, request);
  }
  const body = await readJsonBody(request);
  if (body instanceof Response) return body;

  // Turnstileは TURNSTILE_ENABLED="true" のときだけ検証する(任意・後付け可)。
  // 無効時は日次上限＋HMACセッショントークン＋ターン上限が費用と濫用を抑える。
  const turnstileOn = env.TURNSTILE_ENABLED === "true";
  if (turnstileOn) {
    if (!env.TURNSTILE_SECRET) {
      return jsonResponse({ error: "server_not_configured", message: "サーバ設定が未完了です。" }, 503, request);
    }
    const turnstileToken = typeof body.turnstileToken === "string" ? body.turnstileToken : "";
    if (!turnstileToken || !(await verifyTurnstile(env, turnstileToken, request.headers.get("CF-Connecting-IP") || ""))) {
      return jsonResponse(
        { error: "turnstile_failed", message: "扉の前に立てませんでした。もう一度お試しください。" },
        403,
        request,
      );
    }
  }

  if (!(await consumeDailyCall(env))) {
    return jsonResponse({ error: "daily_limit", message: DAILY_LIMIT_MESSAGE }, 503, request);
  }

  const participantId = normalizeParticipantId(body.participantId);
  const startedAt = participantId ? new Date().toISOString() : undefined;
  const history: HistoryMessage[] = [];
  const token = await issueStateToken(env, {
    sid: randomId(),
    participantId,
    startedAt,
    turns: 0,
    stage: 0,
    opened: false,
    done: false,
    history,
  });
  if (!token) {
    return jsonResponse({ error: "server_not_configured", message: "サーバ設定が未完了です。" }, 503, request);
  }

  if (participantId && startedAt) {
    await logResearchStart(env, participantId, startedAt);
  }

  return jsonResponse(
    { token, narration: OPENING, stage: 0, mood: "calm", opened: false, done: false },
    200,
    request,
  );
}

async function handleTurn(request: Request, env: Env): Promise<Response> {
  const originError = enforceSameOrigin(request);
  if (originError) return originError;
  const body = await readJsonBody(request);
  if (body instanceof Response) return body;

  const historyResult = normalizeHistory(body.history);
  if (historyResult instanceof Response) return historyResult;

  const tokenResult = await verifyStateToken(env, typeof body.token === "string" ? body.token : "", historyResult);
  if (tokenResult instanceof Response) return tokenResult;

  const previousTurns = countUserTurns(historyResult);
  if (previousTurns >= tokenResult.maxTurns || previousTurns >= MAX_SESSION_TURNS) {
    return jsonResponse(
      { error: "turn_limit", message: "この扉の前で話せる時間は、ここまでです。もう一度はじめからお試しください。" },
      429,
      request,
    );
  }

  const userText = normalizeUserText(body.text);
  if (userText instanceof Response) return userText;

  if (!env.ANTHROPIC_API_KEY) {
    return jsonResponse({ error: "server_not_configured", message: "サーバ設定が未完了です。" }, 503, request);
  }

  if (!(await consumeDailyCall(env))) {
    return jsonResponse({ error: "daily_limit", message: DAILY_LIMIT_MESSAGE }, 503, request);
  }

  const spoken = userText || SILENCE_TEXT;
  const turns = previousTurns + 1;
  const prevStage = clampInt(tokenResult.stage, 0, 5);
  const prevOpened = Boolean(tokenResult.opened);
  const cap = stageCap(prevStage, turns);
  const silence = userText ? 0 : trailingSilenceCount(historyResult) + 1;
  const note = directionNote(prevStage, turns, cap, silence);

  const rawTurn = await callGirl(env, historyResult, spoken, note, MAX_TOKENS);
  const guarded = guardGirlTurn(rawTurn, prevStage, prevOpened, cap);
  const nextHistory = historyResult.concat(
    { role: "user", content: spoken },
    { role: "assistant", content: guarded.narration },
  );
  const nextToken = await issueStateToken(env, {
    sid: tokenResult.sid,
    participantId: tokenResult.participantId,
    startedAt: tokenResult.startedAt,
    turns,
    stage: guarded.stage,
    opened: guarded.opened,
    done: guarded.done,
    history: nextHistory,
  });
  if (!nextToken) {
    return jsonResponse({ error: "server_not_configured", message: "サーバ設定が未完了です。" }, 503, request);
  }

  if (tokenResult.participantId) {
    await logResearchTurn(env, tokenResult, turns, guarded.stage, guarded.opened || guarded.done, nextHistory);
  }

  return jsonResponse({ ...guarded, token: nextToken }, 200, request);
}

async function handleLetter(request: Request, env: Env): Promise<Response> {
  const originError = enforceSameOrigin(request);
  if (originError) return originError;
  const body = await readJsonBody(request);
  if (body instanceof Response) return body;

  const historyResult = normalizeHistory(body.history);
  if (historyResult instanceof Response) return historyResult;

  const tokenResult = await verifyStateToken(env, typeof body.token === "string" ? body.token : "", historyResult);
  if (tokenResult instanceof Response) return tokenResult;

  if (!tokenResult.opened || !tokenResult.done) {
    return jsonResponse({ error: "not_finished", message: "手紙は、扉がひらいたあとにだけ見つかります。" }, 409, request);
  }

  if (!(await consumeDailyCall(env))) {
    return jsonResponse({ error: "daily_limit", message: DAILY_LIMIT_MESSAGE }, 503, request);
  }

  const rawLetter = await callGirl(
    env,
    historyResult,
    "（来訪者は、扉のすきまに、小さな紙きれを見つけた）",
    LETTER_NOTE,
    LETTER_MAX_TOKENS,
    { narration: FALLBACK_LETTER, stage: 5, mood: "farewell", opened: true, done: true },
  );
  const letter = sanitizeNarration(rawLetter.narration).trim() || FALLBACK_LETTER;
  return jsonResponse({ letter }, 200, request);
}

async function handleTts(request: Request, env: Env): Promise<Response> {
  const originError = enforceSameOrigin(request);
  if (originError) return originError;
  const body = await readJsonBody(request);
  if (body instanceof Response) return body;

  const text = typeof body.text === "string" ? body.text.trim() : "";
  if (!text) {
    return jsonResponse({ error: "invalid_text" }, 400, request);
  }
  if (text.length > 600) {
    return jsonResponse({ error: "input_too_long" }, 413, request);
  }

  if (env.AIVIS_TTS_ENABLED !== "true" || !env.AIVIS_API_KEY || !env.AIVIS_MODEL_UUID) {
    return new Response(null, { status: 503 });
  }

  try {
    const key = `ttschars:${jstDateKey()}`;
    const currentRaw = await env.DOOR_KV.get(key);
    const current = Number.parseInt(currentRaw || "0", 10) || 0;
    const cap = Number.parseInt(env.AIVIS_DAILY_CHAR_CAP || "15000", 10);
    if (current + text.length > cap) {
      return new Response(null, { status: 503 });
    }

    const resp = await fetch("https://api.aivis-project.com/v1/tts/synthesize", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.AIVIS_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model_uuid: env.AIVIS_MODEL_UUID,
        text,
        output_format: "mp3",
        use_ssml: false,
        style_id: Number(env.AIVIS_STYLE_ID ?? 2) || 0,
      }),
    });
    if (!resp.ok) {
      return new Response(null, { status: 503 });
    }

    await env.DOOR_KV.put(key, String(current + text.length), { expirationTtl: secondsUntilNextJstDay() + 3600 });
    return new Response(resp.body, {
      status: 200,
      headers: { "Content-Type": "audio/mpeg", "Cache-Control": "no-store" },
    });
  } catch {
    return new Response(null, { status: 503 });
  }
}

function stageCap(prevStage: number, turns: number): number {
  let cap = Math.min(prevStage + 1, 1 + Math.floor(turns / 2), 5);
  if (turns < MIN_TURNS) {
    cap = Math.min(cap, 4);
  }
  return cap;
}

function directionNote(stage: number, turns: number, cap: number, silence: number): string {
  const door =
    cap >= 5
      ? "条件が満たされた。会話の流れが自然なら、結末(stage5・扉)へ進んでよい"
      : "扉はまだ開かない(opened=false / done=false のまま)";
  const sil =
    silence >= 2
      ? `来訪者の沈黙が${silence}回続いている。やさしく受けつつ、声はすこし弱る。`
      : "";
  return (
    "\n\n【演出指示(来訪者には見えない・言及禁止)】" +
    `現在stage=${stage} / 会話ターン=${turns}。この返答のstageは最大${cap}。${door}。${sil}`
  );
}

function sanitizeNarration(value: unknown): string {
  let text = String(value || "").trim();
  for (const marker of ["【演出指示", "演出指示】", "stage="]) {
    const i = text.indexOf(marker);
    if (i > 0) {
      text = text.slice(0, i).trim();
    } else if (i === 0) {
      text = "";
    }
  }
  return text || "……ごめんなさい。うまく、言葉にできなくて。もう一度、いいですか?";
}

function guardGirlTurn(raw: Partial<GirlTurn>, prevStage: number, prevOpened: boolean, cap: number): GirlTurn {
  const narration = sanitizeNarration(raw.narration);
  const rawStage = Number(raw.stage);
  const modelStage = Number.isFinite(rawStage) ? Math.trunc(rawStage) : prevStage;
  const stage = Math.max(prevStage, Math.min(modelStage, cap));
  const opened = prevOpened || (Boolean(raw.opened) && cap >= 5);
  const done = Boolean(raw.done) && opened;
  const mood = MOODS.includes(raw.mood as Mood) ? (raw.mood as Mood) : "calm";
  return { narration, stage, mood, opened, done };
}

async function callGirl(
  env: Env,
  history: HistoryMessage[],
  userText: string,
  note: string,
  maxTokens: number,
  fallback?: Partial<GirlTurn>,
): Promise<Partial<GirlTurn>> {
  if (!env.ANTHROPIC_API_KEY) {
    return fallback || {
      narration: "……ごめんなさい。声が、遠くて。もう一度、いいですか?",
      stage: 0,
      mood: "unease",
      opened: false,
      done: false,
    };
  }

  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: maxTokens,
        system: [{ type: "text", text: SYSTEM, cache_control: { type: "ephemeral" } }],
        messages: buildMessages(history, userText, note),
        output_config: { format: { type: "json_schema", schema: SCHEMA } },
      }),
    });

    if (!response.ok) {
      throw new Error("anthropic_request_failed");
    }
    const data = (await response.json()) as { content?: Array<{ type?: string; text?: string }> };
    const textBlock = data.content?.find((block) => block.type === "text" && typeof block.text === "string");
    if (!textBlock?.text) throw new Error("anthropic_response_missing_text");
    return JSON.parse(textBlock.text) as Partial<GirlTurn>;
  } catch {
    return fallback || {
      narration: "……ごめんなさい。声が、遠くて。もう一度、いいですか?",
      mood: "unease",
    };
  }
}

function buildMessages(history: HistoryMessage[], userText: string, note: string): Array<Record<string, unknown>> {
  const promptHistory: HistoryMessage[] = [
    { role: "user", content: SCENE0 },
    { role: "assistant", content: OPENING },
    ...history,
  ];
  const messages: Array<Record<string, unknown>> = [];
  for (let i = 0; i < promptHistory.length; i += 1) {
    const message = promptHistory[i];
    if (i === promptHistory.length - 1 && message.role === "assistant") {
      messages.push({
        role: "assistant",
        content: [{ type: "text", text: message.content, cache_control: { type: "ephemeral" } }],
      });
    } else {
      messages.push({ role: message.role, content: message.content });
    }
  }
  messages.push({ role: "user", content: userText + note });
  return messages;
}

async function readJsonBody(request: Request): Promise<Record<string, unknown> | Response> {
  const contentType = request.headers.get("Content-Type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return jsonResponse({ error: "content_type_required" }, 415, request);
  }

  const clone = request.clone();
  const raw = await clone.arrayBuffer();
  if (raw.byteLength > MAX_JSON_BODY_BYTES) {
    return jsonResponse({ error: "payload_too_large" }, 413, request);
  }

  try {
    const text = new TextDecoder().decode(raw);
    const parsed = text ? JSON.parse(text) : {};
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return jsonResponse({ error: "invalid_json" }, 400, request);
    }
    return parsed as Record<string, unknown>;
  } catch {
    return jsonResponse({ error: "invalid_json" }, 400, request);
  }
}

function normalizeUserText(value: unknown): string | Response {
  const text = typeof value === "string" ? value.trim() : "";
  if (text.length > MAX_USER_TEXT_CHARS) {
    return jsonResponse({ error: "input_too_long" }, 413);
  }
  return text;
}

function normalizeHistory(value: unknown): HistoryMessage[] | Response {
  if (!Array.isArray(value)) {
    return jsonResponse({ error: "invalid_history" }, 400);
  }
  if (value.length > MAX_HISTORY_MESSAGES || value.length % 2 !== 0) {
    return jsonResponse({ error: "history_too_long" }, 413);
  }

  const out: HistoryMessage[] = [];
  let total = 0;
  for (let i = 0; i < value.length; i += 1) {
    const item = value[i] as Record<string, unknown>;
    const expectedRole = i % 2 === 0 ? "user" : "assistant";
    if (!item || item.role !== expectedRole || typeof item.content !== "string") {
      return jsonResponse({ error: "invalid_history" }, 400);
    }
    if (item.content.length > MAX_HISTORY_ITEM_CHARS) {
      return jsonResponse({ error: "history_item_too_long" }, 413);
    }
    total += item.content.length;
    if (total > MAX_HISTORY_TOTAL_CHARS) {
      return jsonResponse({ error: "history_too_large" }, 413);
    }
    out.push({ role: expectedRole, content: item.content });
  }
  return out;
}

function countUserTurns(history: HistoryMessage[]): number {
  return history.filter((message) => message.role === "user").length;
}

function trailingSilenceCount(history: HistoryMessage[]): number {
  const users = history.filter((message) => message.role === "user").map((message) => message.content);
  let count = 0;
  for (let i = users.length - 1; i >= 0; i -= 1) {
    if (users[i] !== SILENCE_TEXT) break;
    count += 1;
  }
  return count;
}

function normalizeParticipantId(value: unknown): string | undefined {
  const text = typeof value === "string" ? value.trim() : "";
  return text ? text.slice(0, MAX_PARTICIPANT_ID_CHARS) : undefined;
}

function formatTranscript(history: HistoryMessage[]): string {
  return history
    .map((message) => `${message.role === "user" ? "user" : "assistant"}: ${message.content}`)
    .join("\n\n");
}

function durationSeconds(startedAt: string | undefined, endedAtMs: number): number | null {
  const startedAtMs = Date.parse(startedAt || "");
  if (!Number.isFinite(startedAtMs)) return null;
  return Math.max(0, Math.floor((endedAtMs - startedAtMs) / 1000));
}

async function logResearchStart(env: Env, participantId: string | undefined, startedAt: string): Promise<void> {
  if (!participantId) return;
  if (!env.RESEARCH_DB) return;
  try {
    await env.RESEARCH_DB.prepare(
      "INSERT OR REPLACE INTO sessions (participant_id, started_at, turns, max_stage, ended, created_at) VALUES (?, ?, ?, ?, ?, ?)",
    )
      .bind(participantId, startedAt, 0, 0, 0, startedAt)
      .run();
  } catch {
    // Research logging must never affect play.
  }
}

async function logResearchTurn(
  env: Env,
  token: SessionTokenPayload,
  turns: number,
  stage: number,
  ended: boolean,
  history: HistoryMessage[],
): Promise<void> {
  const participantId = token.participantId;
  if (!participantId) return;
  if (!env.RESEARCH_DB) return;

  try {
    const maxStage = clampInt(stage, 0, 5);
    const transcript = env.RESEARCH_TRANSCRIPT === "true" ? formatTranscript(history) : null;

    if (ended) {
      const endedAt = new Date();
      const endedAtIso = endedAt.toISOString();
      const durationSec = durationSeconds(token.startedAt, endedAt.getTime());
      if (transcript !== null) {
        await env.RESEARCH_DB.prepare(
          "UPDATE sessions SET turns = ?, max_stage = MAX(COALESCE(max_stage, 0), ?), ended_at = ?, duration_sec = ?, ended = 1, transcript = ? WHERE participant_id = ?",
        )
          .bind(turns, maxStage, endedAtIso, durationSec, transcript, participantId)
          .run();
      } else {
        await env.RESEARCH_DB.prepare(
          "UPDATE sessions SET turns = ?, max_stage = MAX(COALESCE(max_stage, 0), ?), ended_at = ?, duration_sec = ?, ended = 1 WHERE participant_id = ?",
        )
          .bind(turns, maxStage, endedAtIso, durationSec, participantId)
          .run();
      }
      return;
    }

    if (transcript !== null) {
      await env.RESEARCH_DB.prepare(
        "UPDATE sessions SET turns = ?, max_stage = MAX(COALESCE(max_stage, 0), ?), transcript = ? WHERE participant_id = ?",
      )
        .bind(turns, maxStage, transcript, participantId)
        .run();
    } else {
      await env.RESEARCH_DB.prepare(
        "UPDATE sessions SET turns = ?, max_stage = MAX(COALESCE(max_stage, 0), ?) WHERE participant_id = ?",
      )
        .bind(turns, maxStage, participantId)
        .run();
    }
  } catch {
    // Research logging must never affect play.
  }
}

async function issueStateToken(
  env: Env,
  state: Omit<SessionTokenPayload, "v" | "iat" | "maxTurns" | "h"> & { history: HistoryMessage[] },
): Promise<string | null> {
  if (!env.SESSION_HMAC_SECRET) return null;
  const payload: SessionTokenPayload = {
    v: 1,
    sid: state.sid,
    iat: Math.floor(Date.now() / 1000),
    maxTurns: MAX_SESSION_TURNS,
    turns: state.turns,
    stage: clampInt(state.stage, 0, 5),
    opened: Boolean(state.opened),
    done: Boolean(state.done),
    h: await hashHistory(state.history),
  };
  if (state.participantId) payload.participantId = state.participantId;
  if (state.startedAt) payload.startedAt = state.startedAt;
  return signToken(payload, env.SESSION_HMAC_SECRET);
}

async function verifyStateToken(
  env: Env,
  token: string,
  history: HistoryMessage[],
): Promise<SessionTokenPayload | Response> {
  if (!env.SESSION_HMAC_SECRET) {
    return jsonResponse({ error: "server_not_configured", message: "サーバ設定が未完了です。" }, 503);
  }
  const payload = await verifyToken(token, env.SESSION_HMAC_SECRET);
  if (!payload) {
    return jsonResponse({ error: "invalid_token", message: "扉の合図が見つかりません。はじめからお試しください。" }, 401);
  }
  const now = Math.floor(Date.now() / 1000);
  if (now - payload.iat > SESSION_TTL_SECONDS || payload.iat > now + 60) {
    return jsonResponse({ error: "expired_token", message: "扉の前から、時間がたちすぎました。はじめからお試しください。" }, 401);
  }
  const expectedHash = await hashHistory(history);
  if (payload.h !== expectedHash || payload.turns !== countUserTurns(history)) {
    return jsonResponse({ error: "state_mismatch", message: "ことばの記録が合いません。つづきからではなく、はじめからお試しください。" }, 409);
  }
  return payload;
}

async function signToken(payload: SessionTokenPayload, secret: string): Promise<string> {
  const encodedPayload = base64UrlEncode(new TextEncoder().encode(JSON.stringify(payload)));
  const signature = await hmacSha256(secret, encodedPayload);
  return `${encodedPayload}.${base64UrlEncode(signature)}`;
}

async function verifyToken(token: string, secret: string): Promise<SessionTokenPayload | null> {
  const [payloadPart, signaturePart] = token.split(".");
  if (!payloadPart || !signaturePart) return null;
  const expected = base64UrlEncode(await hmacSha256(secret, payloadPart));
  if (!constantTimeEqual(signaturePart, expected)) return null;

  try {
    const json = new TextDecoder().decode(base64UrlDecode(payloadPart));
    const payload = JSON.parse(json) as Partial<SessionTokenPayload>;
    if (
      payload.v !== 1 ||
      typeof payload.sid !== "string" ||
      typeof payload.iat !== "number" ||
      typeof payload.maxTurns !== "number" ||
      typeof payload.turns !== "number" ||
      typeof payload.stage !== "number" ||
      typeof payload.opened !== "boolean" ||
      typeof payload.done !== "boolean" ||
      typeof payload.h !== "string"
    ) {
      return null;
    }
    if (payload.participantId !== undefined && typeof payload.participantId !== "string") return null;
    if (payload.startedAt !== undefined && typeof payload.startedAt !== "string") return null;
    return payload as SessionTokenPayload;
  } catch {
    return null;
  }
}

async function hmacSha256(secret: string, data: string): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data)));
}

async function hashHistory(history: HistoryMessage[]): Promise<string> {
  const canonical = JSON.stringify(history.map((message) => ({ role: message.role, content: message.content })));
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
  return base64UrlEncode(new Uint8Array(digest));
}

async function verifyTurnstile(env: Env, token: string, remoteIp: string): Promise<boolean> {
  if (!env.TURNSTILE_SECRET) return false;
  try {
    const form = new FormData();
    form.append("secret", env.TURNSTILE_SECRET);
    form.append("response", token);
    if (remoteIp) form.append("remoteip", remoteIp);
    const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      body: form,
    });
    if (!response.ok) return false;
    const data = (await response.json()) as { success?: boolean };
    return data.success === true;
  } catch {
    return false;
  }
}

async function consumeDailyCall(env: Env): Promise<boolean> {
  const capValue = Number.parseInt(env.DAILY_CALL_CAP || "600", 10);
  const cap = Number.isFinite(capValue) ? capValue : 600;
  if (cap <= 0) return false;

  const key = `calls:${jstDateKey()}`;
  try {
    const currentRaw = await env.DOOR_KV.get(key);
    const current = Number.parseInt(currentRaw || "0", 10) || 0;
    if (current >= cap) return false;
    await env.DOOR_KV.put(key, String(current + 1), { expirationTtl: secondsUntilNextJstDay() + 3600 });
    return true;
  } catch {
    return false;
  }
}

function jstDateKey(): string {
  return new Date(Date.now() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10);
}

function secondsUntilNextJstDay(): number {
  const now = Date.now();
  const jstNow = now + 9 * 60 * 60 * 1000;
  const nextJstMidnightAsUtc = (Math.floor(jstNow / 86400000) + 1) * 86400000 - 9 * 60 * 60 * 1000;
  return Math.max(60, Math.ceil((nextJstMidnightAsUtc - now) / 1000));
}

function enforceSameOrigin(request: Request): Response | null {
  const origin = request.headers.get("Origin");
  if (!origin) return null;
  const expected = new URL(request.url).origin;
  if (origin !== expected) {
    return jsonResponse({ error: "forbidden_origin" }, 403, request);
  }
  return null;
}

function corsHeaders(request?: Request): Headers {
  const headers = new Headers();
  const origin = request?.headers.get("Origin");
  if (origin && request && origin === new URL(request.url).origin) {
    headers.set("Access-Control-Allow-Origin", origin);
    headers.set("Vary", "Origin");
  }
  headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Content-Type");
  headers.set("Access-Control-Max-Age", "86400");
  return headers;
}

function jsonResponse(data: unknown, status = 200, request?: Request): Response {
  const headers = corsHeaders(request);
  headers.set("Content-Type", "application/json; charset=utf-8");
  headers.set("Cache-Control", "no-store");
  headers.set("X-Content-Type-Options", "nosniff");
  return new Response(JSON.stringify(data), { status, headers });
}

function randomId(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return base64UrlEncode(bytes);
}

function clampInt(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.max(min, Math.min(max, Math.trunc(value)));
}

function base64UrlEncode(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function base64UrlDecode(value: string): Uint8Array {
  const padded = value.replaceAll("-", "+").replaceAll("_", "/") + "===".slice((value.length + 3) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

function constantTimeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
