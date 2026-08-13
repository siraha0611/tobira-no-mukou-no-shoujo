# 綾香の手紙(縦書き・手書き風)ジェネレーター
# 一文字ずつ、わずかな回転・位置ズレ・濃淡(筆圧ムラ)を与えて手書き感を出す。
# PAGE_SIZE を "A4" にすると、A5用に組んだデザインをそのままの比率で拡大しA4に配置する
# (A5とA4は縦横比が同じ=A5を2枚並べるとA4になる関係。SCALEで全長さを一括変換)
# 使い方: python3 _generate_letter.py → 綾香の手紙_A4.html を再生成
#         → Chrome headless で PDF 化
import random

random.seed(20030815)  # 綾香の最後の夏。シードを固定=毎回同じ揺らぎ(再現可能)

PAGE_SIZE = "A4"  # "A5" or "A4"
BASE_W, BASE_H = 148.0, 210.0  # 元デザインの基準(A5・mm)
PAGE_DIMS = {"A5": (148.0, 210.0), "A4": (210.0, 297.0)}
PAGE_W, PAGE_H = PAGE_DIMS[PAGE_SIZE]
SCALE = PAGE_W / BASE_W  # A4なら約1.4189倍(A5→A4の拡大率)

def mm(v):
    return f"{v * SCALE:.2f}mm"

def pt(v):
    return f"{v * SCALE:.2f}pt"

def jitter_chars(text, char_scale=1.0):
    """各文字を、回転・横ズレ・大きさ・濃さをわずかに揺らしたspanにする"""
    out = []
    for ch in text:
        rot = random.uniform(-2.4, 2.4) * char_scale                    # 回転(度・拡大の影響を受けない)
        dx = random.uniform(-0.08, 0.08) * char_scale * SCALE           # 列と直角方向のズレ(罫線中心を保つため小さめ)
        dy = random.uniform(-0.12, 0.12) * char_scale * SCALE           # 進行方向のズレ
        size = random.uniform(0.94, 1.06)                               # 大きさのムラ
        ink = random.uniform(0.78, 1.0)                                 # 濃淡(筆圧)
        out.append(
            f'<span style="display:inline-block;'
            f'transform:rotate({rot:.2f}deg) translate({dx:.2f}mm,{dy:.2f}mm) scale({size:.3f});'
            f'opacity:{ink:.2f}">{ch}</span>'
        )
    return "".join(out)

LINES = [
    ("to", "あなたへ"),
    ("sp", ""),
    ("in", "今日は、わたしとお話をしてくれて、ありがとうございました。"),
    ("in", "あなたがくれた言葉を、ひとつずつ、大切に味わって、"),
    ("in", "わたしは、わたしを思い出すことができました。"),
    ("sp", ""),
    ("in", "今度こそ、やまとと、お祭りに行ってきます。"),
    ("sp", ""),
    ("in", "あなたの毎日が、おいしい言葉で満ちていますように。"),
    ("sp", ""),
    ("sign", "綾香"),
    ("ps", "追伸　あなたの言葉、ごちそうさまでした"),
]

body = []
for cls, text in LINES:
    if cls == "sp":
        body.append('      <div class="sp"></div>')
        continue
    sway = random.uniform(-0.25, 0.25)  # 行ぜんたいのわずかな傾き(拡大しても角度なので変えない)
    content = jitter_chars(text, 1.15 if cls == "sign" else 1.0)
    klass = f' class="{cls}"' if cls else ""
    body.append(f'      <div{klass} style="transform:rotate({sway:.2f}deg)">{content}</div>')
body_html = "\n".join(body)

# 罫線の列ピッチ(元デザインは10.5mm=罫線間隔10.35mm+線0.15mm)を拡大率にあわせて再計算
COL_PITCH = 10.5 * SCALE
COL_LINE = 0.15 * SCALE
COL_GAP = COL_PITCH - COL_LINE

HTML = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>綾香の手紙</title>
<style>
  @font-face{{
    font-family:'Zen Kurenaido';
    src:url('ZenKurenaido-Regular.ttf') format('truetype');
  }}
  @page{{size:{PAGE_SIZE};margin:0}}
  *{{margin:0;padding:0;box-sizing:border-box}}
  html,body{{width:{PAGE_W}mm;height:{PAGE_H}mm}}
  body{{
    font-family:'Zen Kurenaido','Klee','Hiragino Mincho ProN',serif;
    background:#faf7ee;
    color:#3a3f52; /* 万年筆のブルーブラック */
    -webkit-print-color-adjust:exact;print-color-adjust:exact;
    position:relative;overflow:hidden;
  }}
  .frame{{position:absolute;inset:{mm(6)};border:{mm(0.4)} solid #cdbf9d}}
  .frame::before{{content:"";position:absolute;inset:{mm(1.2)};border:{mm(0.15)} solid #d8ccb0}}
  .paper{{
    position:absolute;inset:{mm(13)} {mm(10)} {mm(15)} {mm(10)};
    /* 罫線は列境界(拡大後 {COL_PITCH:.2f}mmごと)。文字は列中央=線とほぼ均等な余白 */
    background:repeating-linear-gradient(to left,transparent 0,transparent {COL_GAP:.2f}mm,#e6dcc2 {COL_GAP:.2f}mm,#e6dcc2 {COL_PITCH:.2f}mm);
  }}
  .letter{{
    writing-mode:vertical-rl;
    font-size:{pt(13.5)};line-height:{COL_PITCH:.2f}mm;letter-spacing:0.1em;
    height:100%;
  }}
  .to{{font-size:{pt(15)}}}
  .sp{{width:{COL_PITCH:.2f}mm}}
  .in{{padding-top:{mm(8)}}}
  .sign{{font-size:{pt(17)};padding-top:{mm(118)};letter-spacing:.28em}}
  .ps{{font-size:{pt(11)};color:#4a4f64;letter-spacing:.06em;padding-top:{mm(70)}}}
</style>
</head>
<body>
  <div class="frame"></div>
  <div class="paper">
    <div class="letter">
{body_html}
    </div>
  </div>
</body>
</html>
"""

outname = f"綾香の手紙_{PAGE_SIZE}.html"
with open(outname, "w", encoding="utf-8") as f:
    f.write(HTML)
print(f"written: {outname} (scale x{SCALE:.4f} from A5 design)")
