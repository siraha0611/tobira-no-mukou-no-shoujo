# 綾香の手紙(A5・縦書き・手書き風)ジェネレーター
# 一文字ずつ、わずかな回転・位置ズレ・濃淡(筆圧ムラ)を与えて手書き感を出す。
# 使い方: python3 _generate_letter.py → 綾香の手紙_A5.html を再生成
#         → Chrome headless で PDF 化(README参照 or 手紙PDF再生成.command)
import random

random.seed(20030815)  # 綾香の最後の夏。シードを固定=毎回同じ揺らぎ(再現可能)

def jitter_chars(text, scale=1.0):
    """各文字を、回転・横ズレ・大きさ・濃さをわずかに揺らしたspanにする"""
    out = []
    for ch in text:
        rot = random.uniform(-2.4, 2.4) * scale          # 回転(度)
        dx = random.uniform(-0.28, 0.28) * scale          # 列と直角方向のズレ(mm)
        dy = random.uniform(-0.12, 0.12) * scale          # 進行方向のズレ(mm)
        size = random.uniform(0.94, 1.06)                 # 大きさのムラ
        ink = random.uniform(0.78, 1.0)                   # 濃淡(筆圧)
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
    ("",   "わたしは、わたしを思い出すことができました。"),
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
    sway = random.uniform(-0.5, 0.5)  # 行ぜんたいのわずかな傾き
    content = jitter_chars(text, 1.15 if cls == "sign" else 1.0)
    klass = f' class="{cls}"' if cls else ""
    body.append(f'      <div{klass} style="transform:rotate({sway:.2f}deg)">{content}</div>')
body_html = "\n".join(body)

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
  @page{{size:A5;margin:0}}
  *{{margin:0;padding:0;box-sizing:border-box}}
  html,body{{width:148mm;height:210mm}}
  body{{
    font-family:'Zen Kurenaido','Klee','Hiragino Mincho ProN',serif;
    background:#faf7ee;
    color:#3a3f52; /* 万年筆のブルーブラック */
    -webkit-print-color-adjust:exact;print-color-adjust:exact;
    position:relative;overflow:hidden;
  }}
  .frame{{position:absolute;inset:6mm;border:0.4mm solid #cdbf9d}}
  .frame::before{{content:"";position:absolute;inset:1.2mm;border:0.15mm solid #d8ccb0}}
  .paper{{
    position:absolute;inset:13mm 10mm 15mm 10mm;
    /* 罫線は列境界(10.5mmごと)。文字は列中央=線と約3mmの余白 */
    background:repeating-linear-gradient(to left,transparent 0,transparent 10.35mm,#e6dcc2 10.35mm,#e6dcc2 10.5mm);
  }}
  .letter{{
    writing-mode:vertical-rl;
    font-size:13.5pt;line-height:10.5mm;letter-spacing:0.1em;
    height:100%;
  }}
  .to{{font-size:15pt}}
  .sp{{width:10.5mm}}
  .in{{padding-top:8mm}}
  .sign{{font-size:17pt;padding-top:118mm;letter-spacing:.28em}}
  .ps{{font-size:11pt;color:#4a4f64;letter-spacing:.06em;padding-top:70mm}}
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

with open("綾香の手紙_A5.html", "w", encoding="utf-8") as f:
    f.write(HTML)
print("written: 綾香の手紙_A5.html")
